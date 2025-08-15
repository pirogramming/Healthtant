from django.db import models
import uuid

class Food(models.Model):
    food_id = models.CharField(
    primary_key=True,
    max_length=50,
    unique=True,
    default = uuid.uuid4
)
    food_img = models.CharField(max_length=255, null=True, blank=True)

    food_name = models.CharField(max_length=255)
    food_category = models.CharField(max_length=255)
    representative_food = models.CharField(max_length=255)

    # 기준량과 기본 영양소
    nutritional_value_standard_amount = models.BigIntegerField()
    calorie = models.FloatField()
    moisture = models.FloatField()
    protein = models.FloatField()
    fat = models.FloatField()
    carbohydrate = models.FloatField()

    # 선택적 영양소 (Float로 변경)
    sugar = models.FloatField(null=True, blank=True)
    dietary_fiber = models.FloatField(null=True, blank=True)
    calcium = models.FloatField(null=True, blank=True)
    iron_content = models.FloatField(null=True, blank=True)
    phosphorus = models.FloatField(null=True, blank=True)
    potassium = models.FloatField(null=True, blank=True)
    salt = models.BigIntegerField(null=True, blank=True)  # 나트륨은 mg 단위이므로 BigInt 유지

    VitaminA = models.FloatField(null=True, blank=True)
    VitaminB = models.FloatField(null=True, blank=True)
    VitaminC = models.FloatField(null=True, blank=True)
    VitaminD = models.FloatField(null=True, blank=True)
    VitaminE = models.FloatField(null=True, blank=True)

    cholesterol = models.FloatField(null=True, blank=True)
    saturated_fatty_acids = models.FloatField(null=True, blank=True)
    trans_fatty_acids = models.FloatField(null=True, blank=True)
    #magnesium = models.FloatField(null=True, blank=True)

    serving_size = models.FloatField(null=True, blank=True)
    weight = models.FloatField()
    company_name = models.CharField(max_length=255)

    # 영양 점수 관련 필드 추가
    nutrition_score = models.FloatField(null=True, blank=True, help_text="0-26 영양 점수")
    nutri_score_grade = models.CharField(max_length=1, null=True, blank=True, help_text="A-E 등급")
    nrf_index = models.FloatField(null=True, blank=True, help_text="NRF 지수")

    product_image_url = models.URLField(max_length=500, null=True, blank=True, help_text="크롤링된 제품 이미지 URL")
    product_url = models.URLField(max_length=500, null=True, blank=True, help_text="크롤링된 제품 상세 페이지 URL")
    crawled_at = models.DateTimeField(null=True, blank=True, help_text="크롤링 수행 시간")
    crawling_status = models.CharField(
        max_length=20, 
        choices=[
            ('pending', '대기 중'),
            ('in_progress', '크롤링 중'),
            ('success', '성공'),
            ('failed', '실패'),
            ('not_found', '제품 없음')
        ],
        default='pending',
        help_text="크롤링 상태"
    )
    crawling_error = models.TextField(null=True, blank=True, help_text="크롤링 오류 메시지")


    # 시간 필드
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'food'
        verbose_name = "식품"
        verbose_name_plural = "식품들"

    def __str__(self):
        return self.food_name
    

class Price(models.Model):
    price_id = models.CharField(max_length=255, primary_key=True)  # P20240001 형태
    food = models.ForeignKey(Food, on_delete=models.CASCADE, related_name='prices')
    shop_name = models.CharField(max_length=100)
    price = models.BigIntegerField()
    discount_price = models.BigIntegerField(null=True, blank=True)
    is_available = models.BooleanField(default=True)

    crawling_status = models.CharField(
        max_length=20,
        default='pending',
        db_index=True,
        help_text="pending | in_progress | success | failed | not_found"
    )
    crawling_error = models.TextField(null=True, blank=True)
    crawled_at = models.DateTimeField(null=True, blank=True)
    product_url = models.URLField(null=True, blank=True)
    product_image_url = models.URLField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # 시간 필드
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'price'
        verbose_name = "가격 정보"
        verbose_name_plural = "가격 정보들"

    def __str__(self):
        return f"{self.food.food_name} - {self.shop_name}: {self.price}원"
    
from django.contrib.auth import get_user_model

User = get_user_model()  # 현재 User 모델 가져오기

class FavoriteFood(models.Model):
    favorite_id = models.BigAutoField(primary_key=True)  # PK는 BIGINT로 설정
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column='user_id',
        related_name='favorite_foods',
    )
    food = models.ForeignKey(
        'Food',
        on_delete=models.CASCADE,
        db_column='food_id',
        related_name='favorited_by',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'Favorite_Food'
        unique_together = ('user', 'food')
        indexes = [models.Index(fields=['user', 'food'])]

    def __str__(self):
        return f'{getattr(self.user, "username", self.user_id)} ♥ {self.food_id}'