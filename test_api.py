#!/usr/bin/env python
"""
API 테스트 스크립트
Django 서버가 실행된 상태에서 이 스크립트를 실행하세요.
"""

import requests
import json

BASE_URL = 'http://localhost:8000/foods'

def test_db_endpoint():
    """새로운 /db/ 엔드포인트 테스트 (POST 방식)"""
    print("=== /db/ 엔드포인트 테스트 (POST) ===")
    
    # 1. 기본 검색
    print("1. 기본 검색 (라면)")
    data = {
        'q': '라면',
        'limit': 5
    }
    response = requests.post(f'{BASE_URL}/db/', json=data)
    if response.status_code == 200:
        result = response.json()
        print(f"검색어: {result['query']}")
        print(f"결과 수: {result['count']}")
        for food in result['results']:
            print(f"- {food['food_name']} (영양점수: {food['nutrition_score']})")
    else:
        print(f"에러: {response.status_code}")
    
    # 2. 영양소 필터링
    print("\n2. 영양소 필터링 (단백질 10g 이상, 칼로리 400kcal 이하)")
    data = {
        'min_protein': 10,
        'max_calorie': 400,
        'sort_by': 'protein',
        'limit': 3
    }
    response = requests.post(f'{BASE_URL}/db/', json=data)
    if response.status_code == 200:
        result = response.json()
        print(f"결과 수: {result['count']}")
        for food in result['results']:
            print(f"- {food['food_name']} (단백질: {food['protein']}g, 칼로리: {food['calorie']}kcal)")
    else:
        print(f"에러: {response.status_code}")
    
    # 3. 카테고리 필터링
    print("\n3. 카테고리 필터링 (과자류)")
    data = {
        'category': '과자류',
        'sort_by': 'calorie',
        'limit': 3
    }
    response = requests.post(f'{BASE_URL}/db/', json=data)
    if response.status_code == 200:
        result = response.json()
        print(f"결과 수: {result['count']}")
        for food in result['results']:
            print(f"- {food['food_name']} (칼로리: {food['calorie']}kcal)")
    else:
        print(f"에러: {response.status_code}")
    
    # 4. 복합 검색
    print("\n4. 복합 검색 (나트륨 500mg 이하, 영양점수 순)")
    data = {
        'max_sodium': 500,
        'sort_by': 'nutrition_score',
        'limit': 5
    }
    response = requests.post(f'{BASE_URL}/db/', json=data)
    if response.status_code == 200:
        result = response.json()
        print(f"결과 수: {result['count']}")
        for food in result['results']:
            print(f"- {food['food_name']} (영양점수: {food['nutrition_score']}, 나트륨: {food.get('salt', 'N/A')}mg)")
    else:
        print(f"에러: {response.status_code}")

def test_food_list():
    """식품 목록 조회 테스트"""
    print("=== 식품 목록 조회 ===")
    response = requests.get(f'{BASE_URL}/api/foods/')
    if response.status_code == 200:
        data = response.json()
        print(f"총 {data['count']}개의 식품이 있습니다.")
        for food in data['results'][:3]:  # 처음 3개만 출력
            print(f"- {food['food_name']} (영양점수: {food['nutrition_score']})")
    else:
        print(f"에러: {response.status_code}")

def test_food_detail():
    """식품 상세 정보 조회 테스트"""
    print("\n=== 식품 상세 정보 조회 ===")
    food_id = 'F20240001'  # 첫 번째 식품
    response = requests.get(f'{BASE_URL}/api/foods/{food_id}/')
    if response.status_code == 200:
        food = response.json()
        print(f"제품명: {food['food_name']}")
        print(f"카테고리: {food['food_category']}")
        print(f"칼로리: {food['calorie']}kcal")
        print(f"단백질: {food['protein']}g")
        print(f"지방: {food['fat']}g")
        print(f"탄수화물: {food['carbohydrate']}g")
        print(f"영양점수: {food['nutrition_score']}")
        print(f"Nutri-Score: {food['nutri_score_grade']}")
        print(f"NRF 지수: {food['nrf_index']}")
    else:
        print(f"에러: {response.status_code}")

def test_food_search():
    """식품 검색 테스트"""
    print("\n=== 식품 검색 테스트 ===")
    
    # 키워드 검색
    print("1. 키워드 검색 (라면)")
    response = requests.get(f'{BASE_URL}/api/foods/search/', params={'query': '라면'})
    if response.status_code == 200:
        foods = response.json()
        for food in foods:
            print(f"- {food['food_name']} (영양점수: {food['nutrition_score']})")
    
    # 영양소 필터링
    print("\n2. 영양소 필터링 (단백질 10g 이상)")
    response = requests.get(f'{BASE_URL}/api/foods/search/', params={'min_protein': 10})
    if response.status_code == 200:
        foods = response.json()
        for food in foods:
            print(f"- {food['food_name']} (단백질: {food['protein']}g)")

def test_top_nutrition():
    """영양 점수 상위 제품 조회 테스트"""
    print("\n=== 영양 점수 상위 제품 ===")
    response = requests.get(f'{BASE_URL}/api/foods/top_nutrition/', params={'limit': 5})
    if response.status_code == 200:
        foods = response.json()
        for i, food in enumerate(foods, 1):
            print(f"{i}. {food['food_name']} (영양점수: {food['nutrition_score']})")

def test_categories():
    """카테고리 목록 조회 테스트"""
    print("\n=== 사용 가능한 카테고리 ===")
    response = requests.get(f'{BASE_URL}/api/foods/categories/')
    if response.status_code == 200:
        categories = response.json()
        for category in categories:
            print(f"- {category}")

def test_price_info():
    """가격 정보 조회 테스트"""
    print("\n=== 가격 정보 조회 ===")
    food_id = 'F20240001'
    response = requests.get(f'{BASE_URL}/api/prices/by_food/', params={'food_id': food_id})
    if response.status_code == 200:
        prices = response.json()
        for price in prices:
            print(f"- {price['shop_name']}: {price['price']}원")
            if price['discount_price']:
                print(f"  할인가: {price['discount_price']}원")

if __name__ == '__main__':
    print("헬스턴트 API 테스트를 시작합니다...\n")
    
    try:
        # 새로운 /db/ 엔드포인트 테스트
        test_db_endpoint()
        
        # 기존 API 테스트
        test_food_list()
        test_food_detail()
        test_food_search()
        test_top_nutrition()
        test_categories()
        test_price_info()
        
        print("\n=== API 테스트 완료 ===")
        
    except requests.exceptions.ConnectionError:
        print("Django 서버가 실행되지 않았습니다.")
        print("다음 명령어로 서버를 실행하세요:")
        print("python manage.py runserver")
    except Exception as e:
        print(f"테스트 중 오류가 발생했습니다: {e}") 