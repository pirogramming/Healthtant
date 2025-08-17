import os, sys
import pandas as pd
from django.db import connection, transaction
import django

# 프로젝트 루트 경로 추가
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# Django 세팅
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
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
    # 0) 테이블 구조 확인
    safe_print("=== 테이블 구조 확인 중... ===")
    with connection.cursor() as cur:
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'food' ORDER BY ordinal_position;")
        db_columns = [row[0] for row in cur.fetchall()]
        safe_print("실제 DB 컬럼 전체:", db_columns)
    
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
        'shop_url': 'shop_url',
        'image_url': 'image_url',
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
    
    # image 컬럼을 food_img에도 복사 (메인페이지용)
    if 'image_url' in out.columns:
        out['food_img'] = out['image_url']

    # Normalize media/link fields: empty string -> None, strip spaces
    if 'image_url' in out.columns:
        out['image_url'] = out['image_url'].astype(str).str.strip().replace({'': None})
    if 'food_img' in out.columns:
        out['food_img'] = out['food_img'].astype(str).str.strip().replace({'': None})
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
    
    # 모든 문자열 컬럼을 200자로 제한 (PostgreSQL 제한에 맞춤)
    for col in out.columns:
        if out[col].dtype == 'object':  # 문자열 컬럼
            out[col] = out[col].astype(str).str[:200]
    
    # 특별히 짧은 컬럼들
    if 'nutri_score_grade' in out.columns:
        out['nutri_score_grade'] = out['nutri_score_grade'].astype(str).str[:3]
    
    # external_code 컬럼 추가 (DB에 있지만 CSV에는 없음)
    if 'external_code' not in out.columns:
        out['external_code'] = None
    
    # 5) 영양 점수 계산 및 추가
    safe_print("영양 점수 계산 중...")
    
    def calculate_nutrition_scores(row):
        """각 행에 대해 영양 점수 계산"""
        # 임시 Food 객체 생성 (DB에 저장하지 않고 계산만 위해)
        class TempFood:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)
        
        def safe_float(val, default=0):
            try:
                if pd.isna(val) or val is None:
                    return default if default is not None else 0.0
                val_str = str(val).strip().lower()
                if val_str in ['', 'none', 'nan']:
                    return default if default is not None else 0.0
                return float(val)
            except:
                return default if default is not None else 0.0
        
        temp_food = TempFood({
            'calorie': safe_float(row['calorie'], 0),
            'moisture': safe_float(row['moisture'], 0),
            'protein': safe_float(row['protein'], 0),
            'fat': safe_float(row['fat'], 0),
            'carbohydrate': safe_float(row['carbohydrate'], 0),
            'sugar': safe_float(row['sugar'], 0),
            'dietary_fiber': safe_float(row['dietary_fiber'], 0),
            'salt': safe_float(row['salt'], 0),
            'saturated_fatty_acids': safe_float(row['saturated_fatty_acids'], 0),
            'trans_fatty_acids': safe_float(row['trans_fatty_acids'], 0),
            'serving_size': safe_float(row['serving_size'], None) if pd.notna(row['serving_size']) else None,
            'weight': safe_float(row['weight'], 100),
            'food_category': str(row['food_category']) if pd.notna(row['food_category']) else '',
        })
        
        try:
            nutrition_score = NutritionalScore(temp_food)
            nutri_grade = letterGrade(temp_food)
            return nutrition_score, nutri_grade, None
        except Exception as e:
            # 디버깅용 출력 (첫 몇 개만)
            if hasattr(calculate_nutrition_scores, 'error_count'):
                calculate_nutrition_scores.error_count += 1
            else:
                calculate_nutrition_scores.error_count = 1
            
            if calculate_nutrition_scores.error_count <= 3:
                safe_print(f"영양점수 계산 오류: {e}")
            return None, None, None
    
    # 각 행에 대해 영양 점수 계산
    nutrition_data = out.apply(calculate_nutrition_scores, axis=1, result_type='expand')
    out['nutrition_score'] = nutrition_data[0]
    out['nutri_score_grade'] = nutrition_data[1] 
    out['nrf_index'] = nutrition_data[2]
    
    safe_print(f"영양 점수 계산 완료! A급: {(out['nutri_score_grade'] == 'A').sum()}개")
    safe_print(f"B급: {(out['nutri_score_grade'] == 'B').sum()}개, C급: {(out['nutri_score_grade'] == 'C').sum()}개")
    
    # 실제 DB 컬럼과 일치하는 컬럼만 사용
    cols = [col for col in db_columns if col in out.columns or col in ['nutrition_score', 'nutri_score_grade', 'nrf_index']]
    
    # 누락된 컬럼들을 None으로 추가
    for c in db_columns:
        if c not in out.columns:
            out[c] = None
    
    # DB 컬럼 순서대로 정렬
    out = out[db_columns]
    cols = db_columns

    # PK 비어있는 행 제거
    out = out[out['food_id'].astype(str).str.strip().ne('')]

    n = len(out)
    safe_print("will upsert rows:", n)

    # Debug counters for incoming media fields
    try:
        _img_nonempty = ((out['image_url'].notna()) & (out['image_url'].astype(str).str.strip() != '')).sum()
        _url_nonempty = int((out['shop_url'].notna()) & (out['shop_url'].astype(str).str.strip() != '')).sum()
        safe_print("incoming non-empty image_url rows:", _img_nonempty)
        safe_print("incoming non-empty shop_url rows:", _url_nonempty)
    except Exception:
        pass

    if n == 0:
        safe_print("ERROR: no rows to upsert.")
        return

    # 6) UPSERT - PostgreSQL에서 대소문자 구분을 위해 따옴표 사용
    placeholders = ",".join(["%s"] * len(cols))
    # 컬럼명을 따옴표로 감싸기
    quoted_cols = [f'"{c}"' for c in cols]
    
    # Build SET clause for UPSERT with "keep existing if incoming is empty/NULL" for selected columns
    set_parts = []
    for c in cols:
        if c == 'food_id':
            continue
        quoted_c = f'"{c}"'
        if c in ('image_url', 'shop_url'):
            # If the incoming value is NULL or empty string, keep the existing DB value
            set_parts.append(f'{quoted_c}=COALESCE(NULLIF(excluded.{quoted_c}, \'\'), {TABLE_NAME}.{quoted_c})')
        else:
            set_parts.append(f'{quoted_c}=excluded.{quoted_c}')
    set_clause = ",\n".join(set_parts)
    sql = f"""
    INSERT INTO {TABLE_NAME} ({", ".join(quoted_cols)})
    VALUES ({placeholders})
    ON CONFLICT("food_id") DO UPDATE SET
    {set_clause};
    """

    # numpy 타입을 Python 네이티브 타입으로 변환
    def convert_value(val):
        if pd.isna(val):
            return None
        if val is None:
            return None
        if str(val).lower() in ['none', 'nan', '']:
            return None
        if hasattr(val, 'item'):  # numpy scalar
            return val.item()
        return val
    
    records = [tuple(convert_value(val) for val in out.iloc[i].tolist()) for i in range(n)]

    with transaction.atomic():
        with connection.cursor() as cur:
            chunk = 1000
            for i in range(0, n, chunk):
                cur.executemany(sql, records[i:i+chunk])

    safe_print("DONE: food upsert rows:", n)

if __name__ == "__main__":
    main()