#!/bin/bash
set -e

echo "🔄 Starting entrypoint script..."

echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

echo "🗄️ Running database migrations..."
python manage.py migrate --noinput

echo "👥 Creating superuser if not exists..."
python manage.py shell <<EOF
from django.contrib.auth.models import User
import os
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser(
        username=os.getenv('DJANGO_SUPERUSER_USERNAME', 'admin'),
        email=os.getenv('DJANGO_SUPERUSER_EMAIL', 'admin@example.com'),
        password=os.getenv('DJANGO_SUPERUSER_PASSWORD', 'admin')
    )
    print("✅ Superuser created")
else:
    print("ℹ️ Superuser already exists")
EOF

echo "🚀 Starting application..."
exec "$@"