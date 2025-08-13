from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'nickname', 'user_gender', 'user_age', 'created_at']
    list_filter = ['user_gender', 'user_age', 'created_at']
    search_fields = ['user__username', 'nickname', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('사용자 정보', {
            'fields': ('user', 'nickname')
        }),
        ('개인 정보', {
            'fields': ('user_gender', 'user_age', 'profile_image_url')
        }),
        ('시간 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
