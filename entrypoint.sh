#!/bin/bash

# DB가 실행될 때까지 대기
until nc -z db 5432; do
  echo "Waiting for PostgreSQL..."
  sleep 1
done

# 마이그레이션 및 collectstatic
python manage.py migrate
python manage.py collectstatic --noinput

# gunicorn 실행
exec gunicorn myflix.wsgi:application --bind 0.0.0.0:8000