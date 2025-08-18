import pandas as pd
import os

def extract_manufacturers():
    """가공식품DB에서 제조사 정보 추출하여 현재 food_id와 매칭"""
    
    # 1. 가공식품DB 로드
    excel_file = '20250327_가공식품DB_147999건.xlsx'
    if not os.path.exists(excel_file):
        print(f"ERROR: {excel_file} 파일이 없습니다.")
        return
    
    print("가공식품DB 로딩 중...")
    df_full = pd.read_excel(excel_file, dtype=str)
    print(f"전체 가공식품DB: {len(df_full)}개 행")
    print(f"컬럼: {list(df_full.columns)}")
    
    # 2. 현재 food_clean_mallname.csv 로드
    current_file = 'food_clean_mallname.csv'
    if not os.path.exists(current_file):
        print(f"ERROR: {current_file} 파일이 없습니다.")
        return
    
    df_current = pd.read_csv(current_file, dtype=str)
    print(f"현재 데이터: {len(df_current)}개 행")
    current_food_ids = set(df_current['food_id'].tolist())
    
    # 3. food_id로 매칭하여 제조사 정보 추출
    print("\n=== 제조사 정보 매칭 중 ===")
    
    # 매칭 결과를 저장할 리스트
    manufacturer_mappings = []
    matched_count = 0
    
    for _, current_row in df_current.iterrows():
        food_id = current_row['food_id']
        
        # 가공식품DB에서 해당 식품코드 찾기
        matching_rows = df_full[df_full['식품코드'] == food_id]
        
        if len(matching_rows) > 0:
            manufacturer = matching_rows.iloc[0]['제조사명']
            if pd.notna(manufacturer) and str(manufacturer).strip() != '':
                manufacturer_mappings.append({
                    'food_id': food_id,
                    'food_name': current_row['food_name'], 
                    'manufacturer_name': str(manufacturer).strip()
                })
                matched_count += 1
    
    print(f"매칭된 제품: {matched_count}개 / {len(df_current)}개")
    
    # 4. 매칭 결과를 CSV로 저장
    if manufacturer_mappings:
        df_manufacturers = pd.DataFrame(manufacturer_mappings)
        output_file = 'manufacturer_mappings.csv'
        df_manufacturers.to_csv(output_file, index=False, encoding='utf-8')
        print(f"\n제조사 매핑 파일 생성: {output_file}")
        print(f"총 {len(df_manufacturers)}개 제품의 제조사 정보 추출 완료")
        
        # 샘플 출력
        print("\n=== 제조사 매핑 샘플 ===")
        for _, row in df_manufacturers.head(10).iterrows():
            print(f"{row['food_id']}: {row['food_name']} → {row['manufacturer_name']}")
    else:
        print("매칭된 제조사 정보가 없습니다.")

if __name__ == "__main__":
    extract_manufacturers()