# insert_food_safe.py
# - ASCII 출력만 사용 (이모지/특수문자 없음)
# - Windows 콘솔에서 surrogate 에러 회피
# - CSV: 탭 구분, UTF-8-SIG 기본, 실패시 CP949로 재시도

import pandas as pd
from django.db import connection, transaction
from django.utils import timezone
import django
import os, sys
import django
import numpy as np

# ① manage.py가 있는 프로젝트 루트를 sys.path에 추가
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # 이 파일과 manage.py가 같은 폴더라면 OK
sys.path.insert(0, BASE_DIR)

# ② DJANGO_SETTINGS_MODULE을 manage.py와 동일하게
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')  # ← manage.py에서 복붙

django.setup()

CSV_PATH = 'foods_with_price_image.csv'   # <-- 네 CSV 경로
TABLE_NAME = 'food'                       # <-- 실제 테이블명 (예: 'food' 또는 'foods_food')

def safe_print(*args):
    try:
        s = " ".join(str(a) for a in args)
        sys.stdout.write(s + "\n")
    except Exception:
        # 강제 치환 출력
        s = " ".join(str(a) for a in args)
        sys.stdout.write(s.encode('utf-8', 'replace').decode('utf-8') + "\n")

def to_float(s):
    try:
        s = str(s).strip().replace(',', '')
        if s == '' or s.lower() == 'nan':
            return None
        return float(s)
    except Exception:
        return None

def to_bigint(s):
    try:
        s = str(s).strip().replace(',', '')
        if s == '' or s.lower() == 'nan':
            return None
        return int(float(s))
    except Exception:
        return None

def read_csv_smart(path):
    # 1차: utf-8-sig, 자동 구분자
    try:
        df = pd.read_csv(path, sep=None, engine='python', dtype=str, encoding='utf-8-sig')
        if df.shape[1] > 1:
            return df
    except Exception:
        pass
    # 2차: utf-8-sig, 탭
    try:
        df = pd.read_csv(path, sep='\t', engine='python', dtype=str, encoding='utf-8-sig')
        if df.shape[1] > 1:
            return df
    except Exception:
        pass
    # 3차: utf-8-sig, 콤마
    try:
        df = pd.read_csv(path, sep=',', engine='python', dtype=str, encoding='utf-8-sig')
        if df.shape[1] > 1:
            return df
    except Exception:
        pass
    # 4차: cp949, 자동 구분자
    try:
        df = pd.read_csv(path, sep=None, engine='python', dtype=str, encoding='cp949', on_bad_lines='skip')
        if df.shape[1] > 1:
            return df
    except Exception:
        pass
    # 5차: cp949, 탭
    try:
        df = pd.read_csv(path, sep='\t', engine='python', dtype=str, encoding='cp949', on_bad_lines='skip')
        if df.shape[1] > 1:
            return df
    except Exception:
        pass
    # 6차: cp949, 콤마
    df = pd.read_csv(path, sep=',', engine='python', dtype=str, encoding='cp949', on_bad_lines='skip')
    return df

def main():
    # 1) CSV 로드
    df = read_csv_smart(CSV_PATH).fillna('')
    # BOM/공백 제거
    df.columns = df.columns.str.replace('\ufeff', '', regex=False).str.strip()
    # 혹시 헤더가 데이터로 섞였으면 제거
    if 'food_id' in df.columns:
        df = df[df['food_id'].astype(str).str.strip().ne('food_id')]

    safe_print("shape:", df.shape)
    safe_print("first columns:", df.columns.tolist()[:10])

    required = {'food_id','food_name','food_category','representative_food','calorie'}
    missing = required - set(df.columns)
    if missing:
        safe_print("ERROR: missing required columns:", missing)
        return

    non_empty_food_id = df['food_id'].astype(str).str.strip().ne('').sum()
    safe_print("non-empty food_id rows:", non_empty_food_id)
    if non_empty_food_id == 0:
        safe_print("ERROR: all food_id empty. Check CSV delimiter/header.")
        return

    # 2) 매핑
    csv_to_db = {
        'food_id': 'food_id',
        'food_name': 'food_name',
        'food_category': 'food_category',
        'representative_food': 'representative_food',
        'calorie': 'calorie',
        'moisture': 'moisture',
        'protein': 'protein',
        'fat': 'fat',
        'carbohydrate': 'carbohydrate',
        'sugar': 'sugar',
        'dietary_fiber': 'dietary_fiber',
        'calcium': 'calcium',
        'iron_content': 'iron_content',
        'phosphorus': 'phosphorus',
        'potassium': 'potassium',
        'salt': 'salt',
        'VitaminA': 'VitaminA',
        'VitaminB': 'VitaminB',
        'VitaminC': 'VitaminC',
        'VitaminD': 'VitaminD',
        'VitaminE': 'VitaminE',
        'cholesterol': 'cholesterol',
        'saturated_fatty_acids': 'saturated_fatty_acids',
        'trans_fatty_acids': 'trans_fatty_acids',
        'serving_size': 'serving_size',
        'nutrition_score': 'nutrition_score',
        'nutri_score_grade': 'nutri_score_grade',
        'nrf_index': 'nrf_index',
        'company_name': 'company_name',
        'food_img': 'food_img',
        'nutritional_value_standard_amount': 'nutritional_value_standard_amount',
        'weight': 'weight',
        'image': 'product_image_url',       # CSV 'image' -> DB 'product_image_url'
        'product_link': 'product_url',      # CSV 'product_link' -> DB 'product_url'
    }
    for src in csv_to_db:
        if src not in df.columns:
            df[src] = ''

    out = pd.DataFrame({dst: df[src] for src, dst in csv_to_db.items()})

    # Normalize media/link fields: empty string -> None, strip spaces
    if 'product_image_url' in out.columns:
        out['product_image_url'] = out['product_image_url'].astype(str).str.strip().replace({'': None})
    if 'product_url' in out.columns:
        out['product_url'] = out['product_url'].astype(str).str.strip().replace({'': None})

    # 3) 타입 보정
    float_cols = [
        'calorie','moisture','protein','fat','carbohydrate','sugar','dietary_fiber',
        'calcium','iron_content','phosphorus','potassium','salt','VitaminA','VitaminB',
        'VitaminC','VitaminD','VitaminE','cholesterol','saturated_fatty_acids',
        'trans_fatty_acids','serving_size','weight','nutrition_score','nrf_index'
    ]
    for c in float_cols:
        out[c] = out[c].apply(to_float)

    out['nutritional_value_standard_amount'] = out['nutritional_value_standard_amount'].apply(to_bigint)

    # NOT NULL 문자열 기본값
    for c in ['food_name','food_category','representative_food','company_name']:
        out[c] = out[c].apply(lambda s: (s or '').strip() or 'UNKNOWN')
    # NOT NULL 실수 기본값
    for c in ['calorie','moisture','protein','fat','carbohydrate','weight']:
        out[c] = out[c].apply(lambda v: 0.0 if v is None else v)
    # NOT NULL 정수 기본값
    out['nutritional_value_standard_amount'] = out['nutritional_value_standard_amount'].apply(
        lambda v: 0 if v is None else v
    )

    # 4) 시간/상태 컬럼
    now = timezone.now()
    out['created_at'] = now
    out['updated_at'] = now
    out['created_at'] = out['created_at'].apply(lambda x: x.isoformat(sep=' ') if hasattr(x, 'isoformat') else x)
    out['updated_at'] = out['updated_at'].apply(lambda x: x.isoformat(sep=' ') if hasattr(x, 'isoformat') else x)
    out['crawled_at'] = None
    out['crawling_error'] = None
    out['crawling_status'] = 'NEW'

    # 5) 최종 컬럼 순서 (네가 준 food 스키마 기준)

    # NOT NULL 수치 컬럼 강제 정규화 (NaN -> 0)
    nn_float = ['calorie','moisture','protein','fat','carbohydrate','weight']
    out[nn_float] = out[nn_float].apply(pd.to_numeric, errors='coerce').fillna(0.0)

    # 정수 컬럼도 강제 정규화 (NaN -> 0, int형)
    out['nutritional_value_standard_amount'] = (
        pd.to_numeric(out['nutritional_value_standard_amount'], errors='coerce')
        .fillna(0)
        .astype(int)
    )

    # 문자열 NOT NULL 컬럼도 공백 -> 'UNKNOWN'
    for c in ['food_name','food_category','representative_food','company_name']:
        out[c] = out[c].astype(str).str.strip().replace('', 'UNKNOWN')
    cols = [
        'food_id','food_img','food_name','food_category','representative_food',
        'nutritional_value_standard_amount','calorie','moisture','protein','fat',
        'carbohydrate','sugar','dietary_fiber','calcium','iron_content','phosphorus',
        'potassium','VitaminA','VitaminB','VitaminC','VitaminD','VitaminE',
        'cholesterol','saturated_fatty_acids','trans_fatty_acids','serving_size',
        'weight','company_name','nutrition_score','nutri_score_grade','nrf_index',
        'created_at','updated_at','crawled_at','crawling_error','crawling_status',
        'product_image_url','product_url','salt'
    ]

    for c in cols:
        if c not in out.columns:
            out[c] = None
    out = out[cols]

    # PK 비어있는 행 제거
    out = out[out['food_id'].astype(str).str.strip().ne('')]

    n = len(out)
    safe_print("will upsert rows:", n)

    # Debug counters for incoming media fields
    try:
        _img_nonempty = int((out['product_image_url'].notna()) & (out['product_image_url'].astype(str).str.strip() != '')).sum()
        _url_nonempty = int((out['product_url'].notna()) & (out['product_url'].astype(str).str.strip() != '')).sum()
        safe_print("incoming non-empty product_image_url rows:", _img_nonempty)
        safe_print("incoming non-empty product_url rows:", _url_nonempty)
    except Exception:
        pass

    if n == 0:
        safe_print("ERROR: no rows to upsert.")
        return

    # 6) UPSERT
    placeholders = ",".join(["?"] * len(cols))
    # Build SET clause for UPSERT with "keep existing if incoming is empty/NULL" for selected columns
    set_parts = []
    for c in cols:
        if c == 'food_id':
            continue
        if c in ('product_image_url', 'product_url', 'crawled_at', 'crawling_error'):
            # If the incoming value is NULL or empty string, keep the existing DB value
            set_parts.append(f"{c}=COALESCE(NULLIF(excluded.{c}, ''), {TABLE_NAME}.{c})")
        else:
            set_parts.append(f"{c}=excluded.{c}")
    set_clause = ",\n".join(set_parts)
    sql = f"""
    INSERT INTO {TABLE_NAME} ({", ".join(cols)})
    VALUES ({placeholders})
    ON CONFLICT(food_id) DO UPDATE SET
    {set_clause};
    """

    records = [tuple(out.iloc[i].tolist()) for i in range(n)]

    with transaction.atomic():
        with connection.cursor() as cur:
            chunk = 1000
            for i in range(0, n, chunk):
                cur.executemany(sql, records[i:i+chunk])

    safe_print("DONE: food upsert rows:", n)

if __name__ == "__main__":
    main()