import os, sys
import pandas as pd
from django.db import transaction
import django

# 프로젝트 루트 경로 추가
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# Django 세팅
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from foods.models import Food

def update_mallname():
    """food_clean_mallname.csv의 shop_name 데이터를 mallName 필드에 업데이트"""
    
    csv_path = os.path.join(BASE_DIR, 'food_clean_mallname.csv')
    
    if not os.path.exists(csv_path):
        print(f"ERROR: {csv_path} 파일이 존재하지 않습니다.")
        return
    
    # CSV 파일 읽기
    try:
        df = pd.read_csv(csv_path, dtype=str)
        print(f"CSV 파일 로드 완료: {len(df)}개 행")
        print(f"컬럼: {list(df.columns)}")
    except Exception as e:
        print(f"CSV 파일 읽기 오류: {e}")
        return
    
    # 필요한 컬럼 확인
    required_cols = ['food_id', 'shop_name']
    if not all(col in df.columns for col in required_cols):
        print(f"ERROR: 필요한 컬럼이 없습니다. 필요: {required_cols}, 실제: {list(df.columns)}")
        return
    
    # 빈 값 제거
    df = df.dropna(subset=['food_id', 'shop_name'])
    df = df[df['shop_name'].str.strip() != '']
    print(f"유효한 데이터: {len(df)}개 행")
    
    if len(df) == 0:
        print("업데이트할 데이터가 없습니다.")
        return
    
    # 데이터베이스 업데이트
    updated_count = 0
    not_found_count = 0
    
    with transaction.atomic():
        for _, row in df.iterrows():
            food_id = row['food_id'].strip()
            shop_name = row['shop_name'].strip()
            
            try:
                food = Food.objects.get(food_id=food_id)
                food.mallName = shop_name
                food.save(update_fields=['mallName'])
                updated_count += 1
                
                if updated_count % 100 == 0:
                    print(f"진행상황: {updated_count}개 업데이트 완료")
                    
            except Food.DoesNotExist:
                not_found_count += 1
                if not_found_count <= 5:  # 처음 5개만 출력
                    print(f"찾을 수 없는 food_id: {food_id}")
            except Exception as e:
                print(f"업데이트 오류 (food_id: {food_id}): {e}")
    
    print(f"\n=== 완료 ===")
    print(f"업데이트된 제품: {updated_count}개")
    print(f"찾을 수 없는 제품: {not_found_count}개")
    
    # 결과 확인
    total_foods = Food.objects.count()
    foods_with_mallname = Food.objects.filter(mallName__isnull=False).exclude(mallName='').count()
    print(f"전체 제품: {total_foods}개")
    print(f"mallName이 있는 제품: {foods_with_mallname}개")
    
    # 샘플 mallName 출력
    sample_mallnames = list(Food.objects.exclude(mallName='').exclude(mallName__isnull=True).values_list('mallName', flat=True).distinct()[:10])
    print(f"샘플 mallName: {sample_mallnames}")

if __name__ == "__main__":
    update_mallname()