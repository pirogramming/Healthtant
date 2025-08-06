from django.contrib import admin
from .models import Diet


@admin.register(Diet)
class DietAdmin(admin.ModelAdmin):
    list_display = ['diet_id', 'user', 'food', 'date', 'meal', 'created_at']
    list_filter = ['meal', 'date', 'created_at']
    search_fields = ['user__username', 'food__food_name']
    readonly_fields = ['diet_id', 'created_at', 'updated_at']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('식단 정보', {
            'fields': ('diet_id', 'user', 'food', 'date', 'meal')
        }),
        ('시간 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )