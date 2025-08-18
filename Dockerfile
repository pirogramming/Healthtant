FROM python:3.10-slim AS builder
ENV PIP_NO_CACHE_DIR=1
WORKDIR /app

# 캐시 최적화를 위해 패키지 설치를 분리
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
  && rm -rf /var/lib/apt/lists/*

# requirements.txt 먼저 복사하여 의존성 캐싱 최적화
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m venv /opt/venv \
  && /opt/venv/bin/pip install --upgrade pip \
  && /opt/venv/bin/pip install -r requirements.txt

FROM python:3.10-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app

# 런타임 의존성만 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libpq5 libjpeg62-turbo zlib1g \
  && rm -rf /var/lib/apt/lists/* \
  && apt-get clean

# venv 복사
COPY --from=builder /opt/venv /opt/venv

# 소스코드 복사 (마지막에 복사하여 캐시 활용)
COPY . .

# 정적파일 및 미디어 디렉토리 생성
RUN mkdir -p /app/staticfiles /app/media

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120", "--max-requests", "1000", "--max-requests-jitter", "50"]