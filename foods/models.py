from django.db import models
import uuid

class Food(models.Model):
    food_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    food_img = models.CharField(max_length=255, null=True, blank=True)

    food_name = models.CharField(max_length=255)
    food_category = models.CharField(max_length=255)
    representative_food = models.CharField(max_length=255)

    nutritional_value_standard_amount = models.BigIntegerField()
    calorie = models.BigIntegerField()
    moisture = models.BigIntegerField()
    protein = models.BigIntegerField()
    fat = models.BigIntegerField()
    carbohydrate = models.BigIntegerField()

    sugar = models.BigIntegerField(null=True, blank=True)
    dietary_fiber = models.BigIntegerField(null=True, blank=True)
    calcium = models.BigIntegerField(null=True, blank=True)
    iron_content = models.BigIntegerField(null=True, blank=True)
    phosphorus = models.BigIntegerField(null=True, blank=True)
    potassium = models.BigIntegerField(null=True, blank=True)
    salt = models.BigIntegerField(null=True, blank=True)

    VitaminA = models.BigIntegerField(null=True, blank=True)
    VitaminB = models.BigIntegerField(null=True, blank=True)
    VitaminC = models.BigIntegerField(null=True, blank=True)
    VitaminD = models.BigIntegerField(null=True, blank=True)
    VitaminE = models.BigIntegerField(null=True, blank=True)

    cholesterol = models.BigIntegerField(null=True, blank=True)
    saturated_fatty_acids = models.BigIntegerField(null=True, blank=True)
    trans_fatty_acids = models.BigIntegerField(null=True, blank=True)

    serving_size = models.BigIntegerField(null=True, blank=True)
    weight = models.BigIntegerField()
    company_name = models.CharField(max_length=255)

    def __str__(self):
        return self.food_name