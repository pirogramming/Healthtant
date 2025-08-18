import os
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from foods.models import Food

# mallName 업데이트 데이터 (CSV에서 추출한 일부)
update_data = [
    ('P101-101000100-0103', '쿠팡'),
    ('P101-101000100-0005', '까까팡'),
    ('P101-101000100-0061', 'SSG닷컴'),
    ('P101-101000100-0057', 'G마켓'),
    ('P101-101000100-0053', 'GS더프레시'),
    ('P101-101000100-0038', 'G마켓'),
    ('P101-101000100-0080', '네이버'),
    ('P101-101000100-0007', '쿠팡'),
    ('P101-101000100-0089', '자연박사'),
    ('P101-101000100-0027', '네이버'),
]

print("mallName 업데이트 시작...")
updated = 0
for food_id, shop_name in update_data:
    try:
        food = Food.objects.get(food_id=food_id)
        food.mallName = shop_name
        food.save(update_fields=['mallName'])
        updated += 1
        print(f"업데이트: {food_id} -> {shop_name}")
    except Food.DoesNotExist:
        print(f"찾을 수 없음: {food_id}")
    except Exception as e:
        print(f"오류: {food_id} - {e}")

print(f"총 {updated}개 업데이트 완료")

# 결과 확인
total = Food.objects.count()
with_mallname = Food.objects.filter(mallName__isnull=False).exclude(mallName='').count()
print(f"전체 제품: {total}개, mallName 있는 제품: {with_mallname}개")
