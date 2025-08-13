from rest_framework import serializers
from .models import Food, Price

class PriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Price
        fields = ['price_id', 'shop_name', 'price', 'discount_price', 'is_available', 'created_at']

class FoodSerializer(serializers.ModelSerializer):
    prices = PriceSerializer(many=True, read_only=True)
    
    class Meta:
        model = Food
        fields = [
            'food_id', 'food_name', 'food_category', 'representative_food',
            'nutritional_value_standard_amount', 'calorie', 'moisture', 'protein', 
            'fat', 'carbohydrate', 'sugar', 'dietary_fiber', 'calcium', 'iron_content',
            'phosphorus', 'potassium', 'salt', 'VitaminA', 'VitaminB', 'VitaminC',
            'VitaminD', 'VitaminE', 'cholesterol', 'saturated_fatty_acids', 
            'trans_fatty_acids', 'serving_size', 'weight', 'company_name',
            'nutrition_score', 'nutri_score_grade', 'nrf_index', 'prices',
            'created_at', 'updated_at'
        ]

class FoodListSerializer(serializers.ModelSerializer):
    """목록 조회용 간단한 시리얼라이저"""
    class Meta:
        model = Food
        fields = [
            'food_id', 'food_name', 'food_category', 'calorie', 'protein', 
            'fat', 'carbohydrate', 'nutrition_score', 'nutri_score_grade', 
            'nrf_index', 'company_name'
        ]

class FoodSearchSerializer(serializers.Serializer):
    """검색용 시리얼라이저"""
    query = serializers.CharField(max_length=255, required=False)
    category = serializers.CharField(max_length=255, required=False)
    min_calorie = serializers.IntegerField(required=False)
    max_calorie = serializers.IntegerField(required=False)
    min_protein = serializers.FloatField(required=False)
    max_protein = serializers.FloatField(required=False)
    min_fat = serializers.FloatField(required=False)
    max_fat = serializers.FloatField(required=False)
    min_carbohydrate = serializers.FloatField(required=False)
    max_carbohydrate = serializers.FloatField(required=False)
    min_sodium = serializers.FloatField(required=False)
    max_sodium = serializers.FloatField(required=False) 