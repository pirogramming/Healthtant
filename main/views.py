from django.shortcuts import render

# Create your views here.
def main_page(request):
    """메인 페이지 뷰(바꾸셔도 돼요요)"""
    return render(request, 'main/main_mainpage.html')

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
