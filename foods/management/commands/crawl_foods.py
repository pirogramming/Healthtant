import requests
from bs4 import BeautifulSoup
import json
import time
from django.core.management.base import BaseCommand
from django.db import transaction
from foods.models import Food, Price
import uuid

class Command(BaseCommand):
    help = '식품 정보를 크롤링하여 데이터베이스에 저장합니다.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            default='sample',
            help='크롤링할 소스 (sample, real)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='크롤링할 제품 수 제한'
        )

    def handle(self, *args, **options):
        source = options['source']
        limit = options['limit']
        
        self.stdout.write(f'식품 정보 크롤링을 시작합니다. (소스: {source}, 제한: {limit})')
        
        if source == 'sample':
            self.crawl_sample_data(limit)
        elif source == 'real':
            self.crawl_real_data(limit)
        else:
            self.stdout.write(self.style.ERROR('지원하지 않는 소스입니다.'))
            return
        
        self.stdout.write(self.style.SUCCESS('크롤링이 완료되었습니다.'))

    def crawl_sample_data(self, limit):
        """샘플 데이터 생성 (실제 크롤링 대신 테스트용 데이터)"""
        sample_foods = [
            {
                'food_name': '삼성 라면',
                'food_category': '면류',
                'representative_food': '라면',
                'calorie': 350,
                'protein': 8.5,
                'fat': 12.0,
                'carbohydrate': 55.0,
                'sugar': 2.0,
                'dietary_fiber': 2.5,
                'salt': 1200,
                'company_name': '삼성식품',
                'weight': 120,
            },
            {
                'food_name': '농심 새우깡',
                'food_category': '과자류',
                'representative_food': '과자',
                'calorie': 520,
                'protein': 6.0,
                'fat': 28.0,
                'carbohydrate': 62.0,
                'sugar': 3.0,
                'dietary_fiber': 1.0,
                'salt': 800,
                'company_name': '농심',
                'weight': 90,
            },
            {
                'food_name': '오리온 초코파이',
                'food_category': '과자류',
                'representative_food': '과자',
                'calorie': 280,
                'protein': 4.0,
                'fat': 10.0,
                'carbohydrate': 45.0,
                'sugar': 25.0,
                'dietary_fiber': 1.5,
                'salt': 200,
                'company_name': '오리온',
                'weight': 50,
            },
            {
                'food_name': '롯데 칠성사이다',
                'food_category': '음료류',
                'representative_food': '탄산음료',
                'calorie': 120,
                'protein': 0.0,
                'fat': 0.0,
                'carbohydrate': 30.0,
                'sugar': 30.0,
                'dietary_fiber': 0.0,
                'salt': 50,
                'company_name': '롯데칠성',
                'weight': 500,
            },
            {
                'food_name': '동원 참치캔',
                'food_category': '수산물가공품',
                'representative_food': '참치',
                'calorie': 180,
                'protein': 25.0,
                'fat': 8.0,
                'carbohydrate': 0.0,
                'sugar': 0.0,
                'dietary_fiber': 0.0,
                'salt': 400,
                'company_name': '동원',
                'weight': 150,
            }
        ]

        with transaction.atomic():
            for i, food_data in enumerate(sample_foods[:limit]):
                # Food ID 생성 (F20240001 형태)
                food_id = f"F2024{str(i+1).zfill(4)}"
                
                # 영양 점수 계산 (간단한 예시)
                nutrition_score = self.calculate_nutrition_score(food_data)
                nutri_score_grade = self.calculate_nutri_score_grade(nutrition_score)
                nrf_index = self.calculate_nrf_index(food_data)
                
                food, created = Food.objects.get_or_create(
                    food_id=food_id,
                    defaults={
                        'food_name': food_data['food_name'],
                        'food_category': food_data['food_category'],
                        'representative_food': food_data['representative_food'],
                        'nutritional_value_standard_amount': 100,
                        'calorie': food_data['calorie'],
                        'moisture': 0.0,  # 기본값
                        'protein': food_data['protein'],
                        'fat': food_data['fat'],
                        'carbohydrate': food_data['carbohydrate'],
                        'sugar': food_data['sugar'],
                        'dietary_fiber': food_data['dietary_fiber'],
                        'salt': food_data['salt'],
                        'weight': food_data['weight'],
                        'company_name': food_data['company_name'],
                        'nutrition_score': nutrition_score,
                        'nutri_score_grade': nutri_score_grade,
                        'nrf_index': nrf_index,
                    }
                )
                
                if created:
                    self.stdout.write(f'생성됨: {food.food_name}')
                    
                    # 샘플 가격 정보 생성
                    self.create_sample_prices(food)
                else:
                    self.stdout.write(f'이미 존재함: {food.food_name}')

    def create_sample_prices(self, food):
        """샘플 가격 정보 생성"""
        shops = ['쿠팡', '11번가', 'G마켓', '옥션']
        base_prices = {
            '삼성 라면': 1200,
            '농심 새우깡': 1500,
            '오리온 초코파이': 800,
            '롯데 칠성사이다': 1000,
            '동원 참치캔': 2500,
        }
        
        base_price = base_prices.get(food.food_name, 1000)
        
        for i, shop in enumerate(shops):
            price_id = f"P{food.food_id[1:]}{str(i+1).zfill(2)}"
            price = base_price + (i * 100)  # 가격 변동
            
            Price.objects.get_or_create(
                price_id=price_id,
                defaults={
                    'food': food,
                    'shop_name': shop,
                    'price': price,
                    'discount_price': price - 100 if i > 0 else None,
                    'is_available': True,
                }
            )

    def calculate_nutrition_score(self, food_data):
        """간단한 영양 점수 계산 (0-10)"""
        score = 0
        
        # 단백질 점수 (높을수록 좋음)
        if food_data['protein'] > 20:
            score += 3
        elif food_data['protein'] > 10:
            score += 2
        elif food_data['protein'] > 5:
            score += 1
        
        # 식이섬유 점수 (높을수록 좋음)
        if food_data['dietary_fiber'] > 5:
            score += 2
        elif food_data['dietary_fiber'] > 2:
            score += 1
        
        # 나트륨 점수 (낮을수록 좋음)
        if food_data['salt'] < 300:
            score += 2
        elif food_data['salt'] < 600:
            score += 1
        
        # 당류 점수 (낮을수록 좋음)
        if food_data['sugar'] < 5:
            score += 2
        elif food_data['sugar'] < 10:
            score += 1
        
        # 칼로리 점수 (적당할수록 좋음)
        if 200 <= food_data['calorie'] <= 400:
            score += 1
        
        return min(score, 10)  # 최대 10점

    def calculate_nutri_score_grade(self, nutrition_score):
        """Nutri-Score 등급 계산"""
        if nutrition_score >= 8:
            return 'A'
        elif nutrition_score >= 6:
            return 'B'
        elif nutrition_score >= 4:
            return 'C'
        elif nutrition_score >= 2:
            return 'D'
        else:
            return 'E'

    def calculate_nrf_index(self, food_data):
        """NRF 지수 계산 (간단한 버전)"""
        # 좋은 영양소 점수
        good_score = 0
        if food_data['protein'] > 0:
            good_score += food_data['protein'] / 50  # 단백질 기준
        if food_data['dietary_fiber'] > 0:
            good_score += food_data['dietary_fiber'] / 25  # 식이섬유 기준
        
        # 나쁜 영양소 점수
        bad_score = 0
        if food_data['salt'] > 0:
            bad_score += food_data['salt'] / 2000  # 나트륨 기준
        if food_data['sugar'] > 0:
            bad_score += food_data['sugar'] / 50  # 당류 기준
        
        nrf_index = (good_score * 100 / 2) - (bad_score * 100 / 2)
        return round(nrf_index, 2)

    def crawl_real_data(self, limit):
        """실제 웹사이트에서 크롤링 (예시)"""
        self.stdout.write('실제 크롤링은 구현 예정입니다.')
        # 여기에 실제 크롤링 로직을 구현할 수 있습니다.
        # 예: 식품의약품안전처 API, 대형마트 사이트 등 