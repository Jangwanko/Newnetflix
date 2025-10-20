#!/bin/sh

echo "Waiting for PostgreSQL..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 1
done
echo "PostgreSQL started 🐘"

echo "Running migrations..."
python manage.py migrate
python manage.py migrate --noinput
python manage.py collectstatic --noinput
echo "Starting Gunicorn..."
exec gunicorn myflix.wsgi:application --bind 0.0.0.0:8000 --workers 3

echo "Collecting static files..."
python manage.py collectstatic --noinput

exec gunicorn myflix.wsgi:application --bind 0.0.0.0:8000 --workers 3