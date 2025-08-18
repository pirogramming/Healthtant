#!/usr/bin/env python3
"""
manufacturer_mappings.csv의 제조사명을 mallName 필드에 업데이트하는 스크립트
배포 서버에서 실행: python update_mallname.py
"""

import os
import sys
import django
import csv

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

from foods.models import Food

def main():
    csv_path = 'manufacturer_mappings.csv'
    
    if not os.path.exists(csv_path):
        print(f"파일을 찾을 수 없습니다: {csv_path}")
        return
    
    updated = 0
    not_found = 0
    
    print("manufacturer_mappings.csv에서 제조사명을 mallName으로 업데이트 중...")
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            food_id = row['food_id']
            manufacturer = row['제조사명']
            
            try:
                food = Food.objects.get(food_id=food_id)
                food.mallName = manufacturer
                food.save(update_fields=['mallName'])
                updated += 1
                
                if updated <= 5:
                    print(f'업데이트: {food_id} → {manufacturer}')
                    
            except Food.DoesNotExist:
                not_found += 1
    
    print(f'\n완료!')
    print(f'업데이트된 레코드: {updated}개')
    print(f'찾을 수 없는 레코드: {not_found}개')
    
    # 결과 확인
    total_mallname = Food.objects.filter(mallName__isnull=False).exclude(mallName='').count()
    print(f'전체 mallName이 있는 레코드: {total_mallname}개')

if __name__ == "__main__":
    main()