#!/bin/sh

echo "Waiting for PostgreSQL..."

while ! nc -z db 5432; do
  sleep 1
done

echo "PostgreSQL started 🐘"

exec gunicorn myflix.wsgi:application --bind 0.0.0.0:8000