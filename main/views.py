from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import connection, transaction
from django.db.models import Q, Avg
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import json
import time
import pandas as pd
import os
import uuid
from datetime import datetime
from foods.models import Food, Price
from accounts.models import UserProfile
from diets.models import Diet

# Create your views here.
def main_page(request):
    """메인 페이지 뷰(바꾸셔도 돼요요)"""
    return render(request, 'main/main_mainpage.html')

def csv_upload_page(request):
    """CSV 업로드 페이지 뷰"""
    return render(request, 'main/csv_upload.html')

def parse_where_conditions(where_data, queryset, join_info=None):
    """
    WHERE 조건을 Django ORM 쿼리로 변환하는 함수 (3-5단계 개선)
    
    Args:
        where_data (dict): WHERE 조건 데이터
        queryset: Django QuerySet
        join_info (dict): JOIN 정보 (JOIN된 테이블의 필드 조건 지원)
    
    Returns:
        QuerySet: 필터링된 QuerySet
    """
    if not where_data:
        return queryset
    
    # WHERE 조건 구조 검증
    if 'conditions' not in where_data:
        return queryset
    
    conditions = where_data['conditions']
    if not conditions:
        return queryset
    
    # 조건 개수 제한 (보안상 복잡한 쿼리 방지)
    if len(conditions) > 10:
        return queryset
    
    # 논리 연산자 결정 (기본값: AND)
    logic = where_data.get('logic', 'AND').upper()
    if logic not in ['AND', 'OR']:
        logic = 'AND'
    
    # 지원하는 연산자 목록
    supported_operators = ['=', '!=', '>', '<', '>=', '<=', 'LIKE', 'IN', 'BETWEEN']
    
    # JOIN 정보가 있으면 사용 가능한 필드 확장
    available_fields = [field.name for field in queryset.model._meta.fields]
    if join_info and join_info.get('join_model'):
        join_model = join_info['join_model']
        join_table_name = join_info['join_table']
        join_fields = [field.name for field in join_model._meta.fields]
        # JOIN 테이블 필드는 "테이블명__필드명" 형태로 접근
        available_fields.extend([f"{join_table_name}__{field}" for field in join_fields])
    
    # 단일 조건 처리
    if len(conditions) == 1:
        condition = conditions[0]
        
        # 조건 구조 검증
        if not all(key in condition for key in ['field', 'operator', 'value']):
            return queryset
        
        field_name = condition['field']
        operator = condition['operator']
        value = condition['value']
        
        # 필드명 유효성 검사 강화 (JOIN된 테이블 필드 포함)
        if field_name not in available_fields:
            return queryset
        
        # 연산자 유효성 검사
        if operator not in supported_operators:
            return queryset
        
        # 값 타입 검증
        if not validate_condition_value(operator, value):
            return queryset
        
        # 연산자별 조건 처리
        try:
            if operator == '=':
                queryset = queryset.filter(**{field_name: value})
            elif operator == '!=':
                queryset = queryset.exclude(**{field_name: value})
            elif operator == '>':
                queryset = queryset.filter(**{f'{field_name}__gt': value})
            elif operator == '<':
                queryset = queryset.filter(**{f'{field_name}__lt': value})
            elif operator == '>=':
                queryset = queryset.filter(**{f'{field_name}__gte': value})
            elif operator == '<=':
                queryset = queryset.filter(**{f'{field_name}__lte': value})
            # 고급 연산자 추가 (2-4단계)
            elif operator == 'LIKE':
                queryset = queryset.filter(**{f'{field_name}__icontains': value})
            elif operator == 'IN':
                if isinstance(value, list):
                    queryset = queryset.filter(**{f'{field_name}__in': value})
                else:
                    # IN 연산자에 리스트가 아닌 값이 오면 무시
                    pass
            elif operator == 'BETWEEN':
                if isinstance(value, list) and len(value) == 2:
                    queryset = queryset.filter(**{
                        f'{field_name}__gte': value[0],
                        f'{field_name}__lte': value[1]
                    })
                else:
                    # BETWEEN 연산자에 2개 요소가 아닌 리스트가 오면 무시
                    pass
            else:
                # 지원하지 않는 연산자는 무시
                pass
                
        except Exception:
            # 조건 처리 중 오류가 발생하면 원본 QuerySet 반환
            return queryset
    
    # 복합 조건 처리 (2-3단계)
    elif len(conditions) > 1:
        try:
            # Q 객체 리스트 생성
            q_objects = []
            
            for condition in conditions:
                # 조건 구조 검증
                if not all(key in condition for key in ['field', 'operator', 'value']):
                    continue
                
                field_name = condition['field']
                operator = condition['operator']
                value = condition['value']
                
                # 필드명 유효성 검사 강화 (JOIN된 테이블 필드 포함)
                if field_name not in available_fields:
                    continue
                
                # 연산자 유효성 검사
                if operator not in supported_operators:
                    continue
                
                # 값 타입 검증
                if not validate_condition_value(operator, value):
                    continue
                
                # Q 객체 생성
                if operator == '=':
                    q_objects.append(Q(**{field_name: value}))
                elif operator == '!=':
                    q_objects.append(~Q(**{field_name: value}))
                elif operator == '>':
                    q_objects.append(Q(**{f'{field_name}__gt': value}))
                elif operator == '<':
                    q_objects.append(Q(**{f'{field_name}__lt': value}))
                elif operator == '>=':
                    q_objects.append(Q(**{f'{field_name}__gte': value}))
                elif operator == '<=':
                    q_objects.append(Q(**{f'{field_name}__lte': value}))
                # 고급 연산자 추가 (2-4단계)
                elif operator == 'LIKE':
                    q_objects.append(Q(**{f'{field_name}__icontains': value}))
                elif operator == 'IN':
                    if isinstance(value, list):
                        q_objects.append(Q(**{f'{field_name}__in': value}))
                    else:
                        # IN 연산자에 리스트가 아닌 값이 오면 무시
                        continue
                elif operator == 'BETWEEN':
                    if isinstance(value, list) and len(value) == 2:
                        q_objects.append(Q(**{
                            f'{field_name}__gte': value[0],
                            f'{field_name}__lte': value[1]
                        }))
                    else:
                        # BETWEEN 연산자에 2개 요소가 아닌 리스트가 오면 무시
                        continue
                else:
                    # 지원하지 않는 연산자는 무시
                    continue
            
            # Q 객체들을 논리 연산자로 결합
            if q_objects:
                if logic == 'AND':
                    # 모든 조건을 AND로 결합
                    combined_q = q_objects[0]
                    for q_obj in q_objects[1:]:
                        combined_q = combined_q & q_obj
                    queryset = queryset.filter(combined_q)
                elif logic == 'OR':
                    # 모든 조건을 OR로 결합
                    combined_q = q_objects[0]
                    for q_obj in q_objects[1:]:
                        combined_q = combined_q | q_obj
                    queryset = queryset.filter(combined_q)
                    
        except Exception:
            # 조건 처리 중 오류가 발생하면 원본 QuerySet 반환
            return queryset
    
    return queryset

def validate_condition_value(operator, value):
    """
    조건 값의 유효성을 검사하는 함수
    
    Args:
        operator (str): 연산자
        value: 검사할 값
    
    Returns:
        bool: 유효성 여부
    """
    try:
        if operator == 'IN':
            # IN 연산자는 리스트여야 함
            if not isinstance(value, list):
                return False
            # 리스트가 너무 크면 안됨 (보안상)
            if len(value) > 100:
                return False
            return True
        elif operator == 'BETWEEN':
            # BETWEEN 연산자는 2개 요소의 리스트여야 함
            if not isinstance(value, list) or len(value) != 2:
                return False
            # 두 값이 모두 숫자여야 함
            if not all(isinstance(v, (int, float)) for v in value):
                return False
            # 첫 번째 값이 두 번째 값보다 작아야 함
            if value[0] >= value[1]:
                return False
            return True
        elif operator == 'LIKE':
            # LIKE 연산자는 문자열이어야 함
            if not isinstance(value, str):
                return False
            # 문자열이 너무 길면 안됨 (보안상)
            if len(value) > 100:
                return False
            return True
        else:
            # 기본 연산자들은 None이 아니면 됨
            return value is not None
    except Exception:
        return False

def parse_join_conditions(join_data, model_class):
    """
    JOIN 조건을 Django ORM 쿼리로 변환하는 함수
    
    Args:
        join_data (dict): JOIN 조건 데이터
        model_class: 메인 Django 모델 클래스
    
    Returns:
        tuple: (QuerySet, join_info) - JOIN된 QuerySet과 JOIN 정보
    """
    if not join_data:
        return model_class.objects.all(), None
    
    # JOIN 조건 구조 검증
    if not all(key in join_data for key in ['table', 'type', 'on']):
        return model_class.objects.all(), None
    
    join_table = join_data['table']
    join_type = join_data['type'].upper()
    join_on = join_data['on']
    
    # JOIN 타입 유효성 검사
    if join_type not in ['INNER', 'LEFT', 'RIGHT']:
        return model_class.objects.all(), None
    
    # JOIN 조건 구조 검증
    if not all(key in join_on for key in ['left', 'right']):
        return model_class.objects.all(), None
    
    # 모델 매핑
    model_mapping = {
        'food': Food,
        'price': Price,
        'diet': Diet,
        'user': UserProfile
    }
    
    # 테이블 관계 매핑 및 검증 (3-2단계)
    table_relationships = {
        # food 테이블과의 관계
        'food': {
            'price': {
                'main_field': 'food_id',
                'join_field': 'food_id',
                'join_model': Price,
                'relationship': 'one_to_many'  # food 1개 -> price 여러개
            },
            'diet': {
                'main_field': 'food_id',
                'join_field': 'food_id',
                'join_model': Diet,
                'relationship': 'one_to_many'  # food 1개 -> diet 여러개
            }
        },
        # price 테이블과의 관계
        'price': {
            'food': {
                'main_field': 'food_id',
                'join_field': 'food_id',
                'join_model': Food,
                'relationship': 'many_to_one'  # price 여러개 -> food 1개
            }
        },
        # diet 테이블과의 관계
        'diet': {
            'food': {
                'main_field': 'food_id',
                'join_field': 'food_id',
                'join_model': Food,
                'relationship': 'many_to_one'  # diet 여러개 -> food 1개
            },
            'user': {
                'main_field': 'user_id',
                'join_field': 'user_id',
                'join_model': UserProfile,
                'relationship': 'many_to_one'  # diet 여러개 -> user 1개
            }
        },
        # user 테이블과의 관계
        'user': {
            'diet': {
                'main_field': 'user_id',
                'join_field': 'user_id',
                'join_model': Diet,
                'relationship': 'one_to_many'  # user 1개 -> diet 여러개
            }
        }
    }
    
    # 메인 테이블명 추출
    main_table = None
    for table_name, model in model_mapping.items():
        if model == model_class:
            main_table = table_name
            break
    
    if not main_table:
        return model_class.objects.all(), None
    
    # JOIN 가능한 테이블 조합 검증
    if main_table not in table_relationships:
        return model_class.objects.all(), None
    
    if join_table not in table_relationships[main_table]:
        return model_class.objects.all(), None
    
    # 관계 정보 가져오기
    relationship_info = table_relationships[main_table][join_table]
    expected_main_field = relationship_info['main_field']
    expected_join_field = relationship_info['join_field']
    
    # JOIN 조건 필드 유효성 검사 (개선: 더 유연한 검증)
    left_field = join_on['left']
    right_field = join_on['right']
    
    # 필드명이 예상과 일치하는지 검사 (완화된 검증)
    # 기존: 정확히 일치해야 함
    # 개선: 예상 필드와 일치하거나, 실제 모델에 존재하는 필드면 허용
    if left_field != expected_main_field:
        # 예상 필드와 다르면 실제 모델에 해당 필드가 있는지 확인
        main_model_fields = [field.name for field in model_class._meta.fields]
        if left_field not in main_model_fields:
            return model_class.objects.all(), None
    
    if right_field != expected_join_field:
        # 예상 필드와 다르면 실제 JOIN 모델에 해당 필드가 있는지 확인
        join_model_fields = [field.name for field in join_model_class._meta.fields]
        if right_field not in join_model_fields:
            return model_class.objects.all(), None
    
    # JOIN 모델 가져오기
    join_model_class = relationship_info['join_model']
    
    # JOIN 정보 생성 (개선: 실제 사용된 필드 정보 추가)
    join_info = {
        'join_table': join_table,
        'join_type': join_type,
        'join_model': join_model_class,
        'relationship': relationship_info['relationship'],
        'join_conditions': join_on,
        'is_reversed': False,  # RIGHT JOIN인지 여부
        'actual_fields': {
            'main_field': left_field,
            'join_field': right_field,
            'expected_main_field': expected_main_field,
            'expected_join_field': expected_join_field,
            'field_validation': {
                'main_field_valid': left_field == expected_main_field or left_field in [field.name for field in model_class._meta.fields],
                'join_field_valid': right_field == expected_join_field or right_field in [field.name for field in join_model_class._meta.fields]
            }
        }
    }
    
    # JOIN 타입별 처리 (개선: 더 정확한 ORM 쿼리)
    try:
        if join_type == 'INNER':
            # INNER JOIN: 두 테이블 모두에 매칭되는 레코드만
            if relationship_info['relationship'] == 'one_to_many':
                # 메인 테이블에서 JOIN 테이블로 (1:N)
                # INNER JOIN의 경우 매칭되는 레코드가 있는지 확인
                queryset = model_class.objects.filter(
                    **{f'{join_table}__isnull': False}
                ).prefetch_related(join_table)
            else:
                # 메인 테이블에서 JOIN 테이블로 (N:1)
                queryset = model_class.objects.select_related(join_table)
                
        elif join_type == 'LEFT':
            # LEFT JOIN: 메인 테이블의 모든 레코드 + 매칭되는 JOIN 테이블 레코드
            if relationship_info['relationship'] == 'one_to_many':
                # 메인 테이블에서 JOIN 테이블로 (1:N)
                # LEFT JOIN은 모든 메인 레코드를 포함하므로 필터 없이 prefetch
                queryset = model_class.objects.prefetch_related(join_table)
            else:
                # 메인 테이블에서 JOIN 테이블로 (N:1)
                queryset = model_class.objects.select_related(join_table)
                
        elif join_type == 'RIGHT':
            # RIGHT JOIN: Django ORM에서는 직접 지원하지 않으므로 LEFT JOIN으로 시뮬레이션
            # JOIN 테이블을 메인으로 하고 LEFT JOIN으로 처리
            join_info['is_reversed'] = True
            
            if relationship_info['relationship'] == 'one_to_many':
                # JOIN 테이블을 메인으로 하고 메인 테이블로 LEFT JOIN
                # RIGHT JOIN 시뮬레이션: JOIN 테이블에서 시작하여 메인 테이블로 LEFT JOIN
                queryset = join_model_class.objects.select_related(main_table)
            else:
                # JOIN 테이블을 메인으로 하고 메인 테이블로 LEFT JOIN
                queryset = join_model_class.objects.select_related(main_table)
        
        # JOIN 정보에 쿼리 타입 추가
        join_info['query_type'] = {
            'orm_method': 'select_related' if relationship_info['relationship'] == 'many_to_one' else 'prefetch_related',
            'is_reversed_query': join_type == 'RIGHT'
        }
        
        return queryset, join_info
        
    except Exception:
        # JOIN 처리 중 오류가 발생하면 원본 QuerySet 반환
        return model_class.objects.all(), None

def parse_order_by_conditions(order_by_data, queryset, join_info=None):
    """
    ORDER BY 조건을 Django ORM 쿼리로 변환하는 함수 (5-1단계)
    
    Args:
        order_by_data (list): ORDER BY 조건 데이터
        queryset: Django QuerySet
        join_info (dict): JOIN 정보 (JOIN된 테이블의 필드 정렬 지원)
    
    Returns:
        QuerySet: 정렬된 QuerySet
    """
    if not order_by_data:
        return queryset
    
    # ORDER BY 조건이 리스트가 아니면 변환
    if not isinstance(order_by_data, list):
        order_by_data = [order_by_data]
    
    # 정렬 조건 개수 제한 (보안상 복잡한 쿼리 방지)
    if len(order_by_data) > 5:
        return queryset
    
    # 사용 가능한 필드 목록 생성
    available_fields = [field.name for field in queryset.model._meta.fields]
    if join_info and join_info.get('join_model'):
        join_model = join_info['join_model']
        join_table_name = join_info['join_table']
        join_fields = [field.name for field in join_model._meta.fields]
        # JOIN 테이블 필드는 "테이블명__필드명" 형태로 접근
        available_fields.extend([f"{join_table_name}__{field}" for field in join_fields])
    
    # 정렬 필드 리스트 생성
    order_fields = []
    
    for order_item in order_by_data:
        try:
            # 문자열 형태: "field" 또는 "field ASC/DESC"
            if isinstance(order_item, str):
                parts = order_item.strip().split()
                field_name = parts[0]
                direction = parts[1].upper() if len(parts) > 1 else 'ASC'
            # 딕셔너리 형태: {"field": "field_name", "direction": "ASC/DESC"}
            elif isinstance(order_item, dict):
                field_name = order_item.get('field', '')
                direction = order_item.get('direction', 'ASC').upper()
            else:
                continue
            
            # 필드명 유효성 검사
            if field_name not in available_fields:
                continue
            
            # 정렬 방향 검증
            if direction not in ['ASC', 'DESC']:
                direction = 'ASC'
            
            # Django ORM 정렬 필드 생성
            if direction == 'DESC':
                order_fields.append(f'-{field_name}')
            else:
                order_fields.append(field_name)
                
        except Exception:
            # 개별 정렬 조건 처리 중 오류가 발생하면 해당 조건만 무시
            continue
    
    # 정렬 적용
    if order_fields:
        try:
            queryset = queryset.order_by(*order_fields)
        except Exception:
            # 정렬 적용 중 오류가 발생하면 원본 QuerySet 반환
            return queryset
    
    return queryset

def parse_offset_conditions(offset_data, limit, queryset):
    """
    OFFSET 조건을 Django ORM 쿼리로 변환하는 함수 (5-2단계)
    
    Args:
        offset_data (int): OFFSET 값 또는 페이지네이션 데이터
        limit (int): LIMIT 값
        queryset: Django QuerySet
    
    Returns:
        QuerySet: OFFSET이 적용된 QuerySet
    """
    if not offset_data:
        return queryset
    
    offset = 0
    
    # OFFSET 데이터 타입에 따른 처리
    if isinstance(offset_data, int):
        # 직접 OFFSET 값 제공
        offset = offset_data
    elif isinstance(offset_data, dict):
        # 페이지네이션 형태: {"page": 1, "page_size": 10}
        page = offset_data.get('page', 1)
        page_size = offset_data.get('page_size', limit)
        
        # 페이지와 페이지 크기 검증
        if not isinstance(page, int) or page < 1:
            page = 1
        if not isinstance(page_size, int) or page_size < 1:
            page_size = limit
        
        # OFFSET 계산: (페이지 - 1) * 페이지 크기
        offset = (page - 1) * page_size
    else:
        # 잘못된 타입이면 OFFSET 적용 안함
        return queryset
    
    # OFFSET 값 검증
    if offset < 0:
        offset = 0
    
    # OFFSET 적용
    try:
        queryset = queryset[offset:offset + limit]
    except Exception:
        # OFFSET 적용 중 오류가 발생하면 원본 QuerySet 반환
        return queryset
    
    return queryset

def calculate_pagination_metadata(queryset, offset_data, limit):
    """
    페이지네이션 메타데이터를 계산하는 함수 (5-3단계)
    
    Args:
        queryset: Django QuerySet (필터링된 상태)
        offset_data: OFFSET 데이터 (int 또는 dict)
        limit (int): LIMIT 값
    
    Returns:
        dict: 페이지네이션 메타데이터
    """
    try:
        # 전체 레코드 수 계산 (성능 최적화: count() 사용)
        total_records = queryset.count()
        
        # 기본값 설정
        current_page = 1
        page_size = limit
        
        # OFFSET 데이터에서 페이지 정보 추출
        if isinstance(offset_data, dict):
            current_page = offset_data.get('page', 1)
            page_size = offset_data.get('page_size', limit)
        elif isinstance(offset_data, int) and offset_data > 0:
            # 직접 OFFSET 값이 주어진 경우 페이지 계산
            current_page = (offset_data // limit) + 1
        
        # 값 검증
        if not isinstance(current_page, int) or current_page < 1:
            current_page = 1
        if not isinstance(page_size, int) or page_size < 1:
            page_size = limit
        
        # 총 페이지 수 계산 (올림 나눗셈)
        total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 0
        
        # 페이지네이션 메타데이터 생성
        pagination_meta = {
            'total_records': total_records,
            'total_pages': total_pages,
            'current_page': current_page,
            'page_size': page_size,
            'has_next': current_page < total_pages if total_pages > 0 else False,
            'has_previous': current_page > 1,
            'start_record': (current_page - 1) * page_size + 1 if total_records > 0 else 0,
            'end_record': min(current_page * page_size, total_records),
            'offset_applied': (current_page - 1) * page_size
        }
        
        return pagination_meta
        
    except Exception:
        # 오류 발생 시 기본 메타데이터 반환
        return {
            'total_records': 0,
            'total_pages': 0,
            'current_page': 1,
            'page_size': limit,
            'has_next': False,
            'has_previous': False,
            'start_record': 0,
            'end_record': 0,
            'offset_applied': 0
        }

def get_model_indexes(model_class):
    """
    Django 모델의 인덱스 정보를 수집하는 함수 (5-4단계)
    
    Args:
        model_class: Django 모델 클래스
    
    Returns:
        dict: 인덱스 정보
    """
    try:
        indexes = {
            'single_indexes': [],
            'composite_indexes': [],
            'unique_indexes': []
        }
        
        # 모델의 메타데이터에서 인덱스 정보 추출
        meta = model_class._meta
        
        # 단일 필드 인덱스 수집
        for field in meta.fields:
            if field.db_index:
                indexes['single_indexes'].append({
                    'field': field.name,
                    'type': 'single',
                    'unique': field.unique,
                    'null': field.null
                })
        
        # 복합 인덱스 수집 (Django 3.2+ Meta.indexes)
        if hasattr(meta, 'indexes'):
            for index in meta.indexes:
                index_info = {
                    'fields': index.fields,
                    'type': 'composite',
                    'name': getattr(index, 'name', None),
                    'unique': getattr(index, 'unique', False)
                }
                indexes['composite_indexes'].append(index_info)
        
        # 고유 인덱스 수집
        if hasattr(meta, 'unique_together'):
            for unique_group in meta.unique_together:
                indexes['unique_indexes'].append({
                    'fields': list(unique_group),
                    'type': 'unique_together'
                })
        
        return indexes
        
    except Exception:
        return {
            'single_indexes': [],
            'composite_indexes': [],
            'unique_indexes': []
        }

def analyze_sorting_optimization(order_fields, model_class, join_info=None):
    """
    정렬 최적화를 분석하고 힌트를 제공하는 함수 (5-4단계)
    
    Args:
        order_fields (list): 정렬 필드 리스트
        model_class: Django 모델 클래스
        join_info (dict): JOIN 정보
    
    Returns:
        dict: 정렬 최적화 분석 결과
    """
    try:
        # 인덱스 정보 수집
        indexes = get_model_indexes(model_class)
        
        # 정렬 필드 분석
        sort_analysis = {
            'order_fields': order_fields,
            'index_coverage': [],
            'optimization_suggestions': [],
            'performance_impact': 'medium',
            'recommended_indexes': []
        }
        
        # 각 정렬 필드에 대한 인덱스 커버리지 분석
        for i, field in enumerate(order_fields):
            field_name = field.lstrip('-')  # DESC 정렬의 '-' 제거
            direction = 'DESC' if field.startswith('-') else 'ASC'
            
            field_analysis = {
                'field': field_name,
                'direction': direction,
                'position': i + 1,
                'has_index': False,
                'index_type': None,
                'optimization_score': 0
            }
            
            # 단일 인덱스 확인
            for single_index in indexes['single_indexes']:
                if single_index['field'] == field_name:
                    field_analysis['has_index'] = True
                    field_analysis['index_type'] = 'single'
                    field_analysis['optimization_score'] = 8
                    break
            
            # 복합 인덱스 확인 (첫 번째 필드인 경우)
            if i == 0:  # 첫 번째 정렬 필드만 복합 인덱스의 첫 번째 필드로 사용 가능
                for composite_index in indexes['composite_indexes']:
                    if composite_index['fields'] and composite_index['fields'][0] == field_name:
                        field_analysis['has_index'] = True
                        field_analysis['index_type'] = 'composite_leading'
                        field_analysis['optimization_score'] = 9
                        break
            
            sort_analysis['index_coverage'].append(field_analysis)
        
        # 최적화 제안 생성
        unindexed_fields = [f for f in sort_analysis['index_coverage'] if not f['has_index']]
        if unindexed_fields:
            sort_analysis['optimization_suggestions'].append({
                'type': 'add_index',
                'priority': 'high' if len(order_fields) == 1 else 'medium',
                'message': f"정렬 필드 '{', '.join([f['field'] for f in unindexed_fields])}'에 인덱스 추가 권장"
            })
        
        # 복합 인덱스 제안
        if len(order_fields) > 1:
            sort_analysis['recommended_indexes'].append({
                'type': 'composite',
                'fields': [f.lstrip('-') for f in order_fields],
                'priority': 'high',
                'description': f"복합 인덱스 생성: {', '.join([f.lstrip('-') for f in order_fields])}"
            })
        
        # 성능 영향 평가
        indexed_count = sum(1 for f in sort_analysis['index_coverage'] if f['has_index'])
        total_count = len(sort_analysis['index_coverage'])
        
        if indexed_count == total_count:
            sort_analysis['performance_impact'] = 'low'
        elif indexed_count == 0:
            sort_analysis['performance_impact'] = 'high'
        else:
            sort_analysis['performance_impact'] = 'medium'
        
        return sort_analysis
        
    except Exception:
        return {
            'order_fields': order_fields,
            'index_coverage': [],
            'optimization_suggestions': [],
            'performance_impact': 'unknown',
            'recommended_indexes': []
        }

def optimize_sorting_query(queryset, order_fields, model_class, join_info=None):
    """
    정렬 쿼리를 최적화하는 함수 (5-4단계)
    
    Args:
        queryset: Django QuerySet
        order_fields (list): 정렬 필드 리스트
        model_class: Django 모델 클래스
        join_info (dict): JOIN 정보
    
    Returns:
        tuple: (최적화된 QuerySet, 최적화 정보)
    """
    try:
        # 정렬 최적화 분석
        sort_analysis = analyze_sorting_optimization(order_fields, model_class, join_info)
        
        # 기본 정렬 적용
        optimized_queryset = queryset.order_by(*order_fields)
        
        # 성능 최적화 힌트 적용
        optimization_info = {
            'analysis': sort_analysis,
            'optimizations_applied': [],
            'query_hints': []
        }
        
        # 인덱스 힌트 추가
        if sort_analysis['performance_impact'] == 'high':
            optimization_info['query_hints'].append({
                'type': 'warning',
                'message': '정렬 성능이 낮을 수 있습니다. 인덱스 추가를 고려하세요.'
            })
        
        # JOIN이 있는 경우 추가 최적화
        if join_info and join_info.get('join_model'):
            join_table = join_info['join_table']
            join_model = join_info['join_model']
            
            # JOIN된 테이블의 정렬 필드 분석
            join_order_fields = [f for f in order_fields if f.startswith(f'{join_table}__')]
            if join_order_fields:
                join_sort_analysis = analyze_sorting_optimization(
                    [f.replace(f'{join_table}__', '') for f in join_order_fields], 
                    join_model
                )
                optimization_info['join_optimization'] = join_sort_analysis
        
        # 메모리 최적화 힌트
        if len(order_fields) > 3:
            optimization_info['query_hints'].append({
                'type': 'info',
                'message': '다중 정렬 필드 사용 시 메모리 사용량이 증가할 수 있습니다.'
            })
        
        return optimized_queryset, optimization_info
        
    except Exception:
        # 오류 발생 시 기본 정렬만 적용
        return queryset.order_by(*order_fields), {
            'analysis': None,
            'optimizations_applied': [],
            'query_hints': [{
                'type': 'error',
                'message': '정렬 최적화 분석 중 오류가 발생했습니다.'
            }]
        }

def monitor_sorting_performance(queryset, order_fields, execution_time, model_class):
    """
    정렬 성능을 모니터링하고 분석하는 함수 (5-4단계)
    
    Args:
        queryset: Django QuerySet
        order_fields (list): 정렬 필드 리스트
        execution_time (float): 실행 시간
        model_class: Django 모델 클래스
    
    Returns:
        dict: 성능 모니터링 결과
    """
    try:
        # 기본 성능 메트릭
        performance_metrics = {
            'execution_time': execution_time,
            'order_fields_count': len(order_fields),
            'estimated_records': queryset.count() if hasattr(queryset, 'count') else 'unknown',
            'performance_rating': 'good',
            'recommendations': []
        }
        
        # 실행 시간 기반 성능 평가
        if execution_time < 0.1:
            performance_metrics['performance_rating'] = 'excellent'
        elif execution_time < 0.5:
            performance_metrics['performance_rating'] = 'good'
        elif execution_time < 2.0:
            performance_metrics['performance_rating'] = 'fair'
        else:
            performance_metrics['performance_rating'] = 'poor'
            performance_metrics['recommendations'].append({
                'type': 'performance',
                'priority': 'high',
                'message': f'정렬 실행 시간이 {execution_time:.3f}초로 느립니다. 인덱스 최적화를 고려하세요.'
            })
        
        # 정렬 필드 수 기반 권장사항
        if len(order_fields) > 3:
            performance_metrics['recommendations'].append({
                'type': 'complexity',
                'priority': 'medium',
                'message': f'{len(order_fields)}개의 정렬 필드를 사용하고 있습니다. 복합 인덱스 생성을 고려하세요.'
            })
        
        # 인덱스 분석
        indexes = get_model_indexes(model_class)
        indexed_fields = [idx['field'] for idx in indexes['single_indexes']]
        composite_fields = []
        for idx in indexes['composite_indexes']:
            if idx['fields']:
                composite_fields.extend(idx['fields'])
        
        # 정렬 필드별 인덱스 커버리지 분석
        field_coverage = []
        for field in order_fields:
            field_name = field.lstrip('-')
            has_single_index = field_name in indexed_fields
            has_composite_index = field_name in composite_fields
            
            field_coverage.append({
                'field': field_name,
                'direction': 'DESC' if field.startswith('-') else 'ASC',
                'has_single_index': has_single_index,
                'has_composite_index': has_composite_index,
                'index_coverage': 'full' if has_single_index or has_composite_index else 'none'
            })
        
        performance_metrics['field_coverage'] = field_coverage
        
        # 전체 인덱스 커버리지 계산
        covered_fields = sum(1 for f in field_coverage if f['index_coverage'] != 'none')
        total_fields = len(field_coverage)
        coverage_percentage = (covered_fields / total_fields * 100) if total_fields > 0 else 0
        
        performance_metrics['index_coverage_percentage'] = coverage_percentage
        
        if coverage_percentage < 50:
            performance_metrics['recommendations'].append({
                'type': 'index',
                'priority': 'high',
                'message': f'인덱스 커버리지가 {coverage_percentage:.1f}%로 낮습니다. 정렬 필드에 인덱스를 추가하세요.'
            })
        elif coverage_percentage < 100:
            performance_metrics['recommendations'].append({
                'type': 'index',
                'priority': 'medium',
                'message': f'인덱스 커버리지가 {coverage_percentage:.1f}%입니다. 추가 인덱스로 성능을 향상시킬 수 있습니다.'
            })
        
        return performance_metrics
        
    except Exception:
        return {
            'execution_time': execution_time,
            'order_fields_count': len(order_fields),
            'estimated_records': 'unknown',
            'performance_rating': 'unknown',
            'recommendations': [{
                'type': 'error',
                'priority': 'low',
                'message': '성능 모니터링 중 오류가 발생했습니다.'
            }],
            'field_coverage': [],
            'index_coverage_percentage': 0
        }

@csrf_exempt
@require_http_methods(["POST"])
def db_explorer(request):
    """
    DB 탐색 API - SQL 유사 문법으로 데이터베이스 탐색
    """
    try:
        # 1. JSON 요청 파싱
        data = json.loads(request.body)
        
        # 2. 필수 필드 검증
        if 'table' not in data:
            return JsonResponse({
                'success': False,
                'message': 'table 필드가 필요합니다.',
                'data': None
            }, status=400)
        
        # 3. 테이블명 유효성 검사
        allowed_tables = ['food', 'price', 'diet', 'user']
        table_name = data['table']
        
        if table_name not in allowed_tables:
            return JsonResponse({
                'success': False,
                'message': f'허용되지 않은 테이블입니다. 허용된 테이블: {allowed_tables}',
                'data': None
            }, status=400)
        
        # 4. 테이블명에 따른 모델 매핑
        model_mapping = {
            'food': Food,
            'price': Price,
            'diet': Diet,
            'user': UserProfile
        }
        
        model_class = model_mapping[table_name]
        
        # 5. SELECT 필드 결정 및 유효성 검사 (3-5단계 개선)
        select_fields = data.get('select', [])
        if not select_fields:
            # select 필드가 없으면 모든 필드 선택
            select_fields = [field.name for field in model_class._meta.fields]
        else:
            # select 필드가 있으면 유효성 검사
            available_fields = [field.name for field in model_class._meta.fields]
            
            # JOIN 조건이 있는지 미리 확인
            join_data = data.get('join', None)
            join_applied = join_data is not None and all(key in join_data for key in ['table', 'type', 'on'])
            
            # JOIN된 테이블의 필드도 사용 가능하도록 추가
            if join_applied:
                # JOIN 정보를 미리 생성하여 필드 검증에 사용
                temp_queryset, temp_join_info = parse_join_conditions(join_data, model_class)
                if temp_join_info and temp_join_info.get('join_model'):
                    join_model = temp_join_info['join_model']
                    join_table_name = temp_join_info['join_table']
                    join_fields = [field.name for field in join_model._meta.fields]
                    # JOIN 테이블 필드는 "테이블명__필드명" 형태로 접근
                    available_fields.extend([f"{join_table_name}__{field}" for field in join_fields])
            
            invalid_fields = [field for field in select_fields if field not in available_fields]
            
            if invalid_fields:
                return JsonResponse({
                    'success': False,
                    'message': f'존재하지 않는 필드입니다: {invalid_fields}. 사용 가능한 필드: {available_fields}',
                    'data': None
                }, status=400)
        
        # 6. WHERE 조건 처리
        where_data = data.get('where', None)
        where_applied = where_data is not None and 'conditions' in where_data and len(where_data['conditions']) > 0
        
        # 7. JOIN 조건 처리 (3-5단계 최적화)
        join_data = data.get('join', None)
        join_applied = join_data is not None and all(key in join_data for key in ['table', 'type', 'on'])
        
        # 8. ORDER BY 조건 처리 (5-1단계)
        order_by_data = data.get('order_by', None)
        order_by_applied = order_by_data is not None and (
            isinstance(order_by_data, list) and len(order_by_data) > 0 or
            isinstance(order_by_data, str) and order_by_data.strip()
        )
        
        # 9. LIMIT 값 검증
        limit = data.get('limit', 100)
        if not isinstance(limit, int) or limit < 1:
            return JsonResponse({
                'success': False,
                'message': 'limit은 1 이상의 정수여야 합니다.',
                'data': None
            }, status=400)
        
        if limit > 1000:  # 최대 1000개로 제한
            limit = 1000
        
        # 10. OFFSET 값 검증 및 적용 (5-2단계)
        offset_data = data.get('offset', 0)
        if not isinstance(offset_data, int) and not isinstance(offset_data, dict):
            offset_data = 0 # 기본값 설정
        
        # 11. 쿼리 실행 (3-5단계 최적화된 순서)
        start_time = time.time()
        
        try:
            # 1단계: JOIN 조건 적용 (기본 구조만)
            queryset, join_info = parse_join_conditions(join_data, model_class)
            
            # 2단계: WHERE 조건 적용 (JOIN된 테이블 필드 지원)
            queryset = parse_where_conditions(where_data, queryset, join_info)
            
            # 3단계: ORDER BY 조건 적용 및 최적화 (5-4단계)
            sort_optimization_info = None
            if order_by_applied:
                # 정렬 필드 추출
                order_fields = []
                if isinstance(order_by_data, list):
                    for order_item in order_by_data:
                        if isinstance(order_item, str):
                            parts = order_item.strip().split()
                            field_name = parts[0]
                            direction = parts[1].upper() if len(parts) > 1 else 'ASC'
                            if direction == 'DESC':
                                order_fields.append(f'-{field_name}')
                            else:
                                order_fields.append(field_name)
                        elif isinstance(order_item, dict):
                            field_name = order_item.get('field', '')
                            direction = order_item.get('direction', 'ASC').upper()
                            if direction == 'DESC':
                                order_fields.append(f'-{field_name}')
                            else:
                                order_fields.append(field_name)
                elif isinstance(order_by_data, str):
                    parts = order_by_data.strip().split()
                    field_name = parts[0]
                    direction = parts[1].upper() if len(parts) > 1 else 'ASC'
                    if direction == 'DESC':
                        order_fields.append(f'-{field_name}')
                    else:
                        order_fields.append(field_name)
                
                # 정렬 최적화 적용
                if order_fields:
                    queryset, sort_optimization_info = optimize_sorting_query(
                        queryset, order_fields, model_class, join_info
                    )
            else:
                # ORDER BY가 없는 경우 기본 정렬 적용
                queryset = parse_order_by_conditions(order_by_data, queryset, join_info)
            
            # 4단계: SELECT 필드 적용 (JOIN된 테이블 필드 포함)
            if join_info and join_info.get('join_model'):
                # JOIN된 테이블의 필드도 선택 가능하도록 처리
                join_table_name = join_info['join_table']
                join_model = join_info['join_model']
                join_fields = [field.name for field in join_model._meta.fields]
                
                # JOIN 테이블 필드가 선택된 경우 처리
                join_selected_fields = [field for field in select_fields if field.startswith(f"{join_table_name}__")]
                if join_selected_fields:
                    # JOIN 테이블 필드가 선택된 경우 select_related/prefetch_related 최적화
                    if join_info['relationship'] == 'many_to_one':
                        queryset = queryset.select_related(join_table_name)
                    else:
                        queryset = queryset.prefetch_related(join_table_name)
            
            # 5단계: 쿼리 최적화 (3-5단계)
            if join_info:
                # JOIN이 있는 경우 쿼리 최적화
                if join_info['relationship'] == 'many_to_one':
                    # N:1 관계인 경우 select_related로 최적화
                    queryset = queryset.select_related(join_info['join_table'])
                else:
                    # 1:N 관계인 경우 prefetch_related로 최적화
                    queryset = queryset.prefetch_related(join_info['join_table'])
            
            # 6단계: SELECT 필드 적용 (최적화된 순서)
            queryset = queryset.values(*select_fields)
            
            # 7단계: OFFSET 적용 (5-2단계)
            queryset = parse_offset_conditions(offset_data, limit, queryset)
            
            # 8단계: LIMIT 적용 (성능 최적화)
            # OFFSET이 적용된 후 LIMIT를 다시 적용해야 함
            queryset = queryset[:limit]
            
            # 9단계: 결과 변환 (지연 평가)
            results = list(queryset)
            
        except Exception as query_error:
            return JsonResponse({
                'success': False,
                'message': f'쿼리 실행 중 오류가 발생했습니다: {str(query_error)}',
                'data': None
            }, status=500)
        
        execution_time = time.time() - start_time
        
        # 정렬 성능 모니터링 (5-4단계)
        sorting_performance_metrics = None
        if order_by_applied and sort_optimization_info:
            # 정렬 필드 추출 (모니터링용)
            monitor_order_fields = []
            if isinstance(order_by_data, list):
                for order_item in order_by_data:
                    if isinstance(order_item, str):
                        parts = order_item.strip().split()
                        field_name = parts[0]
                        direction = parts[1].upper() if len(parts) > 1 else 'ASC'
                        if direction == 'DESC':
                            monitor_order_fields.append(f'-{field_name}')
                        else:
                            monitor_order_fields.append(field_name)
                    elif isinstance(order_item, dict):
                        field_name = order_item.get('field', '')
                        direction = order_item.get('direction', 'ASC').upper()
                        if direction == 'DESC':
                            monitor_order_fields.append(f'-{field_name}')
                        else:
                            monitor_order_fields.append(field_name)
            elif isinstance(order_by_data, str):
                parts = order_by_data.strip().split()
                field_name = parts[0]
                direction = parts[1].upper() if len(parts) > 1 else 'ASC'
                if direction == 'DESC':
                    monitor_order_fields.append(f'-{field_name}')
                else:
                    monitor_order_fields.append(field_name)
            
            if monitor_order_fields:
                sorting_performance_metrics = monitor_sorting_performance(
                    queryset, monitor_order_fields, execution_time, model_class
                )
        
        # 12. WHERE 조건 정보 수집
        where_info = None
        if where_applied:
            conditions_count = len(where_data['conditions'])
            logic = where_data.get('logic', 'AND')
            where_info = {
                'conditions_count': conditions_count,
                'logic': logic,
                'applied_conditions': []
            }
            
            # 적용된 조건들 수집
            for condition in where_data['conditions']:
                if all(key in condition for key in ['field', 'operator', 'value']):
                    where_info['applied_conditions'].append({
                        'field': condition['field'],
                        'operator': condition['operator'],
                        'value': condition['value']
                    })
        
        # 13. JOIN 조건 정보 수집 (개선: 상세 정보 추가)
        join_info_response = None
        if join_applied:
            join_info_response = {
                'join_table': join_data['table'],
                'join_type': join_data['type'],
                'join_conditions': join_data['on']
            }
            if join_info and join_info['is_reversed']:
                join_info_response['is_reversed'] = True
            
            # JOIN 개선 정보 추가
            if join_info:
                join_info_response['improvements'] = {
                    'actual_fields': join_info.get('actual_fields', {}),
                    'query_type': join_info.get('query_type', {}),
                    'field_validation': join_info.get('actual_fields', {}).get('field_validation', {}),
                    'flexible_join': True  # 유연한 JOIN 조건 지원
                }
        
        # 14. ORDER BY 조건 정보 수집 및 정렬 최적화 정보 (5-4단계)
        order_by_info = None
        if order_by_applied:
            order_by_info = {
                'order_by_conditions': order_by_data,
                'applied_conditions': []
            }
            if order_by_data:
                for order_item in order_by_data:
                    if isinstance(order_item, str):
                        order_by_info['applied_conditions'].append({
                            'field': order_item.strip().split()[0],
                            'direction': order_item.strip().split()[1].upper() if len(order_item.strip().split()) > 1 else 'ASC'
                        })
                    elif isinstance(order_item, dict):
                        order_by_info['applied_conditions'].append({
                            'field': order_item.get('field', ''),
                            'direction': order_item.get('direction', 'ASC').upper()
                        })
            
            # 정렬 최적화 정보 추가 (5-4단계)
            if sort_optimization_info:
                order_by_info['sort_optimization'] = {
                    'analysis': sort_optimization_info.get('analysis', {}),
                    'query_hints': sort_optimization_info.get('query_hints', []),
                    'join_optimization': sort_optimization_info.get('join_optimization', {}),
                    'performance_impact': sort_optimization_info.get('analysis', {}).get('performance_impact', 'unknown'),
                    'optimization_score': sum(
                        f.get('optimization_score', 0) 
                        for f in sort_optimization_info.get('analysis', {}).get('index_coverage', [])
                    ) / max(len(sort_optimization_info.get('analysis', {}).get('index_coverage', [])), 1)
                }
                
                # 성능 모니터링 정보 추가 (5-4단계)
                if sorting_performance_metrics:
                    order_by_info['sort_optimization']['performance_monitoring'] = {
                        'execution_time': sorting_performance_metrics.get('execution_time', 0),
                        'performance_rating': sorting_performance_metrics.get('performance_rating', 'unknown'),
                        'index_coverage_percentage': sorting_performance_metrics.get('index_coverage_percentage', 0),
                        'field_coverage': sorting_performance_metrics.get('field_coverage', []),
                        'recommendations': sorting_performance_metrics.get('recommendations', [])
                    }
        
        # 15. 페이지네이션 메타데이터 계산 (5-3단계) - 성능 최적화
        pagination_meta = None
        if offset_data:
            # 성능 최적화: 메타데이터 계산용 쿼리셋 생성
            # (실제 결과와 동일한 필터링 조건 적용, 하지만 SELECT와 LIMIT는 제외)
            meta_queryset = model_class.objects.all()
            
            # JOIN 조건 적용 (메타데이터 계산용)
            if join_applied:
                meta_queryset, meta_join_info = parse_join_conditions(join_data, model_class)
            else:
                meta_join_info = None
            
            # WHERE 조건 적용
            if where_applied:
                meta_queryset = parse_where_conditions(where_data, meta_queryset, meta_join_info)
            
            # ORDER BY 조건은 메타데이터 계산에 불필요하므로 제외 (성능 최적화)
            # 실제 결과에는 ORDER BY가 적용되지만, 전체 개수 계산에는 영향 없음
            
            # JOIN 최적화 (메타데이터 계산용)
            if meta_join_info and meta_join_info.get('join_model'):
                join_table_name = meta_join_info['join_table']
                if meta_join_info['relationship'] == 'many_to_one':
                    meta_queryset = meta_queryset.select_related(join_table_name)
                else:
                    meta_queryset = meta_queryset.prefetch_related(join_table_name)
            
            # 페이지네이션 메타데이터 계산
            pagination_meta = calculate_pagination_metadata(meta_queryset, offset_data, limit)
        
        # 16. OFFSET 조건 정보 수집 (5-2단계) - 기존 로직 유지
        offset_info = None
        if offset_data:
            if isinstance(offset_data, int):
                offset_info = {
                    'offset_type': 'direct',
                    'offset_value': offset_data,
                    'calculated_offset': offset_data
                }
            elif isinstance(offset_data, dict):
                page = offset_data.get('page', 1)
                page_size = offset_data.get('page_size', limit)
                calculated_offset = (page - 1) * page_size
                offset_info = {
                    'offset_type': 'pagination',
                    'page': page,
                    'page_size': page_size,
                    'calculated_offset': calculated_offset
                }
        
        # 17. 응답 메시지 생성 (페이지네이션 메타데이터 포함)
        response_message = f'{table_name} 테이블 조회가 완료되었습니다. (총 {len(results)}개 결과)'
        
        # 페이지네이션 정보 추가 (5-3단계)
        if pagination_meta:
            total_records = pagination_meta['total_records']
            total_pages = pagination_meta['total_pages']
            current_page = pagination_meta['current_page']
            response_message += f' (전체 {total_records}개 중 {pagination_meta["start_record"]}-{pagination_meta["end_record"]}번째, {total_pages}페이지 중 {current_page}페이지)'
        
        if where_applied:
            response_message += f' (WHERE 조건 {len(where_data["conditions"])}개 적용됨)'
        if join_applied:
            response_message += f' (JOIN {join_data["table"]} 테이블 적용됨)'
            if where_applied:
                response_message += ' - JOIN 후 WHERE 조건 최적화 적용'
            
            # JOIN 개선 정보 추가
            if join_info and join_info.get('actual_fields'):
                field_validation = join_info['actual_fields']['field_validation']
                if field_validation['main_field_valid'] and field_validation['join_field_valid']:
                    response_message += ' - 유연한 JOIN 조건 지원'
        
        # ORDER BY 정보 추가 (정렬 최적화 포함)
        if order_by_applied:
            order_count = len(order_by_data) if isinstance(order_by_data, list) else 1
            response_message += f' (ORDER BY {order_count}개 조건 적용됨)'
            
            # 정렬 최적화 정보 추가 (5-4단계)
            if sort_optimization_info and sort_optimization_info.get('analysis'):
                analysis = sort_optimization_info['analysis']
                performance_impact = analysis.get('performance_impact', 'unknown')
                
                if performance_impact == 'low':
                    response_message += ' - 정렬 최적화 완료 (인덱스 활용)'
                elif performance_impact == 'medium':
                    response_message += ' - 정렬 최적화 부분 적용'
                elif performance_impact == 'high':
                    response_message += ' - 정렬 최적화 필요 (인덱스 추가 권장)'
                
                # 최적화 제안이 있는 경우
                suggestions = analysis.get('optimization_suggestions', [])
                if suggestions:
                    high_priority = [s for s in suggestions if s.get('priority') == 'high']
                    if high_priority:
                        response_message += ' - 고우선순위 최적화 제안 있음'
        
        # OFFSET 정보 추가
        if offset_info:
            if offset_info['offset_type'] == 'direct':
                response_message += f' (OFFSET {offset_info["offset_value"]} 적용됨)'
            else:
                response_message += f' (페이지 {offset_info["page"]}, 페이지 크기 {offset_info["page_size"]} 적용됨)'
        
        # 18. 응답 반환 (5-3단계 페이지네이션 메타데이터 포함)
        response_data = {
            'query_info': {
                'executed_sql': f'SELECT {", ".join(select_fields)} FROM {table_name} LIMIT {limit}',
                'execution_time': round(execution_time, 3),
                'total_rows': len(results),
                'table_name': table_name,
                'selected_fields': select_fields,
                'limit_applied': limit,
                'offset_applied': offset_data, # OFFSET 값 추가
                'where_applied': where_applied,
                'where_info': where_info,
                'join_applied': join_applied,
                'join_info': join_info_response,
                'order_by_applied': order_by_applied,
                'order_by_info': order_by_info,
                'offset_applied': offset_info, # OFFSET 정보 추가
                'optimization_applied': {
                    'join_where_optimization': join_applied and where_applied,
                    'query_optimization': join_applied,
                    'execution_order': 'JOIN -> WHERE -> SELECT -> LIMIT (3-5단계 최적화)'
                }
            },
            'results': results
        }
        
        # 페이지네이션 메타데이터 추가 (5-3단계)
        if pagination_meta:
            response_data['pagination'] = pagination_meta
        
        return JsonResponse({
            'success': True,
            'message': response_message,
            'data': response_data
        })
        
    except json.JSONDecodeError as json_error:
        return JsonResponse({
            'success': False,
            'message': f'잘못된 JSON 형식입니다: {str(json_error)}',
            'data': None
        }, status=400)
    except KeyError as key_error:
        return JsonResponse({
            'success': False,
            'message': f'필수 필드가 누락되었습니다: {str(key_error)}',
            'data': None
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'서버 오류가 발생했습니다: {str(e)}',
            'data': None
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def upload_csv_data(request):
    """
    CSV/XLSX 파일 업로드 및 데이터베이스 업데이트 API
    """
    try:
        # 파일 업로드 확인
        if 'csv_file' not in request.FILES:
            return JsonResponse({
                'success': False,
                'message': '파일이 업로드되지 않았습니다.',
                'data': None
            }, status=400)
        
        csv_file = request.FILES['csv_file']
        
        # 파일 확장자 검증
        if not (csv_file.name.endswith('.csv') or csv_file.name.endswith('.xlsx')):
            return JsonResponse({
                'success': False,
                'message': 'CSV 또는 XLSX 파일만 업로드 가능합니다.',
                'data': None
            }, status=400)
        
        # 파일 크기 검증 (100MB 제한)
        if csv_file.size > 100 * 1024 * 1024:
            return JsonResponse({
                'success': False,
                'message': '파일 크기는 100MB를 초과할 수 없습니다.',
                'data': None
            }, status=400)
        
        # 테이블 타입 확인
        table_type = request.POST.get('table_type', 'food')
        if table_type not in ['food', 'price']:
            return JsonResponse({
                'success': False,
                'message': '지원하지 않는 테이블 타입입니다. (food, price만 지원)',
                'data': None
            }, status=400)
        
        # 업로드 모드 확인 (insert, update, upsert)
        upload_mode = request.POST.get('upload_mode', 'upsert')
        if upload_mode not in ['insert', 'update', 'upsert']:
            return JsonResponse({
                'success': False,
                'message': '지원하지 않는 업로드 모드입니다. (insert, update, upsert만 지원)',
                'data': None
            }, status=400)
        
        # 파일 읽기 (CSV 또는 XLSX)
        try:
            if csv_file.name.endswith('.csv'):
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
                    return JsonResponse({
                        'success': False,
                        'message': 'CSV 파일 인코딩을 감지할 수 없습니다. (UTF-8, CP949, EUC-KR 지원)',
                        'data': None
                    }, status=400)
                    
            elif csv_file.name.endswith('.xlsx'):
                # XLSX 파일 읽기
                df = pd.read_excel(csv_file, engine='openpyxl')
                
            else:
                return JsonResponse({
                    'success': False,
                    'message': '지원하지 않는 파일 형식입니다.',
                    'data': None
                }, status=400)
            
        except Exception as file_error:
            return JsonResponse({
                'success': False,
                'message': f'파일 읽기 중 오류가 발생했습니다: {str(file_error)}',
                'data': None
            }, status=400)
        
        # 데이터 검증 및 처리
        start_time = time.time()
        
        try:
            with transaction.atomic():
                if table_type == 'food':
                    result = process_food_data(df, upload_mode)
                elif table_type == 'price':
                    result = process_price_data(df, upload_mode)
                else:
                    return JsonResponse({
                        'success': False,
                        'message': '지원하지 않는 테이블 타입입니다.',
                        'data': None
                    }, status=400)
                
        except Exception as db_error:
            return JsonResponse({
                'success': False,
                'message': f'데이터베이스 처리 중 오류가 발생했습니다: {str(db_error)}',
                'data': None
            }, status=500)
        
        execution_time = time.time() - start_time
        
        # 결과 반환
        return JsonResponse({
            'success': True,
            'message': f'{table_type} 테이블 데이터 업로드가 완료되었습니다.',
            'data': {
                'table_type': table_type,
                'upload_mode': upload_mode,
                'execution_time': round(execution_time, 3),
                'file_info': {
                    'filename': csv_file.name,
                    'file_size': csv_file.size,
                    'total_rows': len(df),
                    'processed_rows': result['processed_rows'],
                    'inserted_rows': result['inserted_rows'],
                    'updated_rows': result['updated_rows'],
                    'skipped_rows': result['skipped_rows'],
                    'error_rows': result['error_rows']
                },
                'processing_details': result['details']
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'서버 오류가 발생했습니다: {str(e)}',
            'data': None
        }, status=500)


def process_food_data(df, upload_mode):
    """
    Food 테이블 데이터 처리
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
    """
    price.shop_name = row.get('shop_name', price.shop_name)
    price.price = int(row.get('price', price.price))
    if row.get('discount_price'):
        price.discount_price = int(row.get('discount_price'))
    if 'is_available' in row:
        price.is_available = bool(row.get('is_available'))


@csrf_exempt
@require_http_methods(["GET"])
def get_csv_template(request):
    """
    CSV 템플릿 다운로드 API
    """
    try:
        table_type = request.GET.get('table_type', 'food')
        
        if table_type == 'food':
            # Food 테이블 템플릿
            template_data = {
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
            template_data = {
                'columns': [
                    'food_id', 'shop_name', 'price', 'discount_price', 'is_available'
                ],
                'sample_data': [
                    'F20240001', '샘플마트', '5000', '4500', 'True'
                ]
            }
        else:
            return JsonResponse({
                'success': False,
                'message': '지원하지 않는 테이블 타입입니다.',
                'data': None
            }, status=400)
        
        return JsonResponse({
            'success': True,
            'message': f'{table_type} 테이블 CSV 템플릿입니다.',
            'data': template_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'서버 오류가 발생했습니다: {str(e)}',
            'data': None
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_database_stats(request):
    """
    데이터베이스 통계 정보 조회 API
    """
    try:
        stats = {
            'food': {
                'total_count': Food.objects.count(),
                'categories': list(Food.objects.values_list('food_category', flat=True).distinct()),
                'companies': list(Food.objects.values_list('company_name', flat=True).distinct())
            },
            'price': {
                'total_count': Price.objects.count(),
                'shops': list(Price.objects.values_list('shop_name', flat=True).distinct()),
                'avg_price': Price.objects.aggregate(avg_price=Avg('price'))['avg_price'] or 0
            }
        }
        
        return JsonResponse({
            'success': True,
            'message': '데이터베이스 통계 정보입니다.',
            'data': stats
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'서버 오류가 발생했습니다: {str(e)}',
            'data': None
        }, status=500)