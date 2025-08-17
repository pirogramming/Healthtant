import os, sys
import pandas as pd
import requests
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import django
from django.db import connection, transaction

# 프로젝트 루트 경로 추가
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# Django 세팅
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

# 모델/점수 함수 import
from foods.models import Food
from common.nutrition_score import NutritionalScore, letterGrade

def safe_print(*args):
    try:
        s = " ".join(str(a) for a in args)
        sys.stdout.write(s + "\n")
    except Exception:
        s = " ".join(str(a) for a in args)
        sys.stdout.write(s.encode('utf-8', 'replace').decode('utf-8') + "\n")

def is_valid_image_url(url):
    """이미지 URL이 유효한지 확인"""
    if pd.isna(url) or url == '' or url.strip() == '':
        return False
    
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        
        # HEAD 요청으로 이미지 존재 여부 확인 (타임아웃 짧게)
        response = requests.head(url, timeout=3, allow_redirects=True)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            return content_type.startswith('image/')
        return False
    except:
        return False

def is_non_food_item(naver_title, food_name):
    """비식품 상품인지 확인"""
    if pd.isna(naver_title):
        naver_title = ''
    if pd.isna(food_name):
        food_name = ''
    
    combined_text = (str(naver_title) + ' ' + str(food_name)).lower()
    
    # 더 정교한 비식품 키워드 리스트
    non_food_keywords = [
        'bs1', 'st1', '브레이버스', '쿠키런', '카드', '게임', '토이', '장난감', 
        '피규어', '스티커', '굿즈', '액세서리', '컵', '텀블러', '머그', 
        '그릇', '접시', '수저', '포스터', '엽서', '키링', '배지', '펜', 
        '노트', '다이어리', '포켓몬', '디즈니', '케이스', '파우치', '가방',
        '지갑', '의류', '옷', '모자', '책', '매뉴얼', '가이드', 'dvd', 
        'cd', '음반', '앨범', '와펜', '패치', '다림질', '데코덴', '탑로더',
        '폰케이스', '슬리퍼', '샌달', '자비츠', '풀빵', '쿠키', 'cookie',
        # 추가 키워드들
        '마그넷', '뱃지', '홀더', '파우치', '세트', '한정판', 'vol', '시즌',
        '컬렉션', '한정', '특별판', '프리미엄', '에디션', '버전',
        # 바나나 관련 키워드들
        '나라사랑 족발편육', '연세대학교연세바나나우유', '뽀로로가 좋아하는 바나나우유',
        '붕장어(아나고)회/필렛', '새송이버섯나물 밀키트', '애호박나물', '취나물무침 (2개)',
        '선물세트 달보드레_하나', '몽키나나', '쇼콜라 판나코타', '앙버터모나카 (2개)',
        '가나슈데니쉬식빵', '가나소프트콘', '연세우유 초코 모나카', '주문하신 카페라떼 나왔습니다',
        '마켓진양호 시나몬라떼', '다크나이트(DARK KNIGHT)', '오나의살들아',
        '데일리슬림쉐이크 바나나', '양수면옥 건호박나물볶음', '칼집요리비엔나',
        '연세바나나우유', '나는 미니김', '정월대보름나물', '미니콘 바나나',
        '만나마카롱3구SET', '바나나머랭쿠키 (2개)', '바나나샌드웨이퍼',
        # 추가 키워드들
        '이삭시그니처', '버터롤', '미라클 블렌드', '요거트비스켓', '백합막장용메주가루',
        '한입 우리콩 두부과자', '두부바게트', '야채두부버터빵', '프로틴플러스두유두부식빵',
        '두부 치즈케이크', '곰곰 우리콩두부', '소이요 백태 전두부', '순두부 치즈 그라탕 볼로네제',
        '우리 쌀콩 미숫가루', '못말림 블렌드', '월넛 브레드', '스키니팝콘', '보리바게트',
        '찐크 프로틴 크래커(참깨맛)', '17곡미숫가루A+', '포시즌블렌드', '알바 블랜드'
    ]
    
    # 의심스러운 패턴들
    suspicious_patterns = [
        '풀빵', '쿠키 런', '게임용', '게임 아이템', '캐릭터', '콜라보',
        '한정 상품', '특별 상품', '이벤트', '기념품'
    ]
    
    # 키워드 체크
    for keyword in non_food_keywords:
        if keyword in combined_text:
            return True
    
    # 패턴 체크
    for pattern in suspicious_patterns:
        if pattern in combined_text:
            return True
    
    return False

def has_valid_price(lprice, hprice, category):
    """가격 정보가 유효한지 확인 (카테고리별 기준 적용)"""
    lprice_numeric = pd.to_numeric(lprice, errors='coerce')
    hprice_numeric = pd.to_numeric(hprice, errors='coerce')
    
    # 둘 다 NaN이면 False
    if pd.isna(lprice_numeric) and pd.isna(hprice_numeric):
        return False
    
    # 유효한 가격 선택 (lprice 우선)
    price = lprice_numeric if not pd.isna(lprice_numeric) else hprice_numeric
    
    # 너무 높은 가격도 필터링 (100만원 이상)
    if price > 1000000:
        return False
    
    # 카테고리별 최소 가격 기준
    category_thresholds = {
        '빵류': 300,         
        '과자': 300,         
        '캔디류': 300,       
        '소스': 400,         
        '즉석조리식품': 800, 
        '즉석섭취식품': 600,  
        '과·채주스': 600,    
        '혼합음료': 600,     
        '양념육': 600,       
    }
    
    # 기본 최소 가격 (더 엄격하게)
    min_price = category_thresholds.get(category, 500)
    
    return price >= min_price

def has_valid_nutrition_data(row):
    """필수 영양소 데이터가 있는지 확인"""
    required_nutrients = ['calorie', 'protein', 'fat', 'carbohydrate']
    
    for nutrient in required_nutrients:
        value = pd.to_numeric(row.get(nutrient, 0), errors='coerce')
        if pd.isna(value) or value < 0:
            return False
    
    # 칼로리가 너무 높거나 낮은 경우 (100g 기준)
    calorie = pd.to_numeric(row.get('calorie', 0), errors='coerce')
    if calorie > 800 or calorie < 1:  # 100g 기준 800칼로리 초과 또는 1칼로리 미만
        return False
    
    return True

def validate_and_clean_row(args):
    """행의 모든 검증을 수행하고 정리된 데이터 반환"""
    idx, row = args
    
    # 1. 비식품 상품 필터링
    if is_non_food_item(row.get('naver_title', ''), row.get('food_name', '')):
        return idx, None, "비식품 상품"
    
    # 2. 필수 영양소 데이터 확인
    if not has_valid_nutrition_data(row):
        return idx, None, "영양소 데이터 부족"
    
    # 3. 가격 확인
    if not has_valid_price(row.get('lprice'), row.get('hprice'), row.get('food_category')):
        return idx, None, "가격 정보 부족"
    
    # 4. 이미지 URL 확인 (시간이 가장 오래 걸림)
    if not is_valid_image_url(row.get('image')):
        return idx, None, "이미지 URL 무효"
    
    # 5. 데이터 정리
    cleaned_row = {}
    
    # 문자열 필드 정리 (길이 제한 적용)
    string_fields = {
        'food_name': (row.get('food_name', ''), 255),
        'food_category': (row.get('food_category', ''), 255),
        'representative_food': (row.get('representative_food', ''), 255),
        'company_name': (row.get('company_name', ''), 255),
        'shop_name': (row.get('mallName', ''), 100),
        'nutri_score_grade': (row.get('nutri_score_grade', ''), 10),
    }
    
    for field, (value, max_length) in string_fields.items():
        cleaned_value = str(value).strip() if pd.notna(value) else ''
        # 길이 제한 적용
        if cleaned_value and len(cleaned_value) > max_length:
            cleaned_value = cleaned_value[:max_length]
        
        if field in ['food_name', 'food_category', 'representative_food', 'company_name']:
            cleaned_row[field] = cleaned_value or 'UNKNOWN'
        else:
            cleaned_row[field] = cleaned_value or None
    
    # 숫자 필드 정리
    float_fields = [
        'calorie', 'moisture', 'protein', 'fat', 'carbohydrate', 'sugar', 
        'dietary_fiber', 'calcium', 'iron_content', 'phosphorus', 'potassium', 
        'salt', 'VitaminA', 'VitaminB', 'VitaminC', 'VitaminD', 'VitaminE', 
        'cholesterol', 'saturated_fatty_acids', 'trans_fatty_acids', 
        'serving_size', 'weight', 'nutrition_score', 'nrf_index'
    ]
    
    for field in float_fields:
        value = pd.to_numeric(row.get(field, None), errors='coerce')
        if field in ['calorie', 'moisture', 'protein', 'fat', 'carbohydrate', 'weight']:
            cleaned_row[field] = value if pd.notna(value) else 0.0
        else:
            cleaned_row[field] = value if pd.notna(value) else None
    
    # 정수 필드 정리
    int_fields = ['nutritional_value_standard_amount', 'price', 'discount_price']
    for field in int_fields:
        value = pd.to_numeric(row.get(field if field != 'price' else 'lprice', None), errors='coerce')
        if field == 'discount_price':
            value = pd.to_numeric(row.get('hprice', None), errors='coerce')
        if field == 'nutritional_value_standard_amount':
            cleaned_row[field] = int(value) if pd.notna(value) else 0
        else:
            cleaned_row[field] = int(value) if pd.notna(value) else None
    
    # URL 필드 정리 (길이 제한 적용)
    url_fields = ['food_img', 'shop_url', 'image_url']
    for field in url_fields:
        source_field = field
        if field == 'image_url':
            source_field = 'image'
        elif field == 'shop_url':
            source_field = 'product_link'
        
        value = str(row.get(source_field, '')).strip() if pd.notna(row.get(source_field)) else ''
        # URL 길이 제한 (200자)
        if value and len(value) > 200:
            value = value[:200]
        cleaned_row[field] = value if value else None
    
    # food_id 설정 (길이 제한 50자)
    food_id = str(row.get('food_id', '')).strip()
    if len(food_id) > 50:
        food_id = food_id[:50]
    cleaned_row['food_id'] = food_id
    
    return idx, cleaned_row, "유효"

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
    """기존 스크립트의 CSV 읽기 함수 사용"""
    try:
        df = pd.read_csv(path, sep=None, engine='python', dtype=str, encoding='utf-8-sig')
        if df.shape[1] > 1:
            return df
    except Exception:
        pass
    try:
        df = pd.read_csv(path, sep='\t', engine='python', dtype=str, encoding='utf-8-sig')
        if df.shape[1] > 1:
            return df
    except Exception:
        pass
    try:
        df = pd.read_csv(path, sep=',', engine='python', dtype=str, encoding='utf-8-sig')
        if df.shape[1] > 1:
            return df
    except Exception:
        pass
    try:
        df = pd.read_csv(path, sep=None, engine='python', dtype=str, encoding='cp949', on_bad_lines='skip')
        if df.shape[1] > 1:
            return df
    except Exception:
        pass
    df = pd.read_csv(path, sep=',', engine='python', dtype=str, encoding='cp949', on_bad_lines='skip')
    return df

def purge_foods_and_children_auto():
    """기존 DB 데이터 삭제"""
    with transaction.atomic():
        for rel in Food._meta.related_objects:
            model = rel.related_model
            try:
                qs = model._default_manager.all()
                try:
                    qs = qs.order_by()
                except Exception:
                    pass
                qs.delete()
            except Exception:
                pass
        Food.objects.all().order_by().delete()

def calculate_nutrition_scores(row):
    """영양 점수 계산"""
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
        return nutrition_score, nutri_grade, None
    except:
        return None, None, None

def main():
    safe_print("=== 깨끗한 데이터베이스 재구축 시작 ===")
    
    # 1. 기존 데이터 삭제
    safe_print("기존 DB 데이터 삭제 중...")
    purge_foods_and_children_auto()
    safe_print("기존 데이터 삭제 완료")
    
    # 2. 클린 CSV 파일 읽기
    clean_csv_path = os.path.join(BASE_DIR, 'food_clean_data.csv')
    if not os.path.exists(clean_csv_path):
        safe_print(f"ERROR: {clean_csv_path} 파일이 존재하지 않습니다.")
        return
    
    safe_print("클린 CSV 파일 읽는 중...")
    df = read_csv_smart(clean_csv_path).fillna('')
    
    # BOM/공백 제거
    df.columns = df.columns.str.replace('\ufeff', '', regex=False).str.strip()
    
    safe_print(f"원본 데이터: {len(df)}개 행")
    safe_print("첫 10개 컬럼:", df.columns.tolist()[:10])
    
    # 3. 멀티스레딩으로 데이터 검증 및 정리
    safe_print("데이터 검증 및 정리 중... (멀티스레딩)")
    
    valid_rows = []
    stats = {'비식품 상품': 0, '영양소 데이터 부족': 0, '가격 정보 부족': 0, '이미지 URL 무효': 0, '유효': 0}
    
    completed_count = [0]
    lock = threading.Lock()
    
    def update_progress():
        with lock:
            completed_count[0] += 1
            if completed_count[0] % 500 == 0:
                safe_print(f"진행률: {completed_count[0]}/{len(df)} ({completed_count[0]/len(df)*100:.1f}%)")
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_idx = {
            executor.submit(validate_and_clean_row, (idx, row)): idx 
            for idx, row in df.iterrows()
        }
        
        for future in as_completed(future_to_idx):
            idx, cleaned_row, status = future.result()
            stats[status] += 1
            
            if cleaned_row:
                valid_rows.append(cleaned_row)
            
            update_progress()
    
    safe_print("\n=== 검증 결과 ===")
    for status, count in stats.items():
        safe_print(f"{status}: {count}개")
    
    if not valid_rows:
        safe_print("ERROR: 유효한 데이터가 없습니다.")
        return
    
    # 4. 영양 점수 계산
    safe_print("영양 점수 계산 중...")
    for row in valid_rows:
        nutrition_score, nutri_grade, nrf_index = calculate_nutrition_scores(row)
        row['nutrition_score'] = nutrition_score
        row['nutri_score_grade'] = nutri_grade
        row['nrf_index'] = nrf_index
    
    # 5. 데이터베이스에 삽입
    safe_print(f"데이터베이스에 {len(valid_rows)}개 행 삽입 중...")
    
    TABLE_NAME = Food._meta.db_table
    cols = [
        'food_id','food_img','food_name','food_category','representative_food',
        'nutritional_value_standard_amount','calorie','moisture','protein','fat',
        'carbohydrate','sugar','dietary_fiber','calcium','iron_content','phosphorus',
        'potassium','salt','"VitaminA"','"VitaminB"','"VitaminC"','"VitaminD"','"VitaminE"',
        'cholesterol','saturated_fatty_acids','trans_fatty_acids','serving_size',
        'weight','company_name','nutrition_score','nutri_score_grade','nrf_index',
        'shop_name','price','discount_price','shop_url','image_url'
    ]
    
    placeholders = ",".join(["%s"] * len(cols))
    sql = f"INSERT INTO {TABLE_NAME} ({', '.join(cols)}) VALUES ({placeholders})"
    
    records = []
    for row in valid_rows:
        record = []
        for col in cols:
            value = row.get(col)
            if hasattr(value, 'item'):  # numpy 타입 변환
                record.append(value.item())
            else:
                record.append(value)
        records.append(tuple(record))
    
    with transaction.atomic():
        with connection.cursor() as cur:
            chunk_size = 1000
            for i in range(0, len(records), chunk_size):
                cur.executemany(sql, records[i:i+chunk_size])
    
    # 6. 정리된 CSV 파일 저장
    clean_csv_path = os.path.join(BASE_DIR, 'food_clean_data_rebuild.csv')
    
    clean_df = pd.DataFrame(valid_rows)
    clean_df.to_csv(clean_csv_path, index=False, encoding='utf-8')
    
    safe_print(f"\n=== 완료 ===")
    safe_print(f"데이터베이스에 {len(valid_rows)}개 행 삽입 완료")
    safe_print(f"정리된 데이터가 '{clean_csv_path}'에 저장됨")
    safe_print(f"A급 영양소: {sum(1 for row in valid_rows if row.get('nutri_score_grade') == 'A')}개")
    safe_print(f"B급 영양소: {sum(1 for row in valid_rows if row.get('nutri_score_grade') == 'B')}개")
    safe_print(f"C급 영양소: {sum(1 for row in valid_rows if row.get('nutri_score_grade') == 'C')}개")

if __name__ == "__main__":
    main()