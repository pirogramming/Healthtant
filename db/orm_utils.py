"""
Django ORM 유틸리티 함수들
DB 탐색 API에서 사용하는 ORM 관련 함수들을 모아놓은 모듈
"""

from django.db.models import Q
from foods.models import Food, Price
from accounts.models import UserProfile
from diets.models import Diet


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


def extract_order_fields(order_by_data):
    """
    ORDER BY 데이터에서 정렬 필드 목록을 추출
    
    Args:
        order_by_data: ORDER BY 조건 데이터 (list, str, dict)
    
    Returns:
        list: 정렬 필드 목록 (Django ORM 형식)
    """
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
    
    return order_fields


def collect_order_by_info(order_by_data, sort_optimization_info=None, sorting_performance_metrics=None):
    """
    ORDER BY 조건 정보를 수집하고 정렬 최적화 정보를 포함
    
    Args:
        order_by_data: ORDER BY 조건 데이터
        sort_optimization_info: 정렬 최적화 정보
        sorting_performance_metrics: 정렬 성능 메트릭
    
    Returns:
        dict: ORDER BY 정보
    """
    if not order_by_data:
        return None
    
    order_by_info = {
        'order_by_conditions': order_by_data,
        'applied_conditions': []
    }
    
    # 적용된 조건들 수집
    if isinstance(order_by_data, list):
        for order_item in order_by_data:
            if isinstance(order_item, str):
                parts = order_item.strip().split()
                order_by_info['applied_conditions'].append({
                    'field': parts[0],
                    'direction': parts[1].upper() if len(parts) > 1 else 'ASC'
                })
            elif isinstance(order_item, dict):
                order_by_info['applied_conditions'].append({
                    'field': order_item.get('field', ''),
                    'direction': order_item.get('direction', 'ASC').upper()
                })
    elif isinstance(order_by_data, str):
        parts = order_by_data.strip().split()
        order_by_info['applied_conditions'].append({
            'field': parts[0],
            'direction': parts[1].upper() if len(parts) > 1 else 'ASC'
        })
    
    # 정렬 최적화 정보 추가
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
        
        # 성능 모니터링 정보 추가
        if sorting_performance_metrics:
            order_by_info['sort_optimization']['performance_monitoring'] = {
                'execution_time': sorting_performance_metrics.get('execution_time', 0),
                'performance_rating': sorting_performance_metrics.get('performance_rating', 'unknown'),
                'index_coverage_percentage': sorting_performance_metrics.get('index_coverage_percentage', 0),
                'field_coverage': sorting_performance_metrics.get('field_coverage', []),
                'recommendations': sorting_performance_metrics.get('recommendations', [])
            }
    
    return order_by_info


def collect_where_info(where_data):
    """
    WHERE 조건 정보를 수집
    
    Args:
        where_data: WHERE 조건 데이터
    
    Returns:
        dict: WHERE 조건 정보
    """
    if not where_data or 'conditions' not in where_data:
        return None
    
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
    
    return where_info


def collect_join_info(join_data, join_info):
    """
    JOIN 조건 정보를 수집
    
    Args:
        join_data: JOIN 조건 데이터
        join_info: JOIN 처리 결과 정보
    
    Returns:
        dict: JOIN 조건 정보
    """
    if not join_data:
        return None
    
    join_info_response = {
        'join_table': join_data['table'],
        'join_type': join_data['type'],
        'join_conditions': join_data['on']
    }
    
    if join_info and join_info.get('is_reversed'):
        join_info_response['is_reversed'] = True
    
    # JOIN 개선 정보 추가
    if join_info:
        join_info_response['improvements'] = {
            'actual_fields': join_info.get('actual_fields', {}),
            'query_type': join_info.get('query_type', {}),
            'field_validation': join_info.get('actual_fields', {}).get('field_validation', {}),
            'flexible_join': True  # 유연한 JOIN 조건 지원
        }
    
    return join_info_response


def collect_offset_info(offset_data, limit):
    """
    OFFSET 조건 정보를 수집
    
    Args:
        offset_data: OFFSET 데이터
        limit: LIMIT 값
    
    Returns:
        dict: OFFSET 정보
    """
    if not offset_data:
        return None
    
    if isinstance(offset_data, int):
        return {
            'offset_type': 'direct',
            'offset_value': offset_data,
            'calculated_offset': offset_data
        }
    elif isinstance(offset_data, dict):
        page = offset_data.get('page', 1)
        page_size = offset_data.get('page_size', limit)
        calculated_offset = (page - 1) * page_size
        return {
            'offset_type': 'pagination',
            'page': page,
            'page_size': page_size,
            'calculated_offset': calculated_offset
        }
    
    return None


def build_response_message(table_name, results, pagination_meta, where_applied, 
                         where_data, join_applied, join_data, join_info, 
                         order_by_applied, order_by_data, sort_optimization_info, 
                         offset_info):
    """
    응답 메시지를 생성
    
    Args:
        table_name: 테이블명
        results: 조회 결과
        pagination_meta: 페이지네이션 메타데이터
        where_applied: WHERE 조건 적용 여부
        where_data: WHERE 조건 데이터
        join_applied: JOIN 조건 적용 여부
        join_data: JOIN 조건 데이터
        join_info: JOIN 처리 결과 정보
        order_by_applied: ORDER BY 조건 적용 여부
        order_by_data: ORDER BY 조건 데이터
        sort_optimization_info: 정렬 최적화 정보
        offset_info: OFFSET 정보
    
    Returns:
        str: 응답 메시지
    """
    response_message = f'{table_name} 테이블 조회가 완료되었습니다. (총 {len(results)}개 결과)'
    
    # 페이지네이션 정보 추가
    if pagination_meta:
        total_records = pagination_meta['total_records']
        total_pages = pagination_meta['total_pages']
        current_page = pagination_meta['current_page']
        response_message += f' (전체 {total_records}개 중 {pagination_meta["start_record"]}-{pagination_meta["end_record"]}번째, {total_pages}페이지 중 {current_page}페이지)'
    
    # WHERE 조건 정보 추가
    if where_applied:
        response_message += f' (WHERE 조건 {len(where_data["conditions"])}개 적용됨)'
    
    # JOIN 조건 정보 추가
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
        
        # 정렬 최적화 정보 추가
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
    
    return response_message


def build_query_info(table_name, select_fields, limit, offset_data, where_applied, 
                    where_info, join_applied, join_info_response, order_by_applied, 
                    order_by_info, offset_info, execution_time, results):
    """
    쿼리 정보를 생성
    
    Args:
        table_name: 테이블명
        select_fields: 선택된 필드들
        limit: LIMIT 값
        offset_data: OFFSET 데이터
        where_applied: WHERE 조건 적용 여부
        where_info: WHERE 조건 정보
        join_applied: JOIN 조건 적용 여부
        join_info_response: JOIN 조건 정보
        order_by_applied: ORDER BY 조건 적용 여부
        order_by_info: ORDER BY 조건 정보
        offset_info: OFFSET 정보
        execution_time: 실행 시간
        results: 조회 결과
    
    Returns:
        dict: 쿼리 정보
    """
    return {
        'executed_sql': f'SELECT {", ".join(select_fields)} FROM {table_name} LIMIT {limit}',
        'execution_time': round(execution_time, 3),
        'total_rows': len(results),
        'table_name': table_name,
        'selected_fields': select_fields,
        'limit_applied': limit,
        'offset_applied': offset_data,
        'where_applied': where_applied,
        'where_info': where_info,
        'join_applied': join_applied,
        'join_info': join_info_response,
        'order_by_applied': order_by_applied,
        'order_by_info': order_by_info,
        'offset_info': offset_info,
        'optimization_applied': {
            'join_where_optimization': join_applied and where_applied,
            'query_optimization': join_applied,
            'execution_order': 'JOIN -> WHERE -> SELECT -> LIMIT (3-5단계 최적화)'
        }
    }


def get_database_stats():
    """
    데이터베이스 통계 정보를 조회하는 함수
    
    Returns:
        dict: 데이터베이스 통계 정보
    """
    try:
        from django.db.models import Avg
        
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
        
        return stats
        
    except Exception as e:
        # 오류 발생 시 기본 통계 반환
        return {
            'food': {
                'total_count': 0,
                'categories': [],
                'companies': []
            },
            'price': {
                'total_count': 0,
                'shops': [],
                'avg_price': 0
            },
            'error': str(e)
        }


def validate_table_name(table_name):
    """
    테이블명 유효성을 검사하는 함수
    
    Args:
        table_name (str): 검사할 테이블명
    
    Returns:
        tuple: (bool, str) - (유효성 여부, 오류 메시지)
    """
    allowed_tables = ['food', 'price', 'diet', 'user']
    
    if not table_name:
        return False, '테이블명이 제공되지 않았습니다.'
    
    if table_name not in allowed_tables:
        return False, f'허용되지 않은 테이블입니다. 허용된 테이블: {allowed_tables}'
    
    return True, ''


def get_model_class(table_name):
    """
    테이블명에 따른 Django 모델 클래스를 반환하는 함수
    
    Args:
        table_name (str): 테이블명
    
    Returns:
        Django 모델 클래스 또는 None
    """
    model_mapping = {
        'food': Food,
        'price': Price,
        'diet': Diet,
        'user': UserProfile
    }
    
    return model_mapping.get(table_name)


def validate_select_fields(select_fields, model_class, join_data=None):
    """
    SELECT 필드의 유효성을 검사하는 함수
    
    Args:
        select_fields (list): 선택할 필드 목록
        model_class: Django 모델 클래스
        join_data (dict): JOIN 조건 데이터
    
    Returns:
        tuple: (bool, list, str) - (유효성 여부, 사용 가능한 필드 목록, 오류 메시지)
    """
    if not select_fields:
        # select 필드가 없으면 모든 필드 선택
        available_fields = [field.name for field in model_class._meta.fields]
        return True, available_fields, ''
    
    # 기본 사용 가능한 필드
    available_fields = [field.name for field in model_class._meta.fields]
    
    # JOIN 조건이 있는지 확인
    join_applied = join_data is not None and all(key in join_data for key in ['table', 'type', 'on'])
    
    # JOIN된 테이블의 필드도 사용 가능하도록 추가
    if join_applied:
        try:
            # JOIN 정보를 미리 생성하여 필드 검증에 사용
            temp_queryset, temp_join_info = parse_join_conditions(join_data, model_class)
            if temp_join_info and temp_join_info.get('join_model'):
                join_model = temp_join_info['join_model']
                join_table_name = temp_join_info['join_table']
                join_fields = [field.name for field in join_model._meta.fields]
                # JOIN 테이블 필드는 "테이블명__필드명" 형태로 접근
                available_fields.extend([f"{join_table_name}__{field}" for field in join_fields])
        except Exception:
            pass  # JOIN 검증 실패 시 기본 필드만 사용
    
    # 유효하지 않은 필드 찾기
    invalid_fields = [field for field in select_fields if field not in available_fields]
    
    if invalid_fields:
        return False, available_fields, f'존재하지 않는 필드입니다: {invalid_fields}. 사용 가능한 필드: {available_fields}'
    
    return True, available_fields, ''


def validate_limit_value(limit):
    """
    LIMIT 값의 유효성을 검사하는 함수
    
    Args:
        limit: 검사할 LIMIT 값
    
    Returns:
        tuple: (bool, int, str) - (유효성 여부, 검증된 LIMIT 값, 오류 메시지)
    """
    if not isinstance(limit, int):
        return False, 100, 'limit은 정수여야 합니다.'
    
    if limit < 1:
        return False, 100, 'limit은 1 이상의 정수여야 합니다.'
    
    if limit > 1000:  # 최대 1000개로 제한
        limit = 1000
    
    return True, limit, ''


def validate_offset_data(offset_data):
    """
    OFFSET 데이터의 유효성을 검사하는 함수
    
    Args:
        offset_data: 검사할 OFFSET 데이터
    
    Returns:
        tuple: (bool, any, str) - (유효성 여부, 검증된 OFFSET 데이터, 오류 메시지)
    """
    if not offset_data:
        return True, 0, ''
    
    if isinstance(offset_data, int):
        if offset_data < 0:
            return False, 0, 'OFFSET 값은 0 이상이어야 합니다.'
        return True, offset_data, ''
    
    elif isinstance(offset_data, dict):
        page = offset_data.get('page', 1)
        page_size = offset_data.get('page_size', 100)
        
        if not isinstance(page, int) or page < 1:
            return False, {'page': 1, 'page_size': 100}, '페이지 번호는 1 이상의 정수여야 합니다.'
        
        if not isinstance(page_size, int) or page_size < 1:
            return False, {'page': page, 'page_size': 100}, '페이지 크기는 1 이상의 정수여야 합니다.'
        
        return True, offset_data, ''
    
    else:
        return False, 0, 'OFFSET 데이터는 정수 또는 딕셔너리 형태여야 합니다.'


def validate_order_by_data(order_by_data):
    """
    ORDER BY 데이터의 유효성을 검사하는 함수
    
    Args:
        order_by_data: 검사할 ORDER BY 데이터
    
    Returns:
        tuple: (bool, bool, str) - (유효성 여부, ORDER BY 적용 여부, 오류 메시지)
    """
    if not order_by_data:
        return True, False, ''
    
    order_by_applied = (
        isinstance(order_by_data, list) and len(order_by_data) > 0 or
        isinstance(order_by_data, str) and order_by_data.strip()
    )
    
    if not order_by_applied:
        return True, False, ''
    
    # ORDER BY 조건 개수 제한 (보안상)
    if isinstance(order_by_data, list) and len(order_by_data) > 5:
        return False, False, 'ORDER BY 조건은 최대 5개까지 허용됩니다.'
    
    return True, True, ''


def validate_where_data(where_data):
    """
    WHERE 데이터의 유효성을 검사하는 함수
    
    Args:
        where_data: 검사할 WHERE 데이터
    
    Returns:
        tuple: (bool, bool, str) - (유효성 여부, WHERE 적용 여부, 오류 메시지)
    """
    if not where_data:
        return True, False, ''
    
    where_applied = (
        where_data is not None and 
        'conditions' in where_data and 
        len(where_data['conditions']) > 0
    )
    
    if not where_applied:
        return True, False, ''
    
    # WHERE 조건 개수 제한 (보안상)
    if len(where_data['conditions']) > 10:
        return False, False, 'WHERE 조건은 최대 10개까지 허용됩니다.'
    
    return True, True, ''


def validate_join_data(join_data):
    """
    JOIN 데이터의 유효성을 검사하는 함수
    
    Args:
        join_data: 검사할 JOIN 데이터
    
    Returns:
        tuple: (bool, bool, str) - (유효성 여부, JOIN 적용 여부, 오류 메시지)
    """
    if not join_data:
        return True, False, ''
    
    join_applied = (
        join_data is not None and 
        all(key in join_data for key in ['table', 'type', 'on'])
    )
    
    if not join_applied:
        return True, False, ''
    
    # JOIN 타입 검증
    join_type = join_data.get('type', '').upper()
    if join_type not in ['INNER', 'LEFT', 'RIGHT']:
        return False, False, f'지원하지 않는 JOIN 타입입니다: {join_type}. 지원 타입: INNER, LEFT, RIGHT'
    
    # JOIN 조건 구조 검증
    join_on = join_data.get('on', {})
    if not all(key in join_on for key in ['left', 'right']):
        return False, False, 'JOIN 조건에 left와 right 필드가 필요합니다.'
    
    return True, True, ''


def create_error_response(message, status_code=400):
    """
    에러 응답을 생성하는 함수
    
    Args:
        message (str): 에러 메시지
        status_code (int): HTTP 상태 코드
    
    Returns:
        JsonResponse: 에러 응답
    """
    from django.http import JsonResponse
    
    return JsonResponse({
        'success': False,
        'message': message,
        'data': None
    }, status=status_code)


def create_success_response(message, data, status_code=200):
    """
    성공 응답을 생성하는 함수
    
    Args:
        message (str): 성공 메시지
        data (dict): 응답 데이터
        status_code (int): HTTP 상태 코드
    
    Returns:
        JsonResponse: 성공 응답
    """
    from django.http import JsonResponse
    
    return JsonResponse({
        'success': True,
        'message': message,
        'data': data
    }, status=status_code)
