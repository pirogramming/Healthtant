from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.db.models import Avg
import json
import time
import pandas as pd

# 새로 만든 모듈들 import
from .orm_utils import (
    parse_where_conditions, parse_join_conditions, parse_order_by_conditions,
    parse_offset_conditions, calculate_pagination_metadata, optimize_sorting_query,
    monitor_sorting_performance, extract_order_fields, collect_order_by_info,
    collect_where_info, collect_join_info, collect_offset_info, build_response_message,
    build_query_info, get_database_stats, validate_table_name, get_model_class,
    validate_select_fields, validate_limit_value, validate_offset_data,
    validate_order_by_data, validate_where_data, validate_join_data,
    create_error_response, create_success_response
)
from .csv_processor import (
    process_food_data, process_price_data, validate_file_upload,
    read_csv_file, read_excel_file, get_csv_template_data,
    process_food_data_with_progress, process_price_data_with_progress
)
from foods.models import Food, Price
from accounts.models import UserProfile
from diets.models import Diet

# Create your views here.
def main_page(request):
    """메인 페이지 뷰(바꾸셔도 돼요요)"""
    return render(request, 'main/main_mainpage.html')


def is_admin_user(user):
    """사용자가 admin인지 확인하는 함수"""
    return user.is_authenticated and user.is_staff


@login_required
@user_passes_test(is_admin_user)
def csv_upload_page(request):
    """CSV 업로드 페이지 뷰 (Admin만 접근 가능)"""
    return render(request, 'main/csv_upload.html')



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
            return create_error_response('table 필드가 필요합니다.', 400)
        
        # 3. 테이블명 유효성 검사
        table_name = data['table']
        is_valid, error_message = validate_table_name(table_name)
        if not is_valid:
            return create_error_response(error_message, 400)
        
        # 4. 테이블명에 따른 모델 매핑
        model_class = get_model_class(table_name)
        if not model_class:
            return create_error_response('지원하지 않는 테이블입니다.', 400)
        
        # 5. SELECT 필드 결정 및 유효성 검사 (3-5단계 개선)
        select_fields = data.get('select', [])
        is_valid, available_fields, error_message = validate_select_fields(select_fields, model_class, data.get('join'))
        if not is_valid:
            return create_error_response(error_message, 400)
        
        # select_fields가 비어있으면 모든 필드 선택
        if not select_fields:
            select_fields = available_fields
        
        # 6. WHERE 조건 처리
        where_data = data.get('where', None)
        is_valid, where_applied, error_message = validate_where_data(where_data)
        if not is_valid:
            return create_error_response(error_message, 400)
        
        # 7. JOIN 조건 처리 (3-5단계 최적화)
        join_data = data.get('join', None)
        is_valid, join_applied, error_message = validate_join_data(join_data)
        if not is_valid:
            return create_error_response(error_message, 400)
        
        # 8. ORDER BY 조건 처리 (5-1단계)
        order_by_data = data.get('order_by', None)
        is_valid, order_by_applied, error_message = validate_order_by_data(order_by_data)
        if not is_valid:
            return create_error_response(error_message, 400)
        
        # 9. LIMIT 값 검증
        limit = data.get('limit', 100)
        is_valid, limit, error_message = validate_limit_value(limit)
        if not is_valid:
            return create_error_response(error_message, 400)
        
        # 10. OFFSET 값 검증 및 적용 (5-2단계)
        offset_data = data.get('offset', 0)
        is_valid, offset_data, error_message = validate_offset_data(offset_data)
        if not is_valid:
            return create_error_response(error_message, 400)
        
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
                order_fields = extract_order_fields(order_by_data)
                
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
            return create_error_response(f'쿼리 실행 중 오류가 발생했습니다: {str(query_error)}', 500)
        
        execution_time = time.time() - start_time
        
        # 정렬 성능 모니터링 (5-4단계)
        sorting_performance_metrics = None
        if order_by_applied and sort_optimization_info:
            # 정렬 필드 추출 (모니터링용)
            monitor_order_fields = extract_order_fields(order_by_data)
            
            if monitor_order_fields:
                sorting_performance_metrics = monitor_sorting_performance(
                    queryset, monitor_order_fields, execution_time, model_class
                )
        
        # 12. WHERE 조건 정보 수집
        where_info = collect_where_info(where_data)
        
        # 13. JOIN 조건 정보 수집 (개선: 상세 정보 추가)
        join_info_response = collect_join_info(join_data, join_info)
        
        # 14. ORDER BY 조건 정보 수집 및 정렬 최적화 정보 (5-4단계)
        order_by_info = collect_order_by_info(order_by_data, sort_optimization_info, sorting_performance_metrics)
        
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
        offset_info = collect_offset_info(offset_data, limit)
        
        # 17. 응답 메시지 생성 (페이지네이션 메타데이터 포함)
        response_message = build_response_message(
            table_name, results, pagination_meta, where_applied, 
            where_data, join_applied, join_data, join_info, 
            order_by_applied, order_by_data, sort_optimization_info, 
            offset_info
        )
        
        # 18. 응답 반환 (5-3단계 페이지네이션 메타데이터 포함)
        response_data = {
            'query_info': build_query_info(
                table_name, select_fields, limit, offset_data, where_applied, 
                where_info, join_applied, join_info_response, order_by_applied, 
                order_by_info, offset_info, execution_time, results
            ),
            'results': results
        }
        
        # 페이지네이션 메타데이터 추가 (5-3단계)
        if pagination_meta:
            response_data['pagination'] = pagination_meta
        
        return create_success_response(response_message, response_data)
        
    except json.JSONDecodeError as json_error:
        return create_error_response(f'잘못된 JSON 형식입니다: {str(json_error)}', 400)
    except KeyError as key_error:
        return create_error_response(f'필수 필드가 누락되었습니다: {str(key_error)}', 400)
    except Exception as e:
        return create_error_response(f'서버 오류가 발생했습니다: {str(e)}', 500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
@user_passes_test(is_admin_user)
def upload_csv_data(request):
    """
    CSV/XLSX 파일 업로드 및 데이터베이스 업데이트 API (실시간 진행상황 추적)
    """
    try:
        print(f"[UPLOAD] 새로운 파일 업로드 요청 시작")
        
        # 파일 업로드 확인
        if 'csv_file' not in request.FILES:
            print(f"[UPLOAD] 오류: 파일이 업로드되지 않음")
            return create_error_response('파일이 업로드되지 않았습니다.', 400)
        
        csv_file = request.FILES['csv_file']
        print(f"[UPLOAD] 파일 수신: {csv_file.name} ({csv_file.size / 1024 / 1024:.2f} MB)")
        
        # 파일 유효성 검사
        table_type = request.POST.get('table_type', 'food')
        upload_mode = request.POST.get('upload_mode', 'upsert')
        print(f"[UPLOAD] 테이블 타입: {table_type}, 업로드 모드: {upload_mode}")
        
        try:
            validate_file_upload(csv_file, table_type, upload_mode)
            print(f"[UPLOAD] 파일 유효성 검사 통과")
        except ValueError as validation_error:
            print(f"[UPLOAD] 유효성 검사 실패: {validation_error}")
            return create_error_response(str(validation_error), 400)
        
        # 파일 읽기 (CSV 또는 XLSX)
        try:
            print(f"[UPLOAD] 파일 읽기 시작: {csv_file.name}")
            if csv_file.name.endswith('.csv'):
                df = read_csv_file(csv_file)
                print(f"[UPLOAD] CSV 파일 읽기 완료: {len(df)}행")
            elif csv_file.name.endswith('.xlsx'):
                df = read_excel_file(csv_file)
                print(f"[UPLOAD] XLSX 파일 읽기 완료: {len(df)}행")
            else:
                print(f"[UPLOAD] 지원하지 않는 파일 형식: {csv_file.name}")
                return create_error_response('지원하지 않는 파일 형식입니다.', 400)
                    
        except ValueError as file_error:
            print(f"[UPLOAD] 파일 읽기 오류 (ValueError): {file_error}")
            return create_error_response(str(file_error), 400)
        except Exception as file_error:
            print(f"[UPLOAD] 파일 읽기 오류 (Exception): {file_error}")
            return create_error_response(f'파일 읽기 중 오류가 발생했습니다: {str(file_error)}', 400)
        
        # 진행상황 추적을 위한 세션 키 생성
        import uuid
        progress_key = f"upload_progress_{uuid.uuid4().hex[:8]}"
        print(f"[UPLOAD] 진행상황 키 생성: {progress_key}")
        
        # 초기 진행상황 설정
        request.session[progress_key] = {
            'status': 'processing',
            'total_rows': len(df),
            'processed_rows': 0,
            'current_step': '데이터 검증 중...',
            'progress_percentage': 0,
            'start_time': time.time(),
            'estimated_time': '계산 중...',
            'details': []
        }
        print(f"[UPLOAD] 초기 진행상황 설정 완료: {len(df)}행, 상태: processing")
        
        # 데이터 검증 및 처리
        start_time = time.time()
        print(f"[UPLOAD] 데이터베이스 처리 시작: {table_type} 테이블, {upload_mode} 모드")
        
        try:
            with transaction.atomic():
                print(f"[UPLOAD] 트랜잭션 시작")
                if table_type == 'food':
                    print(f"[UPLOAD] Food 테이블 처리 시작: {len(df)}행")
                    result = process_food_data_with_progress(df, upload_mode, request.session, progress_key)
                elif table_type == 'price':
                    print(f"[UPLOAD] Price 테이블 처리 시작: {len(df)}행")
                    result = process_price_data_with_progress(df, upload_mode, request.session, progress_key)
                else:
                    print(f"[UPLOAD] 지원하지 않는 테이블 타입: {table_type}")
                    return create_error_response('지원하지 않는 테이블 타입입니다.', 400)
                
                print(f"[UPLOAD] 데이터 처리 완료: {result['processed_rows']}행 처리됨")
                
        except Exception as db_error:
            # 오류 발생 시 진행상황 업데이트
            print(f"[UPLOAD] 데이터베이스 처리 오류: {db_error}")
            request.session[progress_key]['status'] = 'error'
            request.session[progress_key]['current_step'] = f'오류 발생: {str(db_error)}'
            return create_error_response(f'데이터베이스 처리 중 오류가 발생했습니다: {str(db_error)}', 500)
        
        execution_time = time.time() - start_time
        print(f"[UPLOAD] 전체 처리 시간: {execution_time:.3f}초")
        
        # 완료 상태로 진행상황 업데이트
        request.session[progress_key].update({
            'status': 'completed',
            'processed_rows': result['processed_rows'],
            'current_step': '처리 완료!',
            'progress_percentage': 100,
            'execution_time': round(execution_time, 3),
            'final_result': result
        })
        print(f"[UPLOAD] 진행상황 완료 상태로 업데이트: {progress_key}")
        
        # 결과 반환
        print(f"[UPLOAD] 업로드 완료! 결과 반환 중...")
        print(f"[UPLOAD] 최종 결과: {result['processed_rows']}행 중 {result['inserted_rows']}개 생성, {result['updated_rows']}개 수정")
        
        return create_success_response(
            f'{table_type} 테이블 데이터 업로드가 완료되었습니다.',
            {
                'progress_key': progress_key,
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
        )
        
    except Exception as e:
        return create_error_response(f'서버 오류가 발생했습니다: {str(e)}', 500)


@csrf_exempt
@require_http_methods(["GET"])
@login_required
@user_passes_test(is_admin_user)
def get_upload_progress(request):
    """
    파일 업로드 진행상황 조회 API (Admin만 접근 가능)
    """
    try:
        progress_key = request.GET.get('progress_key')
        if not progress_key:
            print(f"[PROGRESS] 오류: 진행상황 키가 없음")
            return create_error_response('진행상황 키가 필요합니다.', 400)
        
        print(f"[PROGRESS] 진행상황 조회: {progress_key}")
        progress_data = request.session.get(progress_key, {})
        if not progress_data:
            print(f"[PROGRESS] 진행상황을 찾을 수 없음: {progress_key}")
            return create_error_response('진행상황을 찾을 수 없습니다.', 404)
        
        current_step = progress_data.get('current_step', '알 수 없음')
        progress_percentage = progress_data.get('progress_percentage', 0)
        print(f"[PROGRESS] 진행상황 반환: {progress_key} - {current_step} ({progress_percentage}%)")
        
        return create_success_response('진행상황 정보입니다.', progress_data)
        
    except Exception as e:
        print(f"[PROGRESS] 오류 발생: {e}")
        return create_error_response(f'서버 오류가 발생했습니다: {str(e)}', 500)


@csrf_exempt
@require_http_methods(["GET"])
@login_required
@user_passes_test(is_admin_user)
def get_csv_template(request):
    """
    CSV 템플릿 다운로드 API (Admin만 접근 가능)
    """
    try:
        table_type = request.GET.get('table_type', 'food')
        
        try:
            template_data = get_csv_template_data(table_type)
        except ValueError as template_error:
            return create_error_response(str(template_error), 400)
        
        return create_success_response(f'{table_type} 테이블 CSV 템플릿입니다.', template_data)
        
    except Exception as e:
        return create_error_response(f'서버 오류가 발생했습니다: {str(e)}', 500)


@csrf_exempt
@require_http_methods(["GET"])
@login_required
@user_passes_test(is_admin_user)
def get_database_stats(request):
    """
    데이터베이스 통계 정보 조회 API (Admin만 접근 가능)
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
        
        return create_success_response('데이터베이스 통계 정보입니다.', stats)
        
    except Exception as e:
        return create_error_response(f'서버 오류가 발생했습니다: {str(e)}', 500)
def permission_denied_view(request, exception=None):
    """403 에러 페이지 뷰"""
    return render(request, 'errors/errors_403.html', status=403)

def not_found_view(request, exception=None):
    """404 에러 페이지 뷰"""
    return render(request, 'errors/errors_404.html', status=404)

def bad_request_view(request, exception=None):
    """400 에러 페이지 뷰"""
    return render(request, 'errors/errors_400.html', status=400)

def server_error_view(request, exception=None):
    """500 에러 페이지 뷰"""
    return render(request, 'errors/errors_500.html', status=500)
