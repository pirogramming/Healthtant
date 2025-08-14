from django.urls import path
from . import views

app_name = 'db'

urlpatterns = [
    path('csv-upload/', views.csv_upload_page, name='csv_upload_page'),
    path('db_explorer/', views.db_explorer, name='db_explorer'),
    path('upload-csv/', views.upload_csv_data, name='upload_csv_data'),
    path('upload-progress/', views.get_upload_progress, name='get_upload_progress'),
    path('csv-template/', views.get_csv_template, name='get_csv_template'),
    path('db-stats/', views.get_database_stats, name='get_database_stats')
]