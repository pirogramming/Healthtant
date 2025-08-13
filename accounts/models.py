from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'), 
        ('OTHER', 'Other')
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
<<<<<<< HEAD
    nickname = models.CharField(max_length=10, unique=True)
    user_gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    user_age = models.IntegerField()
    profile_image_url = models.TextField(null=True, blank=True)

    # 시간 필드
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_profile'
        verbose_name = "사용자 프로필"
        verbose_name_plural = "사용자 프로필들"
=======
    nickname = models.CharField(max_length=30)
    user_gender = models.CharField(
    max_length=10,
    choices=[('M', 'Male'), ('F', 'Female'), ('OTHER', 'Other')],
    null=True,  # DB에 null 허용
    blank=True)
    user_age = models.IntegerField(null=True, blank=True)
    profile_image_url = models.TextField(null=True, blank=True)
>>>>>>> f951233ffdadc0dfc6c3c39d0499cd9473321ba2

    def __str__(self):
        return self.nickname