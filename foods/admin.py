from django.contrib import admin
from .models import Food


@admin.register(Food)
class FoodAdmin(admin.ModelAdmin):
    list_display = ['food_id', 'food_name', 'company_name', 'food_category', 'lprice']
    list_filter = ['food_category', 'company_name']
    search_fields = ['food_name', 'company_name', 'representative_food']
    readonly_fields = ['food_id']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('food_id', 'food_name', 'company_name', 'food_category', 'representative_food', 'food_img')
        }),
        ('영양성분 (기준량 100g)', {
            'fields': ('nutritional_value_standard_amount', 'calorie', 'moisture', 'protein', 'fat', 'carbohydrate')
        }),
        ('상세 영양소', {
            'fields': ('sugar', 'dietary_fiber', 'calcium', 'iron_content', 'phosphorus', 'potassium', 'salt'),
            'classes': ('collapse',)
        }),
        ('비타민', {
            'fields': ('VitaminA', 'VitaminB', 'VitaminC', 'VitaminD', 'VitaminE'),
            'classes': ('collapse',)
        }),
        ('지방산 및 콜레스테롤', {
            'fields': ('cholesterol', 'saturated_fatty_acids', 'trans_fatty_acids'),
            'classes': ('collapse',)
        }),
        ('가격 정보', {
            'fields': ('lprice', 'discount_price', 'shop_url', 'image_url'),
            'classes': ('collapse',)
        }),
        ('기타 정보', {
            'fields': ('serving_size', 'weight')
        }),
    )