from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    nickname = models.CharField(max_length=10)
    user_gender = models.CharField(max_length=10, choices=[('M', 'Male'), ('F', 'Female'), ('OTHER', 'Other')])
    user_age = models.IntegerField()
    profile_image_url = models.TextField()

    def __str__(self):
        return self.nickname