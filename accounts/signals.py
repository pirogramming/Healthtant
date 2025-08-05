from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:  # 새 User가 생성된 경우
        UserProfile.objects.create(
            user=instance,
            nickname=instance.username or "새 유저",
            user_gender="M",  # 기본값 (원하면 "F" 또는 None도 가능)
            user_age=20,      # 기본값
            profile_image_url="default.png"
        )