from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import connection
import json
import time
from foods.models import Food, Price
from accounts.models import UserProfile
from diets.models import Diet

# Create your views here.
def main_page(request):
    """메인 페이지 뷰(바꾸셔도 돼요요)"""
    return render(request, 'main/main_mainpage.html')

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
        
        # 5. SELECT 필드 결정
        select_fields = data.get('select', [])
        if not select_fields:
            # select 필드가 없으면 모든 필드 선택
            select_fields = [field.name for field in model_class._meta.fields]
        
        # 6. 기본 쿼리 실행
        start_time = time.time()
        
        # values() 메서드로 딕셔너리 형태로 결과 반환
        queryset = model_class.objects.values(*select_fields)
        
        # LIMIT 처리 (기본값: 100)
        limit = data.get('limit', 100)
        if limit > 1000:  # 최대 1000개로 제한
            limit = 1000
        queryset = queryset[:limit]
        
        # 결과를 리스트로 변환
        results = list(queryset)
        
        execution_time = time.time() - start_time
        
        # 7. 응답 반환
        return JsonResponse({
            'success': True,
            'message': f'{table_name} 테이블 조회가 완료되었습니다.',
            'data': {
                'query_info': {
                    'executed_sql': f'SELECT {", ".join(select_fields)} FROM {table_name} LIMIT {limit}',
                    'execution_time': round(execution_time, 3),
                    'total_rows': len(results)
                },
                'results': results
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '잘못된 JSON 형식입니다.',
            'data': None
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'서버 오류가 발생했습니다: {str(e)}',
            'data': None
        }, status=500)