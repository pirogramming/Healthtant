from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.main_page, name='main_page'),
    path('csv-upload/', views.csv_upload_page, name='csv_upload_page'),
    path('db/', views.db_explorer, name='db_explorer'),
    path('upload-csv/', views.upload_csv_data, name='upload_csv_data'),
    path('upload-progress/', views.get_upload_progress, name='get_upload_progress'),
    path('csv-template/', views.get_csv_template, name='get_csv_template'),
    path('db-stats/', views.get_database_stats, name='get_database_stats'),
    path('test-400/', views.bad_request_view, name='test_400'),
    path('test-403/', views.permission_denied_view, name='test_403'),
    path('test-404/', views.not_found_view, name='test_404'),
    path('test-500/', views.server_error_view, name='test_500'),
    
    # 크롤링 관련
    path('crawling-management/', views.crawling_management_page, name='crawling_management'),
    path('api/start-crawling/', views.start_crawling, name='start_crawling'),
    path('api/start-all-crawling/', views.start_all_crawling, name='start_all_crawling'),
    path('api/crawling-status/', views.get_crawling_status, name='get_crawling_status'),
    path('api/retry-crawling/', views.retry_failed_crawling, name='retry_failed_crawling'),
]