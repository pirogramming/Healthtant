from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

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
        
        # 4. 기본 응답 (아직 쿼리 실행 안함)
        return JsonResponse({
            'success': True,
            'message': f'{table_name} 테이블 요청이 유효합니다.',
            'data': {
                'query_info': {
                    'executed_sql': '아직 구현되지 않음',
                    'execution_time': 0.0,
                    'total_rows': 0
                },
                'results': []
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