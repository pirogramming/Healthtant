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
    salt = models.FloatField(null=True, blank=True)  # 나트륨은 mg 단위이므로 BigInt 유지

    VitaminA = models.FloatField(null=True, blank=True)
    VitaminB = models.FloatField(null=True, blank=True)
    VitaminC = models.FloatField(null=True, blank=True)
    VitaminD = models.FloatField(null=True, blank=True)
    VitaminE = models.FloatField(null=True, blank=True)

    cholesterol = models.FloatField(null=True, blank=True)
    saturated_fatty_acids = models.FloatField(null=True, blank=True)
    trans_fatty_acids = models.FloatField(null=True, blank=True)

    serving_size = models.FloatField(null=True, blank=True)
    weight = models.FloatField()
    company_name = models.CharField(max_length=255)
    
    # 영양 점수 관련 필드
    nutrition_score = models.FloatField(null=True, blank=True)
    nutri_score_grade = models.CharField(max_length=10, null=True, blank=True)
    nrf_index = models.FloatField(null=True, blank=True)
    
    # 가격 정보 (CSV 칼럼에 맞춰 추가)
    lprice = models.BigIntegerField(null=True, blank=True)  # 네이버 쇼핑 최저가
    discount_price = models.BigIntegerField(null=True, blank=True)
    mallName = models.CharField(max_length=100, null=True, blank=True)  # 쇼핑몰 이름
    shop_url = models.URLField(null=True, blank=True)
    image_url = models.URLField(null=True, blank=True)

    class Meta:
        db_table = 'food'
        verbose_name = "식품"
        verbose_name_plural = "식품들"

    def __str__(self):
        return self.food_name
    

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