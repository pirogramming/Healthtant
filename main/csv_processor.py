"""
CSV/XLSX 파일 처리 관련 함수들
데이터베이스 업데이트를 위한 CSV 처리 로직을 모아놓은 모듈
"""

import pandas as pd
import uuid
from datetime import datetime
from django.db import transaction
from foods.models import Food, Price


def process_food_data(df, upload_mode):
    """
    Food 테이블 데이터 처리
    
    Args:
        df: pandas DataFrame
        upload_mode: 업로드 모드 ('insert', 'update', 'upsert')
    
    Returns:
        dict: 처리 결과 정보
    """
    processed_rows = 0
    inserted_rows = 0
    updated_rows = 0
    skipped_rows = 0
    error_rows = 0
    details = []
    
    # 필수 컬럼 확인
    required_columns = ['food_id', 'food_name', 'food_category', 'representative_food', 
                       'nutritional_value_standard_amount', 'calorie', 'moisture', 
                       'protein', 'fat', 'carbohydrate', 'weight', 'company_name']
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f'필수 컬럼이 누락되었습니다: {missing_columns}')
    
    for index, row in df.iterrows():
        try:
            # NaN 값 처리
            row = row.fillna('')
            
            # food_id 생성 (없는 경우)
            food_id = row.get('food_id', '')
            if not food_id:
                food_id = f"F{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:4].upper()}"
            
            # 기존 데이터 확인
            existing_food = Food.objects.filter(food_id=food_id).first()
            
            if upload_mode == 'insert':
                if existing_food:
                    skipped_rows += 1
                    details.append(f"행 {index + 1}: food_id {food_id} 이미 존재 (INSERT 모드)")
                    continue
                
                # 새 데이터 삽입
                food = create_food_object(row, food_id)
                food.save()
                inserted_rows += 1
                details.append(f"행 {index + 1}: food_id {food_id} 삽입 완료")
                
            elif upload_mode == 'update':
                if not existing_food:
                    skipped_rows += 1
                    details.append(f"행 {index + 1}: food_id {food_id} 존재하지 않음 (UPDATE 모드)")
                    continue
                
                # 기존 데이터 업데이트
                update_food_object(existing_food, row)
                existing_food.save()
                updated_rows += 1
                details.append(f"행 {index + 1}: food_id {food_id} 업데이트 완료")
                
            elif upload_mode == 'upsert':
                if existing_food:
                    # 기존 데이터 업데이트
                    update_food_object(existing_food, row)
                    existing_food.save()
                    updated_rows += 1
                    details.append(f"행 {index + 1}: food_id {food_id} 업데이트 완료")
                else:
                    # 새 데이터 삽입
                    food = create_food_object(row, food_id)
                    food.save()
                    inserted_rows += 1
                    details.append(f"행 {index + 1}: food_id {food_id} 삽입 완료")
            
            processed_rows += 1
            
        except Exception as e:
            error_rows += 1
            details.append(f"행 {index + 1}: 오류 발생 - {str(e)}")
            continue
    
    return {
        'processed_rows': processed_rows,
        'inserted_rows': inserted_rows,
        'updated_rows': updated_rows,
        'skipped_rows': skipped_rows,
        'error_rows': error_rows,
        'details': details
    }


def process_price_data(df, upload_mode):
    """
    Price 테이블 데이터 처리
    
    Args:
        df: pandas DataFrame
        upload_mode: 업로드 모드 ('insert', 'update', 'upsert')
    
    Returns:
        dict: 처리 결과 정보
    """
    processed_rows = 0
    inserted_rows = 0
    updated_rows = 0
    skipped_rows = 0
    error_rows = 0
    details = []
    
    # 필수 컬럼 확인
    required_columns = ['food_id', 'shop_name', 'price']
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f'필수 컬럼이 누락되었습니다: {missing_columns}')
    
    for index, row in df.iterrows():
        try:
            # NaN 값 처리
            row = row.fillna('')
            
            food_id = row.get('food_id', '')
            shop_name = row.get('shop_name', '')
            price = row.get('price', 0)
            
            # food_id 검증
            if not food_id:
                error_rows += 1
                details.append(f"행 {index + 1}: food_id가 비어있음")
                continue
            
            # Food 테이블에서 해당 food_id 확인
            food = Food.objects.filter(food_id=food_id).first()
            if not food:
                error_rows += 1
                details.append(f"행 {index + 1}: food_id {food_id}가 Food 테이블에 존재하지 않음")
                continue
            
            # price_id 생성
            price_id = row.get('price_id', '')
            if not price_id:
                price_id = f"P{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:4].upper()}"
            
            # 기존 가격 데이터 확인 (food_id + shop_name으로)
            existing_price = Price.objects.filter(food_id=food_id, shop_name=shop_name).first()
            
            if upload_mode == 'insert':
                if existing_price:
                    skipped_rows += 1
                    details.append(f"행 {index + 1}: food_id {food_id}, shop {shop_name} 이미 존재 (INSERT 모드)")
                    continue
                
                # 새 데이터 삽입
                price_obj = create_price_object(row, price_id, food)
                price_obj.save()
                inserted_rows += 1
                details.append(f"행 {index + 1}: price_id {price_id} 삽입 완료")
                
            elif upload_mode == 'update':
                if not existing_price:
                    skipped_rows += 1
                    details.append(f"행 {index + 1}: food_id {food_id}, shop {shop_name} 존재하지 않음 (UPDATE 모드)")
                    continue
                
                # 기존 데이터 업데이트
                update_price_object(existing_price, row)
                existing_price.save()
                updated_rows += 1
                details.append(f"행 {index + 1}: price_id {existing_price.price_id} 업데이트 완료")
                
            elif upload_mode == 'upsert':
                if existing_price:
                    # 기존 데이터 업데이트
                    update_price_object(existing_price, row)
                    existing_price.save()
                    updated_rows += 1
                    details.append(f"행 {index + 1}: price_id {existing_price.price_id} 업데이트 완료")
                else:
                    # 새 데이터 삽입
                    price_obj = create_price_object(row, price_id, food)
                    price_obj.save()
                    inserted_rows += 1
                    details.append(f"행 {index + 1}: price_id {price_id} 삽입 완료")
            
            processed_rows += 1
            
        except Exception as e:
            error_rows += 1
            details.append(f"행 {index + 1}: 오류 발생 - {str(e)}")
            continue
    
    return {
        'processed_rows': processed_rows,
        'inserted_rows': inserted_rows,
        'updated_rows': updated_rows,
        'skipped_rows': skipped_rows,
        'error_rows': error_rows,
        'details': details
    }


def create_food_object(row, food_id):
    """
    Food 객체 생성
    
    Args:
        row: pandas Series (행 데이터)
        food_id: 음식 ID
    
    Returns:
        Food: 생성된 Food 객체
    """
    return Food(
        food_id=food_id,
        food_img=row.get('food_img', ''),
        food_name=row.get('food_name', ''),
        food_category=row.get('food_category', ''),
        representative_food=row.get('representative_food', ''),
        nutritional_value_standard_amount=int(row.get('nutritional_value_standard_amount', 0)),
        calorie=int(row.get('calorie', 0)),
        moisture=float(row.get('moisture', 0)),
        protein=float(row.get('protein', 0)),
        fat=float(row.get('fat', 0)),
        carbohydrate=float(row.get('carbohydrate', 0)),
        sugar=float(row.get('sugar', 0)) if row.get('sugar') else None,
        dietary_fiber=float(row.get('dietary_fiber', 0)) if row.get('dietary_fiber') else None,
        calcium=float(row.get('calcium', 0)) if row.get('calcium') else None,
        iron_content=float(row.get('iron_content', 0)) if row.get('iron_content') else None,
        phosphorus=float(row.get('phosphorus', 0)) if row.get('phosphorus') else None,
        potassium=float(row.get('potassium', 0)) if row.get('potassium') else None,
        salt=int(row.get('salt', 0)) if row.get('salt') else None,
        VitaminA=float(row.get('VitaminA', 0)) if row.get('VitaminA') else None,
        VitaminB=float(row.get('VitaminB', 0)) if row.get('VitaminB') else None,
        VitaminC=float(row.get('VitaminC', 0)) if row.get('VitaminC') else None,
        VitaminD=float(row.get('VitaminD', 0)) if row.get('VitaminD') else None,
        VitaminE=float(row.get('VitaminE', 0)) if row.get('VitaminE') else None,
        cholesterol=float(row.get('cholesterol', 0)) if row.get('cholesterol') else None,
        saturated_fatty_acids=float(row.get('saturated_fatty_acids', 0)) if row.get('saturated_fatty_acids') else None,
        trans_fatty_acids=float(row.get('trans_fatty_acids', 0)) if row.get('trans_fatty_acids') else None,
        serving_size=float(row.get('serving_size', 0)) if row.get('serving_size') else None,
        weight=float(row.get('weight', 0)),
        company_name=row.get('company_name', ''),
        nutrition_score=float(row.get('nutrition_score', 0)) if row.get('nutrition_score') else None,
        nutri_score_grade=row.get('nutri_score_grade', ''),
        nrf_index=float(row.get('nrf_index', 0)) if row.get('nrf_index') else None
    )


def update_food_object(food, row):
    """
    Food 객체 업데이트
    
    Args:
        food: 기존 Food 객체
        row: pandas Series (행 데이터)
    """
    food.food_img = row.get('food_img', food.food_img)
    food.food_name = row.get('food_name', food.food_name)
    food.food_category = row.get('food_category', food.food_category)
    food.representative_food = row.get('representative_food', food.representative_food)
    food.nutritional_value_standard_amount = int(row.get('nutritional_value_standard_amount', food.nutritional_value_standard_amount))
    food.calorie = int(row.get('calorie', food.calorie))
    food.moisture = float(row.get('moisture', food.moisture))
    food.protein = float(row.get('protein', food.protein))
    food.fat = float(row.get('fat', food.fat))
    food.carbohydrate = float(row.get('carbohydrate', food.carbohydrate))
    
    # 선택적 필드들 업데이트
    if row.get('sugar'):
        food.sugar = float(row.get('sugar'))
    if row.get('dietary_fiber'):
        food.dietary_fiber = float(row.get('dietary_fiber'))
    if row.get('calcium'):
        food.calcium = float(row.get('calcium'))
    if row.get('iron_content'):
        food.iron_content = float(row.get('iron_content'))
    if row.get('phosphorus'):
        food.phosphorus = float(row.get('phosphorus'))
    if row.get('potassium'):
        food.potassium = float(row.get('potassium'))
    if row.get('salt'):
        food.salt = int(row.get('salt'))
    if row.get('VitaminA'):
        food.VitaminA = float(row.get('VitaminA'))
    if row.get('VitaminB'):
        food.VitaminB = float(row.get('VitaminB'))
    if row.get('VitaminC'):
        food.VitaminC = float(row.get('VitaminC'))
    if row.get('VitaminD'):
        food.VitaminD = float(row.get('VitaminD'))
    if row.get('VitaminE'):
        food.VitaminE = float(row.get('VitaminE'))
    if row.get('cholesterol'):
        food.cholesterol = float(row.get('cholesterol'))
    if row.get('saturated_fatty_acids'):
        food.saturated_fatty_acids = float(row.get('saturated_fatty_acids'))
    if row.get('trans_fatty_acids'):
        food.trans_fatty_acids = float(row.get('trans_fatty_acids'))
    if row.get('serving_size'):
        food.serving_size = float(row.get('serving_size'))
    if row.get('weight'):
        food.weight = float(row.get('weight'))
    if row.get('company_name'):
        food.company_name = row.get('company_name')
    if row.get('nutrition_score'):
        food.nutrition_score = float(row.get('nutrition_score'))
    if row.get('nutri_score_grade'):
        food.nutri_score_grade = row.get('nutri_score_grade')
    if row.get('nrf_index'):
        food.nrf_index = float(row.get('nrf_index'))


def create_price_object(row, price_id, food):
    """
    Price 객체 생성
    
    Args:
        row: pandas Series (행 데이터)
        price_id: 가격 ID
        food: Food 객체
    
    Returns:
        Price: 생성된 Price 객체
    """
    return Price(
        price_id=price_id,
        food=food,
        shop_name=row.get('shop_name', ''),
        price=int(row.get('price', 0)),
        discount_price=int(row.get('discount_price', 0)) if row.get('discount_price') else None,
        is_available=bool(row.get('is_available', True))
    )


def update_price_object(price, row):
    """
    Price 객체 업데이트
    
    Args:
        price: 기존 Price 객체
        row: pandas Series (행 데이터)
    """
    price.shop_name = row.get('shop_name', price.shop_name)
    price.price = int(row.get('price', price.price))
    if row.get('discount_price'):
        price.discount_price = int(row.get('discount_price'))
    if 'is_available' in row:
        price.is_available = bool(row.get('is_available'))


def read_csv_file(csv_file):
    """
    CSV 파일을 읽는 함수
    
    Args:
        csv_file: 업로드된 파일 객체
    
    Returns:
        pandas.DataFrame: 읽은 데이터
    
    Raises:
        ValueError: 파일 읽기 실패 시
    """
    # CSV 파일 읽기 - 인코딩 자동 감지
    encodings = ['utf-8', 'cp949', 'euc-kr', 'latin1']
    df = None
    
    for encoding in encodings:
        try:
            df = pd.read_csv(csv_file, encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
    
    if df is None:
        raise ValueError('CSV 파일 인코딩을 감지할 수 없습니다. (UTF-8, CP949, EUC-KR 지원)')
    
    return df


def read_excel_file(excel_file):
    """
    Excel 파일을 읽는 함수
    
    Args:
        excel_file: 업로드된 파일 객체
    
    Returns:
        pandas.DataFrame: 읽은 데이터
    
    Raises:
        ValueError: 파일 읽기 실패 시
    """
    try:
        df = pd.read_excel(excel_file, engine='openpyxl')
        return df
    except Exception as e:
        raise ValueError(f'Excel 파일 읽기 실패: {str(e)}')


def validate_file_upload(csv_file, table_type, upload_mode):
    """
    파일 업로드 유효성 검사
    
    Args:
        csv_file: 업로드된 파일 객체
        table_type: 테이블 타입
        upload_mode: 업로드 모드
    
    Raises:
        ValueError: 유효성 검사 실패 시
    """
    # 파일 확장자 검증
    if not (csv_file.name.endswith('.csv') or csv_file.name.endswith('.xlsx')):
        raise ValueError('CSV 또는 XLSX 파일만 업로드 가능합니다.')
    
    # 파일 크기 검증 (100MB 제한)
    if csv_file.size > 100 * 1024 * 1024:
        raise ValueError('파일 크기는 100MB를 초과할 수 없습니다.')
    
    # 테이블 타입 확인
    if table_type not in ['food', 'price']:
        raise ValueError('지원하지 않는 테이블 타입입니다. (food, price만 지원)')
    
    # 업로드 모드 확인
    if upload_mode not in ['insert', 'update', 'upsert']:
        raise ValueError('지원하지 않는 업로드 모드입니다. (insert, update, upsert만 지원)')


def get_csv_template_data(table_type):
    """
    CSV 템플릿 데이터 반환
    
    Args:
        table_type: 테이블 타입
    
    Returns:
        dict: 템플릿 데이터
    
    Raises:
        ValueError: 지원하지 않는 테이블 타입
    """
    if table_type == 'food':
        # Food 테이블 템플릿
        return {
            'columns': [
                'food_id', 'food_img', 'food_name', 'food_category', 'representative_food',
                'nutritional_value_standard_amount', 'calorie', 'moisture', 'protein', 'fat', 'carbohydrate',
                'sugar', 'dietary_fiber', 'calcium', 'iron_content', 'phosphorus', 'potassium', 'salt',
                'VitaminA', 'VitaminB', 'VitaminC', 'VitaminD', 'VitaminE',
                'cholesterol', 'saturated_fatty_acids', 'trans_fatty_acids',
                'serving_size', 'weight', 'company_name',
                'nutrition_score', 'nutri_score_grade', 'nrf_index'
            ],
            'sample_data': [
                'F20240001', 'food_image_url.jpg', '샘플 식품', '곡류', '대표곡류',
                '100', '350', '12.5', '8.2', '1.5', '72.3',
                '2.1', '3.5', '25.0', '1.2', '120.0', '180.0', '150',
                '0.0', '0.3', '0.0', '0.0', '0.5',
                '0.0', '0.3', '0.0',
                '100.0', '100.0', '샘플회사',
                '7.5', 'B', '85.2'
            ]
        }
    elif table_type == 'price':
        # Price 테이블 템플릿
        return {
            'columns': [
                'food_id', 'shop_name', 'price', 'discount_price', 'is_available'
            ],
            'sample_data': [
                'F20240001', '샘플마트', '5000', '4500', 'True'
            ]
        }
    else:
        raise ValueError('지원하지 않는 테이블 타입입니다.')
