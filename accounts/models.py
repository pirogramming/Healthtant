from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    nickname = models.CharField(max_length=30)
    user_gender = models.CharField(
    max_length=10,
    choices=[('M', 'Male'), ('F', 'Female'), ('OTHER', 'Other')],
    null=True,  # DB에 null 허용
    blank=True)
    user_age = models.IntegerField(null=True, blank=True)
    profile_image_url = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.nickname