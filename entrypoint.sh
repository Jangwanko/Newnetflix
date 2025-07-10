#!/bin/bash

# DB가 준비될 때까지 대기
until nc -z db 5432; do
  echo "Waiting for PostgreSQL..."
  sleep 1
done

# 마이그레이션 및 static 파일 수집
python manage.py migrate
python manage.py collectstatic --noinput

# Gunicorn으로 Django 실행
exec gunicorn myflix.wsgi:application --bind 0.0.0.0:8000