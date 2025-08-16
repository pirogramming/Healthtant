import os, sys
import pandas as pd
from django.db import connection, transaction
import django

# 프로젝트 루트 경로 추가
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# Django 세팅
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

# 모델/점수 함수 import
from foods.models import Food
from common.nutrition_score import NutritionalScore, letterGrade

CSV_PATH = os.path.join(BASE_DIR, 'food_clean_data.csv')
TABLE_NAME = Food._meta.db_table

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

def purge_foods_and_children_auto():
    """
    Food를 참조하는 모든 자식 테이블을 먼저 삭제한 뒤, 마지막에 Food 삭제.
    기본 ordering으로 인해 컬럼 미존재 에러가 나지 않도록 .order_by()로 제거.
    """
    with transaction.atomic():
        # 1) Food 역참조(related_objects) 순회하며 자식부터 삭제
        for rel in Food._meta.related_objects:
            model = rel.related_model
            try:
                # 자식 모델에 기본 ordering이 걸려 있을 수 있으니 제거 후 delete
                qs = model._default_manager.all()
                try:
                    qs = qs.order_by()
                except Exception:
                    pass
                qs.delete()
            except Exception:
                # 일부 테이블이 실제로 없거나 마이그가 안 되어 있을 수 있음 → 무시
                pass

        # 2) 마지막으로 Food 삭제 (ordering 제거)
        Food.objects.all().order_by().delete()

def main():
    # 1) 기존 DB 데이터 모두 삭제
    safe_print("=== 기존 DB 데이터 삭제 중... ===")
    purge_foods_and_children_auto()
    safe_print("기존 데이터 삭제 완료")
    
    # 2) CSV 로드 
    df = read_csv_smart(CSV_PATH).fillna('')
    
    # food_clean_data.csv는 헤더가 있으므로 컬럼명 매핑만 확인
    
    # BOM/공백 제거
    df.columns = df.columns.str.replace('\ufeff', '', regex=False).str.strip()

    safe_print("shape:", df.shape)
    safe_print("first columns:", df.columns.tolist()[:10])

    required = {'food_id'}
    missing = required - set(df.columns)
    if missing:
        safe_print("ERROR: missing required columns:", missing)
        return

    non_empty_food_id = df['food_id'].astype(str).str.strip().ne('').sum()
    safe_print("non-empty food_id rows:", non_empty_food_id)
    if non_empty_food_id == 0:
        safe_print("ERROR: all food_id empty. Check CSV delimiter/header.")
        return

    # 2) 매핑 - food_clean_data.csv 칼럼에 맞춰 수정
    csv_to_db = {
        'food_id': 'food_id',
        'mallName': 'shop_name',
        'lprice': 'price',
        'hprice': 'discount_price',
        'product_link': 'shop_url',
        'image': 'image_url',
        # 영양 점수 필드 추가
        'nutrition_score': 'nutrition_score',
        'nutri_score_grade': 'nutri_score_grade', 
        'nrf_index': 'nrf_index',
        # 기본값들
        'food_name': 'food_name',
        'food_category': 'food_category',
        'representative_food': 'representative_food',
        'company_name': 'company_name',
        'calorie': 'calorie',
        'moisture': 'moisture',
        'protein': 'protein',
        'fat': 'fat',
        'carbohydrate': 'carbohydrate',
        'nutritional_value_standard_amount': 'nutritional_value_standard_amount',
        'weight': 'weight',
        'food_img': 'food_img',
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
    }
    for src in csv_to_db:
        if src not in df.columns:
            df[src] = ''

    out = pd.DataFrame({dst: df[src] for src, dst in csv_to_db.items()})

    # Normalize media/link fields: empty string -> None, strip spaces
    if 'image_url' in out.columns:
        out['image_url'] = out['image_url'].astype(str).str.strip().replace({'': None})
    if 'shop_url' in out.columns:
        out['shop_url'] = out['shop_url'].astype(str).str.strip().replace({'': None})

    # 3) 타입 보정
    float_cols = [
        'calorie','moisture','protein','fat','carbohydrate','sugar','dietary_fiber',
        'calcium','iron_content','phosphorus','potassium','salt','VitaminA','VitaminB',
        'VitaminC','VitaminD','VitaminE','cholesterol','saturated_fatty_acids',
        'trans_fatty_acids','serving_size','weight'
    ]
    for c in float_cols:
        out[c] = out[c].apply(to_float)

    bigint_cols = ['nutritional_value_standard_amount', 'price', 'discount_price']
    for c in bigint_cols:
        out[c] = out[c].apply(to_bigint)

    # NOT NULL 문자열 기본값
    for c in ['food_name','food_category','representative_food','company_name']:
        out[c] = out[c].apply(lambda s: (s or '').strip() or 'UNKNOWN')
    # NOT NULL 실수 기본값
    for c in ['calorie','moisture','protein','fat','carbohydrate','weight']:
        out[c] = out[c].apply(lambda v: 0.0 if v is None else v)
    # NOT NULL 정수 기본값
    for c in ['nutritional_value_standard_amount']:
        out[c] = out[c].apply(lambda v: 0 if v is None else v)


    # 4) 최종 컬럼 순서 (수정된 Food 모델 기준)

    # NOT NULL 수치 컬럼 강제 정규화 (NaN -> 0)
    nn_float = ['calorie','moisture','protein','fat','carbohydrate','weight']
    for c in nn_float:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors='coerce').fillna(0.0)

    # 정수 컬럼도 강제 정규화 (NaN -> 0, int형)
    out['nutritional_value_standard_amount'] = (
        pd.to_numeric(out['nutritional_value_standard_amount'], errors='coerce')
        .fillna(0)
        .astype(int)
    )

    # 문자열 NOT NULL 컬럼도 공백 -> 'UNKNOWN'
    for c in ['food_name','food_category','representative_food','company_name']:
        if c in out.columns:
            out[c] = out[c].astype(str).str.strip().replace('', 'UNKNOWN')
    
    # 5) 영양 점수 계산 및 추가
    safe_print("영양 점수 계산 중...")
    
    def calculate_nutrition_scores(row):
        """각 행에 대해 영양 점수 계산"""
        # 임시 Food 객체 생성 (DB에 저장하지 않고 계산만 위해)
        class TempFood:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)
        
        temp_food = TempFood({
            'calorie': row.get('calorie', 0),
            'moisture': row.get('moisture', 0),
            'protein': row.get('protein', 0),
            'fat': row.get('fat', 0),
            'carbohydrate': row.get('carbohydrate', 0),
            'sugar': row.get('sugar', 0),
            'dietary_fiber': row.get('dietary_fiber', 0),
            'salt': row.get('salt', 0),
            'saturated_fatty_acids': row.get('saturated_fatty_acids', 0),
            'trans_fatty_acids': row.get('trans_fatty_acids', 0),
            'serving_size': row.get('serving_size', None),
            'weight': row.get('weight', 100),
            'food_category': row.get('food_category', ''),
        })
        
        try:
            nutrition_score = NutritionalScore(temp_food)
            nutri_grade = letterGrade(temp_food)
            # nrf_index는 일단 None으로 (구현되어 있지 않음)
            return nutrition_score, nutri_grade, None
        except:
            return None, None, None
    
    # 각 행에 대해 영양 점수 계산
    nutrition_data = out.apply(calculate_nutrition_scores, axis=1, result_type='expand')
    out['nutrition_score'] = nutrition_data[0]
    out['nutri_score_grade'] = nutrition_data[1] 
    out['nrf_index'] = nutrition_data[2]
    
    safe_print(f"영양 점수 계산 완료! A급: {(out['nutri_score_grade'] == 'A').sum()}개")
    safe_print(f"B급: {(out['nutri_score_grade'] == 'B').sum()}개, C급: {(out['nutri_score_grade'] == 'C').sum()}개")
    
    cols = [
        'food_id','food_img','food_name','food_category','representative_food',
        'nutritional_value_standard_amount','calorie','moisture','protein','fat',
        'carbohydrate','sugar','dietary_fiber','calcium','iron_content','phosphorus',
        'potassium','salt','VitaminA','VitaminB','VitaminC','VitaminD','VitaminE',
        'cholesterol','saturated_fatty_acids','trans_fatty_acids','serving_size',
        'weight','company_name','nutrition_score','nutri_score_grade','nrf_index',
        'shop_name','price','discount_price','shop_url','image_url'
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
        _img_nonempty = int((out['image_url'].notna()) & (out['image_url'].astype(str).str.strip() != '')).sum()
        _url_nonempty = int((out['shop_url'].notna()) & (out['shop_url'].astype(str).str.strip() != '')).sum()
        safe_print("incoming non-empty image_url rows:", _img_nonempty)
        safe_print("incoming non-empty shop_url rows:", _url_nonempty)
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
        if c in ('image_url', 'shop_url'):
            # If the incoming value is NULL or empty string, keep the existing DB value
            set_parts.append(f"{c}=COALESCE(NULLIF(excluded.{c}, ''), {c})")
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