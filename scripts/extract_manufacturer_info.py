#!/usr/bin/env python3
"""
20250327_가공식품DB_147999건.xlsx에서 제조사 정보를 추출하여
food_clean_data.csv의 company_name을 업데이트하는 스크립트
"""

import pandas as pd

def main():
    print("제조사 정보 추출 및 매핑 시작...")
    
    try:
        # 1. 원본 Excel 파일 읽기
        print("20250327_가공식품DB_147999건.xlsx 로딩 중...")
        df_original = pd.read_excel('/Users/kimminji/Desktop/Healthtant/20250327_가공식품DB_147999건.xlsx')
        print(f"원본 데이터: {len(df_original)}개 행")
        
        # 2. food_clean_data.csv 읽기
        print("food_clean_data.csv 로딩 중...")
        df_food = pd.read_csv('/Users/kimminji/Desktop/Healthtant/food_clean_data.csv')
        print(f"현재 식품 데이터: {len(df_food)}개 행")
        
        # 3. 제조사 정보 추출 (식품코드 -> 제조사명)
        manufacturer_mapping = {}
        for idx, row in df_original.iterrows():
            food_code = str(row['식품코드']).strip()
            manufacturer = str(row['제조사명']).strip() if pd.notna(row['제조사명']) else ''
            
            # 제조사명이 없으면 수입업체명이나 유통업체명 사용
            if not manufacturer or manufacturer == 'nan':
                manufacturer = str(row['수입업체명']).strip() if pd.notna(row['수입업체명']) else ''
            if not manufacturer or manufacturer == 'nan':
                manufacturer = str(row['유통업체명']).strip() if pd.notna(row['유통업체명']) else ''
                
            if manufacturer and manufacturer != 'nan':
                manufacturer_mapping[food_code] = manufacturer
        
        print(f"제조사 정보를 찾은 식품: {len(manufacturer_mapping)}개")
        
        # 4. food_clean_data.csv의 company_name 업데이트
        updated_count = 0
        for idx, row in df_food.iterrows():
            food_id = str(row['food_id']).strip()
            if food_id in manufacturer_mapping:
                df_food.at[idx, 'company_name'] = manufacturer_mapping[food_id]
                updated_count += 1
        
        print(f"업데이트된 식품: {updated_count}개")
        
        # 5. 업데이트된 CSV 저장
        output_file = '/Users/kimminji/Desktop/Healthtant/food_clean_data_updated.csv'
        df_food.to_csv(output_file, index=False, encoding='utf-8')
        print(f"업데이트된 파일 저장: {output_file}")
        
        # 6. 통계 출력
        total_foods = len(df_food)
        foods_with_manufacturer = len(df_food[df_food['company_name'].notna() & (df_food['company_name'] != '') & (df_food['company_name'] != 'UNKNOWN')])
        print(f"\n=== 통계 ===")
        print(f"전체 식품: {total_foods}개")
        print(f"제조사 정보 있음: {foods_with_manufacturer}개 ({foods_with_manufacturer/total_foods*100:.1f}%)")
        
        # 7. 샘플 데이터 확인
        print(f"\n=== 업데이트된 샘플 데이터 ===")
        sample = df_food[df_food['company_name'].notna() & (df_food['company_name'] != '') & (df_food['company_name'] != 'UNKNOWN')].head(10)
        for _, row in sample.iterrows():
            print(f"ID: {row['food_id']}, 식품명: {row['food_name']}, 제조사: {row['company_name']}")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()