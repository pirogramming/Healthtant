from django.contrib import admin
from .models import Food, Price


@admin.register(Food)
class FoodAdmin(admin.ModelAdmin):
    list_display = ['food_id', 'food_name', 'company_name', 'food_category', 'nutrition_score', 'nutri_score_grade', 'created_at']
    list_filter = ['food_category', 'nutri_score_grade', 'company_name', 'created_at']
    search_fields = ['food_name', 'company_name', 'representative_food']
    readonly_fields = ['food_id', 'created_at', 'updated_at']
    
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
        ('영양 평가', {
            'fields': ('nutrition_score', 'nutri_score_grade', 'nrf_index')
        }),
        ('기타 정보', {
            'fields': ('serving_size', 'weight', 'created_at', 'updated_at')
        }),
    )


@admin.register(Price)
class PriceAdmin(admin.ModelAdmin):
    list_display = ['price_id', 'food', 'shop_name', 'price', 'discount_price', 'is_available', 'created_at']
    list_filter = ['shop_name', 'is_available', 'created_at']
    search_fields = ['food__food_name', 'shop_name']
    readonly_fields = ['price_id', 'created_at', 'updated_at']