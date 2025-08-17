FROM python:3.10-slim AS builder
ENV PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m venv /opt/venv \
  && /opt/venv/bin/pip install --upgrade pip \
  && /opt/venv/bin/pip install -r requirements.txt

FROM python:3.10-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libpq5 libjpeg62-turbo zlib1g \
  && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

COPY . .

RUN mkdir -p /app/staticfiles

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120", "--max-requests", "1000", "--max-requests-jitter", "50"]