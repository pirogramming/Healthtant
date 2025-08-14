"""
CSV/XLSX 파일 처리 관련 함수들
데이터베이스 업데이트를 위한 CSV 처리 로직을 모아놓은 모듈
"""

import pandas as pd
import uuid
from datetime import datetime
from django.db import transaction
from foods.models import Food, Price
import time


def process_food_data(df, upload_mode):
    """
    Food 테이블 데이터 처리 (성능 최적화 버전)
    
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
    
    # NaN 값 처리 (전체 DataFrame에 한 번에 적용)
    df = df.fillna('')
            
            # food_id 생성 (없는 경우)
    df['food_id'] = df['food_id'].apply(
        lambda x: x if x else f"F{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:4].upper()}"
    )
    
    # 모든 food_id를 한 번에 조회하여 기존 데이터 확인
    all_food_ids = df['food_id'].tolist()
    existing_foods = {f.food_id: f for f in Food.objects.filter(food_id__in=all_food_ids)}
    
    # 배치 처리를 위한 리스트
    foods_to_create = []
    foods_to_update = []
    
    total_rows = len(df)
    
    for index, row in df.iterrows():
        try:
            food_id = row['food_id']
            existing_food = existing_foods.get(food_id)
            
            if upload_mode == 'insert':
                if existing_food:
                    skipped_rows += 1
                    if index % 1000 == 0:  # 1000행마다 진행상황만 로그
                        details.append(f"INSERT 모드: {index}/{total_rows} 행 처리 중...")
                    continue
                
                # 새 데이터 객체 생성 (아직 저장하지 않음)
                food = create_food_object(row, food_id)
                foods_to_create.append(food)
                inserted_rows += 1
                
            elif upload_mode == 'update':
                if not existing_food:
                    skipped_rows += 1
                    if index % 1000 == 0:
                        details.append(f"UPDATE 모드: {index}/{total_rows} 행 처리 중...")
                    continue
                
                # 기존 데이터 업데이트 (아직 저장하지 않음)
                update_food_object(existing_food, row)
                foods_to_update.append(existing_food)
                updated_rows += 1
                
            elif upload_mode == 'upsert':
                if existing_food:
                    # 기존 데이터 업데이트
                    update_food_object(existing_food, row)
                    foods_to_update.append(existing_food)
                    updated_rows += 1
                else:
                    # 새 데이터 생성
                    food = create_food_object(row, food_id)
                    foods_to_create.append(food)
                    inserted_rows += 1
            
            processed_rows += 1
            
            # 진행상황 로그 (1000행마다)
            if index % 1000 == 0:
                details.append(f"처리 진행률: {index}/{total_rows} 행 완료")
            
        except Exception as e:
            error_rows += 1
            details.append(f"행 {index + 1}: 오류 발생 - {str(e)}")
            continue
    
    # 배치 처리로 데이터베이스에 저장
    try:
        # 새 데이터 배치 생성
        if foods_to_create:
            Food.objects.bulk_create(foods_to_create, batch_size=100)  # 1000 → 100으로 줄임
            details.append(f"배치 생성 완료: {len(foods_to_create)}개")
        
        # 기존 데이터 배치 업데이트
        if foods_to_update:
            Food.objects.bulk_update(
                foods_to_update, 
                fields=['food_img', 'food_name', 'food_category', 'representative_food',
                       'nutritional_value_standard_amount', 'calorie', 'moisture', 
                       'protein', 'fat', 'carbohydrate', 'sugar', 'dietary_fiber',
                       'calcium', 'iron_content', 'phosphorus', 'potassium', 'salt',
                       'VitaminA', 'VitaminB', 'VitaminC', 'VitaminD', 'VitaminE',
                       'cholesterol', 'saturated_fatty_acids', 'trans_fatty_acids',
                        'serving_size', 'weight', 'company_name',
                       'nutrition_score', 'nutri_score_grade', 'nrf_index'],
                batch_size=100  # 1000 → 100으로 줄임
            )
            details.append(f"배치 업데이트 완료: {len(foods_to_update)}개")
            
    except Exception as e:
        details.append(f"배치 처리 중 오류: {str(e)}")
        # 배치 처리 실패 시 개별 처리로 폴백
        for food in foods_to_create:
            try:
                food.save()
            except:
                pass
        for food in foods_to_update:
            try:
                food.save()
            except:
                pass
    
    details.append(f"전체 처리 완료: {processed_rows}행 중 {inserted_rows}개 생성, {updated_rows}개 수정")
    
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
    Price 테이블 데이터 처리 (성능 최적화 버전)
    
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
    
    # NaN 값 처리 (전체 DataFrame에 한 번에 적용)
    df = df.fillna('')
    
    # food_id 검증 및 Food 테이블에서 한 번에 조회
    all_food_ids = df['food_id'].dropna().unique().tolist()
    existing_foods = {f.food_id: f for f in Food.objects.filter(food_id__in=all_food_ids)}
    
    # price_id 생성 (없는 경우)
    df['price_id'] = df['price_id'].apply(
        lambda x: x if x else f"P{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:4].upper()}"
    )
    
    # 배치 처리를 위한 리스트
    prices_to_create = []
    prices_to_update = []
    
    total_rows = len(df)
    
    for index, row in df.iterrows():
        try:
            food_id = row['food_id']
            shop_name = row['shop_name']
            price = row['price']
            
            # food_id 검증
            if not food_id:
                error_rows += 1
                details.append(f"행 {index + 1}: food_id가 비어있음")
                continue
            
            # Food 테이블에서 해당 food_id 확인
            food = existing_foods.get(food_id)
            if not food:
                error_rows += 1
                details.append(f"행 {index + 1}: food_id {food_id}가 Food 테이블에 존재하지 않음")
                continue
            
            price_id = row['price_id']
            
            # 기존 가격 데이터 확인 (food_id + shop_name으로)
            existing_price = Price.objects.filter(food_id=food_id, shop_name=shop_name).first()
            
            if upload_mode == 'insert':
                if existing_price:
                    skipped_rows += 1
                    if index % 1000 == 0:  # 1000행마다 진행상황만 로그
                        details.append(f"INSERT 모드: {index}/{total_rows} 행 처리 중...")
                    continue
                
                # 새 데이터 객체 생성 (아직 저장하지 않음)
                price_obj = create_price_object(row, price_id, food)
                prices_to_create.append(price_obj)
                inserted_rows += 1
                
            elif upload_mode == 'update':
                if not existing_price:
                    skipped_rows += 1
                    if index % 1000 == 0:
                        details.append(f"UPDATE 모드: {index}/{total_rows} 행 처리 중...")
                    continue
                
                # 기존 데이터 업데이트 (아직 저장하지 않음)
                update_price_object(existing_price, row)
                prices_to_update.append(existing_price)
                updated_rows += 1
                
            elif upload_mode == 'upsert':
                if existing_price:
                    # 기존 데이터 업데이트
                    update_price_object(existing_price, row)
                    prices_to_update.append(existing_price)
                    updated_rows += 1
                else:
                    # 새 데이터 생성
                    price_obj = create_price_object(row, price_id, food)
                    prices_to_create.append(price_obj)
                    inserted_rows += 1
            
            processed_rows += 1
            
            # 진행상황 로그 (1000행마다)
            if index % 1000 == 0:
                details.append(f"처리 진행률: {index}/{total_rows} 행 완료")
            
        except Exception as e:
            error_rows += 1
            details.append(f"행 {index + 1}: 오류 발생 - {str(e)}")
            continue
    
    # 배치 처리로 데이터베이스에 저장
    try:
        # 새 데이터 배치 생성
        if prices_to_create:
            Price.objects.bulk_create(prices_to_create, batch_size=100)  # 1000 → 100으로 줄임
            details.append(f"배치 생성 완료: {len(prices_to_create)}개")
        
        # 기존 데이터 배치 업데이트
        if prices_to_update:
            Price.objects.bulk_update(
                prices_to_update, 
                fields=['shop_name', 'price', 'discount_price', 'is_available'],
                batch_size=100  # 1000 → 100으로 줄임
            )
            details.append(f"배치 업데이트 완료: {len(prices_to_update)}개")
            
    except Exception as e:
        details.append(f"배치 처리 중 오류: {str(e)}")
        # 배치 처리 실패 시 개별 처리로 폴백
        for price in prices_to_create:
            try:
                price.save()
            except:
                pass
        for price in prices_to_update:
            try:
                price.save()
            except:
                pass
    
    details.append(f"전체 처리 완료: {processed_rows}행 중 {inserted_rows}개 생성, {updated_rows}개 수정")
    
    return {
        'processed_rows': processed_rows,
        'inserted_rows': inserted_rows,
        'updated_rows': updated_rows,
        'skipped_rows': skipped_rows,
        'error_rows': error_rows,
        'details': details
    }


def process_food_data_with_progress(df, upload_mode, session, progress_key):
    """
    Food 테이블 데이터 처리 (진행상황 추적 포함)
    
    Args:
        df: pandas DataFrame
        upload_mode: 업로드 모드 ('insert', 'update', 'upsert')
        session: Django 세션 객체
        progress_key: 진행상황 키
    
    Returns:
        dict: 처리 결과 정보
    """
    processed_rows = 0
    inserted_rows = 0
    updated_rows = 0
    skipped_rows = 0
    error_rows = 0
    details = []
    
    # 진행상황 업데이트: 데이터 검증 단계
    session[progress_key].update({
        'current_step': '필수 컬럼 검증 중...',
        'progress_percentage': 5
    })
    session.save()  # 세션 저장 강제
    print(f"[{progress_key}] 5% - 필수 컬럼 검증 중...")
    
    # 필수 컬럼 확인
    required_columns = ['food_id', 'food_name', 'food_category', 'representative_food', 
                       'nutritional_value_standard_amount', 'calorie', 'moisture', 
                       'protein', 'fat', 'carbohydrate', 'weight', 'company_name']
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f'필수 컬럼이 누락되었습니다: {missing_columns}')
    
    # 진행상황 업데이트: 데이터 전처리 단계
    session[progress_key].update({
        'current_step': '데이터 전처리 중...',
        'progress_percentage': 10
    })
    session.save()  # 세션 저장 강제
    print(f"[{progress_key}] 10% - 데이터 전처리 중...")
    
    # NaN 값 처리 (전체 DataFrame에 한 번에 적용)
    df = df.fillna('')
    
    # food_id 생성 (없는 경우)
    df['food_id'] = df['food_id'].apply(
        lambda x: x if x else f"F{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:4].upper()}"
    )
    
    # 진행상황 업데이트: 기존 데이터 조회 단계
    session[progress_key].update({
        'current_step': '기존 데이터 조회 중...',
        'progress_percentage': 15
    })
    session.save()  # 세션 저장 강제
    
    # 모든 food_id를 배치로 나누어 조회하여 기존 데이터 확인
    all_food_ids = df['food_id'].tolist()
    total_ids = len(all_food_ids)
    batch_size = 1000  # 배치 크기
    
    print(f"[{progress_key}] 15% - 기존 데이터 배치 조회 시작 (총 {total_ids}개, 배치 크기: {batch_size})")
    
    existing_foods = {}
    total_batches = (total_ids + batch_size - 1) // batch_size
    
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, total_ids)
        batch_ids = all_food_ids[start_idx:end_idx]
        
        # 진행상황 업데이트
        batch_progress = 15 + int((batch_num / total_batches) * 5)  # 15% ~ 20%
        session[progress_key].update({
            'current_step': f'기존 데이터 조회 중... ({batch_num + 1}/{total_batches} 배치)',
            'progress_percentage': batch_progress
        })
        session.save()
        
        print(f"[{progress_key}] 배치 {batch_num + 1}/{total_batches} 조회 중... ({len(batch_ids)}개)")
        
        # 배치별로 기존 데이터 조회
        batch_existing = {f.food_id: f for f in Food.objects.filter(food_id__in=batch_ids)}
        existing_foods.update(batch_existing)
        
        # 진행상황 출력
        print(f"[{progress_key}] 배치 {batch_num + 1} 완료: {len(batch_existing)}개 발견 (누적: {len(existing_foods)}개)")
    
    print(f"[{progress_key}] 기존 데이터 조회 완료: 총 {len(existing_foods)}개 발견")
    
    # 배치 처리를 위한 리스트
    foods_to_create = []
    foods_to_update = []
    
    total_rows = len(df)
    
    # 진행상황 업데이트: 데이터 처리 단계 시작
    session[progress_key].update({
        'current_step': '데이터 처리 중...',
        'progress_percentage': 20
    })
    session.save()  # 세션 저장 강제
    print(f"[{progress_key}] 20% - 데이터 처리 시작 (총 {total_rows}행)")
    
    for index, row in df.iterrows():
        try:
            food_id = row['food_id']
            existing_food = existing_foods.get(food_id)
            
            # 디버깅: 처음 몇 행의 처리 과정 로그
            if index < 5:
                print(f"[{progress_key}] 디버그 - 행 {index}: food_id={food_id}, existing_food={existing_food is not None}, upload_mode={upload_mode}")
            
            if upload_mode == 'insert':
                if existing_food:
                    skipped_rows += 1
                    if index < 5:
                        print(f"[{progress_key}] 디버그 - 행 {index}: INSERT 모드에서 기존 데이터 존재로 건너뛰기")
                    continue
                
                # 새 데이터 객체 생성 (아직 저장하지 않음)
                food = create_food_object(row, food_id)
                foods_to_create.append(food)
                inserted_rows += 1
                if index < 5:
                    print(f"[{progress_key}] 디버그 - 행 {index}: INSERT 모드에서 새 데이터 생성")
                
            elif upload_mode == 'update':
                if not existing_food:
                    skipped_rows += 1
                    if index < 5:
                        print(f"[{progress_key}] 디버그 - 행 {index}: UPDATE 모드에서 기존 데이터 없음으로 건너뛰기")
                    continue
                
                # 기존 데이터 업데이트 (아직 저장하지 않음)
                update_food_object(existing_food, row)
                foods_to_update.append(existing_food)
                updated_rows += 1
                if index < 5:
                    print(f"[{progress_key}] 디버그 - 행 {index}: UPDATE 모드에서 기존 데이터 업데이트")
                
            elif upload_mode == 'upsert':
                if existing_food:
                    # 기존 데이터 업데이트
                    update_food_object(existing_food, row)
                    foods_to_update.append(existing_food)
                    updated_rows += 1
                    if index < 5:
                        print(f"[{progress_key}] 디버그 - 행 {index}: UPSERT 모드에서 기존 데이터 업데이트")
                else:
                    # 새 데이터 생성
                    food = create_food_object(row, food_id)
                    foods_to_create.append(food)
                    inserted_rows += 1
                    if index < 5:
                        print(f"[{progress_key}] 디버그 - 행 {index}: UPSERT 모드에서 새 데이터 생성")
            
            processed_rows += 1
            
            # 진행상황 실시간 업데이트 (100행마다)
            if index % 100 == 0:
                progress_percentage = min(20 + int((index / total_rows) * 60), 80)
                estimated_remaining = calculate_estimated_time(index, total_rows, session[progress_key]['start_time'])
                
                session[progress_key].update({
                    'processed_rows': index + 1,
                    'current_step': f'데이터 처리 중... ({index + 1}/{total_rows})',
                    'progress_percentage': progress_percentage,
                    'estimated_time': estimated_remaining,
                    'details': [f'처리 진행률: {index + 1}/{total_rows} 행 완료']
                })
            
        except Exception as e:
            error_rows += 1
            error_msg = f"행 {index + 1}: 오류 발생 - {str(e)}"
            details.append(error_msg)
            print(f"[{progress_key}] 오류 발생: {error_msg}")
            continue
    
    # 진행상황 업데이트: 데이터베이스 저장 단계
    session[progress_key].update({
        'current_step': '데이터베이스에 저장 중...',
        'progress_percentage': 85
    })
    session.save()  # 세션 저장 강제
    print(f"[{progress_key}] 85% - 데이터베이스에 저장 중...")
    
    # 배치 처리로 데이터베이스에 저장
    try:
        # 새 데이터 배치 생성
        if foods_to_create:
            Food.objects.bulk_create(foods_to_create, batch_size=100)
            details.append(f"배치 생성 완료: {len(foods_to_create)}개")
            print(f"[{progress_key}] 배치 생성 완료: {len(foods_to_create)}개")
        
        # 기존 데이터 배치 업데이트
        if foods_to_update:
            Food.objects.bulk_update(
                foods_to_update, 
                fields=['food_img', 'food_name', 'food_category', 'representative_food',
                       'nutritional_value_standard_amount', 'calorie', 'moisture', 
                       'protein', 'fat', 'carbohydrate', 'sugar', 'dietary_fiber',
                       'calcium', 'iron_content', 'phosphorus', 'potassium', 'salt',
                       'VitaminA', 'VitaminB', 'VitaminC', 'VitaminD', 'VitaminE',
                       'cholesterol', 'saturated_fatty_acids', 'trans_fatty_acids',
                        'serving_size', 'weight', 'company_name',
                       'nutrition_score', 'nutri_score_grade', 'nrf_index'],
                batch_size=100
            )
            details.append(f"배치 업데이트 완료: {len(foods_to_update)}개")
            print(f"[{progress_key}] 배치 업데이트 완료: {len(foods_to_update)}개")
            
    except Exception as e:
        details.append(f"배치 처리 중 오류: {str(e)}")
        # 배치 처리 실패 시 개별 처리로 폴백
        for food in foods_to_create:
            try:
                food.save()
            except:
                pass
        for food in foods_to_update:
            try:
                food.save()
            except:
                pass
    
    details.append(f"전체 처리 완료: {processed_rows}행 중 {inserted_rows}개 생성, {updated_rows}개 수정")
    
    # 진행상황 업데이트: 완료 단계
    session[progress_key].update({
        'current_step': '처리 완료!',
        'progress_percentage': 100,
        'processed_rows': processed_rows
    })
    session.save()  # 세션 저장 강제
    print(f"[{progress_key}] 100% - 처리 완료! 총 {processed_rows}행 중 {inserted_rows}개 생성, {updated_rows}개 수정")
    
    return {
        'processed_rows': processed_rows,
        'inserted_rows': inserted_rows,
        'updated_rows': updated_rows,
        'skipped_rows': skipped_rows,
        'error_rows': error_rows,
        'details': details
    }


def process_price_data_with_progress(df, upload_mode, session, progress_key):
    """
    Price 테이블 데이터 처리 (진행상황 추적 포함)
    
    Args:
        df: pandas DataFrame
        upload_mode: 업로드 모드 ('insert', 'update', 'upsert')
        session: Django 세션 객체
        progress_key: 진행상황 키
    
    Returns:
        dict: 처리 결과 정보
    """
    processed_rows = 0
    inserted_rows = 0
    updated_rows = 0
    skipped_rows = 0
    error_rows = 0
    details = []
    
    # 진행상황 업데이트: 데이터 검증 단계
    session[progress_key].update({
        'current_step': '필수 컬럼 검증 중...',
        'progress_percentage': 5
    })
    session.save()  # 세션 저장 강제
    print(f"[{progress_key}] 5% - 필수 컬럼 검증 중...")
    
    # 필수 컬럼 확인
    required_columns = ['food_id', 'shop_name', 'price']
    
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f'필수 컬럼이 누락되었습니다: {missing_columns}')
    
    # 진행상황 업데이트: 데이터 전처리 단계
    session[progress_key].update({
        'current_step': '데이터 전처리 중...',
        'progress_percentage': 10
    })
    session.save()  # 세션 저장 강제
    print(f"[{progress_key}] 10% - 데이터 전처리 중...")
    
    # NaN 값 처리 (전체 DataFrame에 한 번에 적용)
    df = df.fillna('')
    
    # 진행상황 업데이트: Food 테이블 조회 단계
    session[progress_key].update({
        'current_step': 'Food 테이블 조회 중...',
        'progress_percentage': 15
    })
    session.save()  # 세션 저장 강제
    
    # food_id 검증 및 Food 테이블에서 배치로 조회
    all_food_ids = df['food_id'].dropna().unique().tolist()
    total_ids = len(all_food_ids)
    batch_size = 1000  # 배치 크기
    
    print(f"[{progress_key}] 15% - Food 테이블 배치 조회 시작 (총 {total_ids}개, 배치 크기: {batch_size})")
    
    existing_foods = {}
    total_batches = (total_ids + batch_size - 1) // batch_size
    
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, total_ids)
        batch_ids = all_food_ids[start_idx:end_idx]
        
        # 진행상황 업데이트
        batch_progress = 15 + int((batch_num / total_batches) * 5)  # 15% ~ 20%
        session[progress_key].update({
            'current_step': f'Food 테이블 조회 중... ({batch_num + 1}/{total_batches} 배치)',
            'progress_percentage': batch_progress
        })
        session.save()
        
        print(f"[{progress_key}] Food 배치 {batch_num + 1}/{total_batches} 조회 중... ({len(batch_ids)}개)")
        
        # 배치별로 기존 데이터 조회
        batch_existing = {f.food_id: f for f in Food.objects.filter(food_id__in=batch_ids)}
        existing_foods.update(batch_existing)
        
        # 진행상황 출력
        print(f"[{progress_key}] Food 배치 {batch_num + 1} 완료: {len(batch_existing)}개 발견 (누적: {len(existing_foods)}개)")
    
    print(f"[{progress_key}] Food 테이블 조회 완료: 총 {len(existing_foods)}개 발견")
    
    # price_id 생성 (없는 경우)
    df['price_id'] = df['price_id'].apply(
        lambda x: x if x else f"P{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:4].upper()}"
    )
    
    # 배치 처리를 위한 리스트
    prices_to_create = []
    prices_to_update = []
    
    total_rows = len(df)
    
    # 진행상황 업데이트: 데이터 처리 단계 시작
    session[progress_key].update({
        'current_step': '데이터 처리 중...',
        'progress_percentage': 20
    })
    session.save()  # 세션 저장 강제
    print(f"[{progress_key}] 20% - 데이터 처리 시작 (총 {total_rows}행)")
    
    for index, row in df.iterrows():
        try:
            food_id = row['food_id']
            shop_name = row['shop_name']
            price = row['price']
            
            # food_id 검증
            if not food_id:
                error_rows += 1
                details.append(f"행 {index + 1}: food_id가 비어있음")
                continue
            
            # Food 테이블에서 해당 food_id 확인
            food = existing_foods.get(food_id)
            if not food:
                error_rows += 1
                details.append(f"행 {index + 1}: food_id {food_id}가 Food 테이블에 존재하지 않음")
                continue
            
            price_id = row['price_id']
            
            # 기존 가격 데이터 확인 (food_id + shop_name으로)
            existing_price = Price.objects.filter(food_id=food_id, shop_name=shop_name).first()
            
            if upload_mode == 'insert':
                if existing_price:
                    skipped_rows += 1
                    continue
                
                # 새 데이터 객체 생성 (아직 저장하지 않음)
                price_obj = create_price_object(row, price_id, food)
                prices_to_create.append(price_obj)
                inserted_rows += 1
                
            elif upload_mode == 'update':
                if not existing_price:
                    skipped_rows += 1
                    continue
                
                # 기존 데이터 업데이트 (아직 저장하지 않음)
                update_price_object(existing_price, row)
                prices_to_update.append(existing_price)
                updated_rows += 1
                
            elif upload_mode == 'upsert':
                if existing_price:
                    # 기존 데이터 업데이트
                    update_price_object(existing_price, row)
                    prices_to_update.append(existing_price)
                    updated_rows += 1
                else:
                    # 새 데이터 생성
                    price_obj = create_price_object(row, price_id, food)
                    prices_to_create.append(price_obj)
                    inserted_rows += 1
            
            processed_rows += 1
            
            # 진행상황 실시간 업데이트 (50행마다)
            if index % 50 == 0:
                progress_percentage = min(20 + int((index / total_rows) * 60), 80)
                estimated_remaining = calculate_estimated_time(index, total_rows, session[progress_key]['start_time'])
                
                session[progress_key].update({
                    'processed_rows': index + 1,
                    'current_step': f'데이터 처리 중... ({index + 1}/{total_rows})',
                    'progress_percentage': progress_percentage,
                    'estimated_time': estimated_remaining,
                    'details': [f'처리 진행률: {index + 1}/{total_rows} 행 완료']
                })
                session.save()  # 세션 저장 강제
                print(f"[{progress_key}] {progress_percentage}% - {index + 1}/{total_rows} 행 처리 완료 (예상 남은 시간: {estimated_remaining})")
            
        except Exception as e:
            error_rows += 1
            details.append(f"행 {index + 1}: 오류 발생 - {str(e)}")
            continue
    
    # 진행상황 업데이트: 데이터베이스 저장 단계
    session[progress_key].update({
        'current_step': '데이터베이스에 저장 중...',
        'progress_percentage': 85
    })
    session.save()  # 세션 저장 강제
    
    # 배치 처리로 데이터베이스에 저장
    try:
        # 새 데이터 배치 생성
        if prices_to_create:
            Price.objects.bulk_create(prices_to_create, batch_size=100)  # 1000 → 100으로 줄임
            details.append(f"배치 생성 완료: {len(prices_to_create)}개")
        
        # 기존 데이터 배치 업데이트
        if prices_to_update:
            Price.objects.bulk_update(
                prices_to_update, 
                fields=['shop_name', 'price', 'discount_price', 'is_available'],
                batch_size=100  # 1000 → 100으로 줄임
            )
            details.append(f"배치 생성 완료: {len(prices_to_update)}개")
            
    except Exception as e:
        details.append(f"배치 처리 중 오류: {str(e)}")
        # 배치 처리 실패 시 개별 처리로 폴백
        for price in prices_to_create:
            try:
                price.save()
            except:
                pass
        for price in prices_to_update:
            try:
                price.save()
            except:
                pass
    
    details.append(f"전체 처리 완료: {processed_rows}행 중 {inserted_rows}개 생성, {updated_rows}개 수정")
    
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
    Food 객체 생성 (안전한 데이터 타입 변환 포함)
    
    Args:
        row: pandas Series (행 데이터)
        food_id: 음식 ID
    
    Returns:
        Food: 생성된 Food 객체
    """
    
    def safe_int(value, default=0):
        """안전한 정수 변환"""
        if pd.isna(value) or value == '' or value is None:
            return default
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return default
    
    def safe_float(value, default=0.0):
        """안전한 실수 변환"""
        if pd.isna(value) or value == '' or value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def safe_str(value, default=''):
        """안전한 문자열 변환"""
        if pd.isna(value) or value is None:
            return default
        return str(value).strip()
    
    return Food(
        food_id=food_id,
        food_img=safe_str(row.get('food_img')),
        food_name=safe_str(row.get('food_name')),
        food_category=safe_str(row.get('food_category')),
        representative_food=safe_str(row.get('representative_food')),
        nutritional_value_standard_amount=safe_int(row.get('nutritional_value_standard_amount')),
        calorie=safe_int(row.get('calorie')),
        moisture=safe_float(row.get('moisture')),
        protein=safe_float(row.get('protein')),
        fat=safe_float(row.get('fat')),
        carbohydrate=safe_float(row.get('carbohydrate')),
        sugar=safe_float(row.get('sugar')) if row.get('sugar') and not pd.isna(row.get('sugar')) else None,
        dietary_fiber=safe_float(row.get('dietary_fiber')) if row.get('dietary_fiber') and not pd.isna(row.get('dietary_fiber')) else None,
        calcium=safe_float(row.get('calcium')) if row.get('calcium') and not pd.isna(row.get('calcium')) else None,
        iron_content=safe_float(row.get('iron_content')) if row.get('iron_content') and not pd.isna(row.get('iron_content')) else None,
        phosphorus=safe_float(row.get('phosphorus')) if row.get('phosphorus') and not pd.isna(row.get('phosphorus')) else None,
        potassium=safe_float(row.get('potassium')) if row.get('potassium') and not pd.isna(row.get('potassium')) else None,
        salt=safe_int(row.get('salt')) if row.get('salt') and not pd.isna(row.get('salt')) else None,
        VitaminA=safe_float(row.get('VitaminA')) if row.get('VitaminA') and not pd.isna(row.get('VitaminA')) else None,
        VitaminB=safe_float(row.get('VitaminB')) if row.get('VitaminB') and not pd.isna(row.get('VitaminB')) else None,
        VitaminC=safe_float(row.get('VitaminC')) if row.get('VitaminC') and not pd.isna(row.get('VitaminC')) else None,
        VitaminD=safe_float(row.get('VitaminD')) if row.get('VitaminD') and not pd.isna(row.get('VitaminD')) else None,
        VitaminE=safe_float(row.get('VitaminE')) if row.get('VitaminE') and not pd.isna(row.get('VitaminE')) else None,
        cholesterol=safe_float(row.get('cholesterol')) if row.get('cholesterol') and not pd.isna(row.get('cholesterol')) else None,
        saturated_fatty_acids=safe_float(row.get('saturated_fatty_acids')) if row.get('saturated_fatty_acids') and not pd.isna(row.get('saturated_fatty_acids')) else None,
        trans_fatty_acids=safe_float(row.get('trans_fatty_acids')) if row.get('trans_fatty_acids') and not pd.isna(row.get('trans_fatty_acids')) else None,
        serving_size=safe_float(row.get('serving_size')) if row.get('serving_size') and not pd.isna(row.get('serving_size')) else None,
        weight=safe_float(row.get('weight')),
        company_name=safe_str(row.get('company_name')),
        nutrition_score=safe_float(row.get('nutrition_score')) if row.get('nutrition_score') and not pd.isna(row.get('nutrition_score')) else None,
        nutri_score_grade=safe_str(row.get('nutri_score_grade')),
        nrf_index=safe_float(row.get('nrf_index')) if row.get('nrf_index') and not pd.isna(row.get('nrf_index')) else None
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


def calculate_estimated_time(processed_rows, total_rows, start_time):
    """
    남은 시간을 계산하는 함수
    
    Args:
        processed_rows: 처리된 행 수
        total_rows: 전체 행 수
        start_time: 시작 시간
    
    Returns:
        str: 예상 남은 시간
    """
    if processed_rows == 0:
        return "계산 중..."
    
    elapsed_time = time.time() - start_time
    if elapsed_time == 0:
        return "계산 중..."
    
    # 평균 처리 시간 계산
    avg_time_per_row = elapsed_time / processed_rows
    
    # 남은 행 수
    remaining_rows = total_rows - processed_rows
    
    # 예상 남은 시간
    estimated_remaining = avg_time_per_row * remaining_rows
    
    if estimated_remaining < 60:
        return f"{int(estimated_remaining)}초"
    elif estimated_remaining < 3600:
        return f"{int(estimated_remaining / 60)}분 {int(estimated_remaining % 60)}초"
    else:
        hours = int(estimated_remaining / 3600)
        minutes = int((estimated_remaining % 3600) / 60)
        return f"{hours}시간 {minutes}분"