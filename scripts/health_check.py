#!/usr/bin/env python3
"""
빠른 헬스체크를 위한 스크립트
"""
import os
import sys
import django
from pathlib import Path

# Django 설정
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

def health_check():
    """간단한 헬스체크 수행"""
    try:
        # 1. Database 연결 확인
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        print("✅ Database: OK")
        
        # 2. Django 설정 확인
        from django.conf import settings
        print(f"✅ Django: OK (DEBUG={settings.DEBUG})")
        
        # 3. 필수 환경변수 확인
        required_env = ['POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD']
        for env_var in required_env:
            if not os.getenv(env_var):
                print(f"⚠️  Missing env var: {env_var}")
        
        return True
        
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

if __name__ == "__main__":
    success = health_check()
    sys.exit(0 if success else 1)