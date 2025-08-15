# -*- coding: utf-8 -*-
# insert_price_from_csv.py
# - CSV(6열: food_id,shop_name,price,discount_price,shop_url,image_url) 로부터 price UPSERT
# - FK(food.food_id) 없는 행은 자동 제거
# - 기존 price 행은 ON CONFLICT(price_id) UPDATE
# - food.product_image_url 이 비어있으면 CSV의 이미지로 보충 업데이트

import os, sys, hashlib
import pandas as pd
from django.db import connection, transaction
from django.utils import timezone
import django

# ==== Django 환경 ====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')  # manage.py와 동일
django.setup()

# ==== 설정 ====
CSV_PATH     = os.path.join(BASE_DIR, 'naver_prices_clean.csv')  # 네가 올려둔 파일명
PRICE_TABLE  = 'price'                                     # 실제 가격 테이블명
FOOD_TABLE   = 'food'                                      # 실제 food 테이블명

# ---- 유틸 ----
def safe_print(*args):
    try:
        s = " ".join(str(a) for a in args)
        sys.stdout.write(s + "\n")
    except Exception:
        s = " ".join(str(a) for a in args)
        sys.stdout.write(s.encode('utf-8', 'replace').decode('utf-8') + "\n")

def sha1(s: str) -> str:
    return hashlib.sha1(s.encode('utf-8')).hexdigest()

def mk_price_id(food_id: str, shop_name: str, product_url: str, image_url: str, price: int) -> str:
    # product_url 우선, 없으면 image_url, 그것도 없으면 price 로 고정키 구성
    anchor = (product_url or image_url or str(price or 0)).strip()
    key = f"{(food_id or '').strip()}|{(shop_name or '').strip()}|{anchor}"
    return sha1(key)

def read_csv_6cols(path: str) -> pd.DataFrame:
    # 인코딩/구분자 유연 파서 (콤마 CSV 고정, header 유무/중복헤더 정리)
    tries = ['utf-8-sig', 'cp949']
    last_err = None
    for enc in tries:
        try:
            df = pd.read_csv(
                path,
                engine='python',    # 유연 파서
                sep=',',            # 이 파일은 콤마 CSV
                header=None,        # 헤더를 직접 처리(중복헤더 라인 존재)
                dtype=str,
                on_bad_lines='skip' # 깨진 라인 무시
            )
            # 공백/NaN 제거
            df = df.fillna('').astype(str)
            # 6열만 남기기/부족하면 채우기
            if df.shape[1] < 6:
                # 부족한 열은 빈 문자열로 채움
                for _ in range(6 - df.shape[1]):
                    df[df.shape[1]] = ''
            elif df.shape[1] > 6:
                df = df.iloc[:, :6]

            # 첫 행이 친절한 헤더인지 확인
            friendly_header = ['food_id','shop_name','price','discount_price','shop_url','image_url']
            alias_header    = ['food_id','mallName','lprice','hprice','product_link','image']

            def row_equals(r, header):
                return all(str(r[i]).strip() == header[i] for i in range(6))

            # 헤더 제거 로직
            drop_idx = []
            if row_equals(df.iloc[0], friendly_header):
                drop_idx.append(0)
            # 두 번째 줄이 alias 헤더일 수 있음
            if df.shape[0] > 1 and row_equals(df.iloc[1], alias_header):
                drop_idx.append(1)

            if drop_idx:
                df = df.drop(index=drop_idx).reset_index(drop=True)

            # 최종 컬럼명 부여
            df.columns = friendly_header

            # 완전 공백 행 제거
            df = df[~(df.apply(lambda r: ''.join(r.values.tolist()).strip() == '', axis=1))]

            return df
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"CSV 파싱 실패: {last_err}")

def main():
    # 1) CSV 로드/정리
    df = read_csv_6cols(CSV_PATH)

    # 타입 보정
    def to_int(s):
        try:
            s = str(s).replace(',', '').strip()
            if s == '' or s.lower() == 'nan':
                return None
            return int(float(s))
        except Exception:
            return None

    p = pd.DataFrame()
    p['food_id']            = df['food_id'].astype(str).str.strip()
    p['shop_name']          = df['shop_name'].astype(str).str.strip().replace('', 'UNKNOWN')
    p['price']              = df['price'].apply(to_int).fillna(0).astype('int64')  # NOT NULL
    dp                      = df['discount_price'].apply(to_int)
    p['discount_price']     = dp.where(pd.notna(dp), None)
    p['product_url']        = df['shop_url'].astype(str).str.strip().replace('', None)
    p['product_image_url']  = df['image_url'].astype(str).str.strip().replace('', None)

    # 상태/시간
    now_s = timezone.now().isoformat(sep=' ')
    p['is_available']     = (p['price'] > 0).astype(int)  # sqlite: 0/1
    p['created_at']       = now_s
    p['updated_at']       = now_s
    p['crawled_at']       = None
    p['crawling_error']   = None
    p['crawling_status']  = 'NEW'

    # PK
    p['price_id'] = [
        mk_price_id(fid, shop, url or '', img or '', int(price))
        for fid, shop, url, img, price in zip(
            p['food_id'], p['shop_name'], p['product_url'], p['product_image_url'], p['price']
        )
    ]

    # FK 보호: food 테이블에 없는 food_id 제거
    with connection.cursor() as cur:
        cur.execute(f"SELECT food_id FROM {FOOD_TABLE};")
        food_ids = set(r[0] for r in cur.fetchall())
    before = p['food_id'].nunique()
    p = p[p['food_id'].isin(food_ids)]
    after = p['food_id'].nunique()
    safe_print(f"[PRICE] unique in CSV:", before, ", valid in food:", after)

    # 완전 비어있는 food_id 제거
    p = p[p['food_id'].astype(str).str.strip().ne('')]

    # 2) price UPSERT
    cols = [
        'price_id','shop_name','price','discount_price','is_available',
        'created_at','updated_at','food_id','crawled_at','crawling_error',
        'crawling_status','product_image_url','product_url'
    ]
    placeholders = ",".join(["?"] * len(cols))
    # NULL/빈문자 보존 로직: 새 값이 없으면 기존 값을 유지하도록 COALESCE/NULLIF 사용
    set_clause = (
        f"shop_name=excluded.shop_name,"
        f"price=excluded.price,"
        f"discount_price=COALESCE(excluded.discount_price, {PRICE_TABLE}.discount_price),"
        f"is_available=excluded.is_available,"
        f"created_at=excluded.created_at,"   # 생성시각 그대로 유지하고 싶으면 이 줄은 빼도 됨
        f"updated_at=excluded.updated_at,"
        f"food_id=excluded.food_id,"
        f"crawled_at=COALESCE(excluded.crawled_at, {PRICE_TABLE}.crawled_at),"
        f"crawling_error=COALESCE(NULLIF(excluded.crawling_error,''), {PRICE_TABLE}.crawling_error),"
        f"crawling_status=excluded.crawling_status,"
        f"product_image_url=COALESCE(NULLIF(excluded.product_image_url,''), {PRICE_TABLE}.product_image_url),"
        f"product_url=COALESCE(NULLIF(excluded.product_url,''), {PRICE_TABLE}.product_url)"
    )
    sql = f"""
    INSERT INTO {PRICE_TABLE} ({", ".join(cols)})
    VALUES ({placeholders})
    ON CONFLICT(price_id) DO UPDATE SET
    {set_clause};
    """
    records = [tuple(p.iloc[i][cols].tolist()) for i in range(len(p))]
    safe_print(f"[PRICE] will upsert rows:", len(records))
    if not records:
        safe_print("[PRICE] SKIP (no rows)")
        return

    # 3) 트랜잭션 실행
    with transaction.atomic():
        with connection.cursor() as cur:
            # FK 확인용: 혹시라도 남아있는 유효하지 않은 food_id가 있으면 여기서 에러날 수 있음
            chunk = 1000
            for i in range(0, len(records), chunk):
                cur.executemany(sql, records[i:i+chunk])

    safe_print(f"[PRICE] DONE:", len(records))

    # 4) 보너스: food.product_image_url 보충(비어있는 경우만)
    #    - 동일 food_id에 대해 CSV에서 첫 번째 non-null image를 사용
    img_src = (
        p[['food_id','product_image_url']]
        .dropna(subset=['product_image_url'])
        .groupby('food_id', as_index=False)['product_image_url'].first()
    )
    if not img_src.empty:
        upd_records = [
            (row['product_image_url'], row['food_id'])
            for _, row in img_src.iterrows()
        ]
        sql_food = f"""
        UPDATE {FOOD_TABLE}
        SET product_image_url = ?
        WHERE food_id = ?
          AND (product_image_url IS NULL OR TRIM(product_image_url) = '');
        """
        with transaction.atomic():
            with connection.cursor() as cur:
                chunk = 1000
                for i in range(0, len(upd_records), chunk):
                    cur.executemany(sql_food, upd_records[i:i+chunk])
        safe_print(f"[FOOD] filled empty product_image_url rows:", len(upd_records))
    else:
        safe_print("[FOOD] no image candidates in CSV")

if __name__ == "__main__":
    main()