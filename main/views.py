from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import connection
from django.db.models import Q
import json
import time
from foods.models import Food, Price
from accounts.models import UserProfile
from diets.models import Diet

# Create your views here.
def main_page(request):
    """메인 페이지 뷰(바꾸셔도 돼요요)"""
    return render(request, 'main/main_mainpage.html')

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
        
        # 8. LIMIT 값 검증
        limit = data.get('limit', 100)
        if not isinstance(limit, int) or limit < 1:
            return JsonResponse({
                'success': False,
                'message': 'limit은 1 이상의 정수여야 합니다.',
                'data': None
            }, status=400)
        
        if limit > 1000:  # 최대 1000개로 제한
            limit = 1000
        
        # 9. 쿼리 실행 (3-5단계 최적화된 순서)
        start_time = time.time()
        
        try:
            # 1단계: JOIN 조건 적용 (기본 구조만)
            queryset, join_info = parse_join_conditions(join_data, model_class)
            
            # 2단계: WHERE 조건 적용 (JOIN된 테이블 필드 지원)
            queryset = parse_where_conditions(where_data, queryset, join_info)
            
            # 3단계: SELECT 필드 적용 (JOIN된 테이블 필드 포함)
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
            
            # 4단계: 쿼리 최적화 (3-5단계)
            if join_info:
                # JOIN이 있는 경우 쿼리 최적화
                if join_info['relationship'] == 'many_to_one':
                    # N:1 관계인 경우 select_related로 최적화
                    queryset = queryset.select_related(join_info['join_table'])
                else:
                    # 1:N 관계인 경우 prefetch_related로 최적화
                    queryset = queryset.prefetch_related(join_info['join_table'])
            
            # 5단계: SELECT 필드 적용 (최적화된 순서)
            queryset = queryset.values(*select_fields)
            
            # 6단계: LIMIT 적용 (성능 최적화)
            queryset = queryset[:limit]
            
            # 7단계: 결과 변환 (지연 평가)
            results = list(queryset)
            
        except Exception as query_error:
            return JsonResponse({
                'success': False,
                'message': f'쿼리 실행 중 오류가 발생했습니다: {str(query_error)}',
                'data': None
            }, status=500)
        
        execution_time = time.time() - start_time
        
        # 10. WHERE 조건 정보 수집
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
        
        # 11. JOIN 조건 정보 수집 (개선: 상세 정보 추가)
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
        
        # 12. 응답 메시지 생성 (JOIN 개선 반영)
        response_message = f'{table_name} 테이블 조회가 완료되었습니다. (총 {len(results)}개 결과)'
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
        
        # 13. 응답 반환 (3-5단계 개선)
        return JsonResponse({
            'success': True,
            'message': response_message,
            'data': {
                'query_info': {
                    'executed_sql': f'SELECT {", ".join(select_fields)} FROM {table_name} LIMIT {limit}',
                    'execution_time': round(execution_time, 3),
                    'total_rows': len(results),
                    'table_name': table_name,
                    'selected_fields': select_fields,
                    'limit_applied': limit,
                    'where_applied': where_applied,
                    'where_info': where_info,
                    'join_applied': join_applied,
                    'join_info': join_info_response,
                    'optimization_applied': {
                        'join_where_optimization': join_applied and where_applied,
                        'query_optimization': join_applied,
                        'execution_order': 'JOIN -> WHERE -> SELECT -> LIMIT (3-5단계 최적화)'
                    }
                },
                'results': results
            }
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