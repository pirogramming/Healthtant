from django.shortcuts import render

# Create your views here.
def main_page(request):
    """메인 페이지 뷰(바꾸셔도 돼요요)"""
    return render(request, 'main/main_mainpage.html')