#!/bin/bash

echo "📦 PostgreSQL 연결 대기 중..."
while ! nc -z db 5432; do
  sleep 0.5
done

echo "🚀 마이그레이션 실행 중..."
python manage.py migrate

echo "🎬 서버 실행 중..."
exec "$@"