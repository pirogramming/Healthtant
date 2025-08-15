# insert_price_simple.py
# 헤더 없는 5~6열 파일 전용:
# 5 cols: food_id, mallName, lprice, product_link, image
# 6 cols: food_id, mallName, lprice, hprice, product_link, image

import os, sys, hashlib, re
import pandas as pd
from django.db import connection, transaction
from django.utils import timezone
import django

# ==== Django env ====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')  # manage.py와 동일
django.setup()

CSV_PATH    = 'naver_prices_clean.csv'   # <- 네 파일 이름로 바꿔줘
PRICE_TABLE = 'price'

def manual_read_no_header(path):
    rows = []
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.rstrip('\r\n')
            if not line:
                continue
            # 1) 탭
            parts = line.split('\t')
            if len(parts) in (5, 6):
                rows.append(parts)
                continue
            # 2) 콤마
            parts = line.split(',')
            if len(parts) in (5, 6):
                rows.append(parts)
                continue
            # 3) 공백(여러 칸) — 링크에 공백이 거의 없다고 가정, 최대 5분할
            parts = re.split(r'\s+', line.strip(), maxsplit=5)
            if len(parts) in (5, 6):
                rows.append(parts)
                continue
            # 4) food_id 하나만 있는 줄이면 5열로 패딩
            if len(parts) == 1:
                rows.append([parts[0], '', '', '', ''])  # 5열 가정
                continue

    if not rows:
        raise RuntimeError("파싱된 행이 없습니다. 파일/구분자 확인 필요")

    # 가장 많은 열수로 맞추고 나머지는 '' 패딩
    max_cols = max(len(r) for r in rows)
    if max_cols not in (5, 6):
        raise RuntimeError(f"열 개수 {max_cols}: 지원 포맷(5/6열)이 아닙니다")

    fixed = []
    for r in rows:
        r = [x.strip() for x in r]
        if len(r) < max_cols:
            r += [''] * (max_cols - len(r))
        fixed.append(r)

    df = pd.DataFrame(fixed)
    if max_cols == 5:
        df.columns = ['food_id','mallName','lprice','product_link','image']
        df['hprice'] = ''
    else:  # 6
        df.columns = ['food_id','mallName','lprice','hprice','product_link','image']
    return df.fillna('')

def sha1_key(food_id, shop_name, product_url, image_url, price):
    anchor = (product_url or image_url or str(price or ''))
    key = f"{food_id}|{shop_name}|{anchor}"
    return hashlib.sha1(key.encode('utf-8')).hexdigest()

def main():
    df = manual_read_no_header(CSV_PATH)

    # 트리밍
    for c in df.columns:
        df[c] = df[c].astype(str).str.strip()

    # === 변환 ===
    p = pd.DataFrame()
    p['food_id']   = df['food_id']
    p['shop_name'] = df['mallName'].replace('', 'UNKNOWN')

    p['price'] = pd.to_numeric(df['lprice'].str.replace(',', ''), errors='coerce').fillna(0).astype('int64')
    dp = pd.to_numeric(df.get('hprice','').astype(str).str.replace(',', ''), errors='coerce')
    p['discount_price'] = dp.where(pd.notna(dp), None)

    p['product_url']       = df['product_link'].replace('', None)
    p['product_image_url'] = df['image'].replace('', None)

    now_s = timezone.now().isoformat(sep=' ')
    p['is_available']    = (p['price'] > 0).astype(int)
    p['created_at']      = now_s
    p['updated_at']      = now_s
    p['crawled_at']      = None
    p['crawling_error']  = None
    p['crawling_status'] = 'NEW'

    # PK (url 없으면 image, 그마저 없으면 price로 구분)
    p['price_id'] = [
        sha1_key(fid, shop, url, img, int(price))
        for fid, shop, url, img, price in zip(
            p['food_id'], p['shop_name'], p['product_url'], p['product_image_url'], p['price']
        )
    ]

    # FK 비어있는 행 제거
    p = p[p['food_id'].astype(str).str.strip().ne('')]

    # --- FK 보호 및 정규화 ---
    # 1) food_id 유니코드/공백 정리
    p['food_id'] = (
        p['food_id'].astype(str)
        .str.replace('\uFEFF', '', regex=False)  # BOM 제거
        .str.strip()
    )

    # 2) food 테이블에서 유효한 키 수집
    with connection.cursor() as cur:
        cur.execute("SELECT food_id FROM food")
        valid_ids = { (row[0] or '').strip() for row in cur.fetchall() }

    # 3) 어떤 food_id가 없는지 미리 진단
    p_ids = set(p['food_id'].unique())
    missing = sorted(list(p_ids - valid_ids))[:20]  # 샘플 20개만
    print(f"[PRICE] unique in CSV: {len(p_ids)}, valid in food: {len(valid_ids)}")
    print(f"[PRICE] sample missing food_id (at most 20): {missing}")

    # 4) 유효하지 않은 행을 제거
    before = len(p)
    p = p[p['food_id'].isin(valid_ids)]
    dropped = before - len(p)
    print(f"[PRICE] FK filter -> kept={len(p)}, dropped(no matching food)={dropped}")

    # 업서트 컬럼 순서
    cols = [
        'price_id','shop_name','price','discount_price','is_available',
        'created_at','updated_at','food_id','crawled_at','crawling_error',
        'crawling_status','product_image_url','product_url'
    ]

    n = len(p)
    print(f"[PRICE] will upsert rows: {n}")
    if n == 0:
        print("[PRICE] SKIP (no rows)"); return

    # 빈 문자열이 오면 기존 값 덮지 않기 (COALESCE/NULLIF)
    placeholders = ",".join(["?"] * len(cols))
    set_clause = (
        f"shop_name=excluded.shop_name,"
        f"price=excluded.price,"
        f"discount_price=COALESCE(excluded.discount_price, {PRICE_TABLE}.discount_price),"
        f"is_available=excluded.is_available,"
        f"created_at=excluded.created_at,"
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

    records = [tuple(p.iloc[i][cols].tolist()) for i in range(n)]

    with transaction.atomic():
        with connection.cursor() as cur:
            chunk = 1000
            for i in range(0, n, chunk):
                cur.executemany(sql, records[i:i+chunk])

    print(f"[PRICE] DONE: {n}")

if __name__ == "__main__":
    main()