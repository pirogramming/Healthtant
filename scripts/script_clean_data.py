import pandas as pd
import requests
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

def is_valid_image_url(url):
    """이미지 URL이 유효한지 확인"""
    if pd.isna(url) or url == '' or url.strip() == '':
        return False
    
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
        
        # HEAD 요청으로 이미지 존재 여부 확인
        response = requests.head(url, timeout=5, allow_redirects=True)
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
    
    non_food_keywords = [
        'bs1', 'st1', '브레이버스', '쿠키런', '카드', '게임', '토이', '장난감', 
        '피규어', '스티커', '굿즈', '액세서리', '컵', '텀블러', '머그', 
        '그릇', '접시', '수저', '포스터', '엽서', '키링', '배지', '펜', 
        '노트', '다이어리', '포켓몬', '디즈니', '케이스', '파우치', '가방',
        '지갑', '의류', '옷', '모자', '책', '매뉴얼', '가이드', 'dvd', 
        'cd', '음반', '앨범', '와펜', '패치', '다림질', '데코덴', '탑로더',
        '폰케이스', '슬리퍼', '샌달', '자비츠'
    ]
    
    return any(keyword in combined_text for keyword in non_food_keywords)

def has_valid_price(lprice, hprice, category):
    """가격 정보가 유효한지 확인 (카테고리별 기준 적용)"""
    # 기본 가격 유효성 확인
    lprice_numeric = pd.to_numeric(lprice, errors='coerce')
    hprice_numeric = pd.to_numeric(hprice, errors='coerce')
    
    # 둘 다 NaN이면 False
    if pd.isna(lprice_numeric) and pd.isna(hprice_numeric):
        return False
    
    # 유효한 가격 선택 (lprice 우선)
    price = lprice_numeric if not pd.isna(lprice_numeric) else hprice_numeric
    
    # 카테고리별 최소 가격 기준
    category_thresholds = {
        '빵류': 500,         # 중앙값 2,320원, 하위10% 200원
        '과자': 500,         # 중앙값 1,890원, 하위10% 210원  
        '캔디류': 500,       # 중앙값 1,800원, 하위10% 200원
        '소스': 400,         # 중앙값 1,770원, 하위10% 150원
        '즉석조리식품': 1000, # 중앙값 3,200원, 하위10% 670원
        '즉석섭취식품': 800,  # 중앙값 2,980원, 하위10% 550원
        '과·채주스': 800,    # 중앙값 4,000원, 하위10% 380원
        '혼합음료': 800,     # 중앙값 3,000원, 하위10% 350원
        '양념육': 800,       # 중앙값 3,900원, 하위10% 500원
    }
    
    # 기본 최소 가격 (카테고리가 없거나 매핑되지 않은 경우)
    min_price = category_thresholds.get(category, 800)
    
    return price >= min_price

def validate_row(args):
    """행의 이미지, 가격, 비식품 필터링 검증"""
    idx, row = args
    image_url = row['image']
    lprice = row['lprice']
    hprice = row['hprice']
    category = row['food_category']
    naver_title = row['naver_title']
    food_name = row['food_name']
    
    # 1. 비식품 상품 필터링 (가장 빠름)
    if is_non_food_item(naver_title, food_name):
        return idx, False
    
    # 2. 가격 확인 (카테고리별 기준)
    if not has_valid_price(lprice, hprice, category):
        return idx, False
    
    # 3. 이미지 URL 확인 (가장 느림)
    if is_valid_image_url(image_url):
        return idx, True
    
    return idx, False

def clean_foods_csv(input_file, output_file, max_workers=20):
    """이미지나 가격이 없는 food를 삭제하고 새 CSV 파일로 저장"""
    print("CSV 파일을 읽는 중...")
    df = pd.read_csv(input_file)
    
    print(f"총 {len(df)}개의 행이 있습니다.")
    
    # 스레드 안전한 카운터
    completed_count = [0]
    lock = threading.Lock()
    
    def update_progress():
        with lock:
            completed_count[0] += 1
            if completed_count[0] % 100 == 0:
                print(f"진행률: {completed_count[0]}/{len(df)} ({completed_count[0]/len(df)*100:.1f}%)")
    
    print("이미지, 가격, 비식품 필터링 검사 중... (멀티스레딩)")
    valid_indices = set()
    
    # 멀티스레딩으로 병렬 처리
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 모든 행에 대해 작업 제출
        future_to_idx = {
            executor.submit(validate_row, (idx, row)): idx 
            for idx, row in df.iterrows()
        }
        
        # 결과 수집
        for future in as_completed(future_to_idx):
            idx, is_valid = future.result()
            if is_valid:
                valid_indices.add(idx)
            update_progress()
    
    # 유효한 행들만 필터링
    cleaned_df = df.loc[list(valid_indices)].copy()
    
    print(f"정리 완료: {len(df)}개 행 → {len(cleaned_df)}개 행")
    print(f"{len(df) - len(cleaned_df)}개의 행이 삭제되었습니다.")
    
    # 새 CSV 파일로 저장
    cleaned_df.to_csv(output_file, index=False)
    print(f"정리된 데이터가 '{output_file}'에 저장되었습니다.")

if __name__ == "__main__":
    input_file = "../food_raw_data.csv"
    output_file = "../food_clean_data.csv"
    
    clean_foods_csv(input_file, output_file)