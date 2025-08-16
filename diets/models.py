import uuid
from django.db import models
from django.conf import settings

class Diet(models.Model):
    # 선택할 수 있는 끼니 종류
    MEAL_CHOICES = [
        ('아침', '아침'),
        ('점심', '점심'),
        ('저녁', '저녁'),
    ]

    # UUID로 정의되는 PK
    diet_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    food = models.ForeignKey('foods.Food', on_delete=models.CASCADE)
    date = models.DateField()
    meal = models.CharField(max_length=10, choices=MEAL_CHOICES)

    # 시간 필드
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'diet'
        verbose_name = "식단"
        verbose_name_plural = "식단들"
        # 같은 사용자가 같은 날, 같은 끼니에 같은 음식을 중복 등록하지 않도록
        unique_together = ['user', 'food', 'date', 'meal']

    def __str__(self):
        return f"{self.user} | {self.date} | {self.get_meal_display()}"
