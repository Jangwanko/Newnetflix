#!/bin/sh
set -e

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
APP_ROLE="${APP_ROLE:-web}"
VIDEO_WORKER_POLL_INTERVAL="${VIDEO_WORKER_POLL_INTERVAL:-3}"
GUNICORN_WORKERS="${GUNICORN_WORKERS:-3}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-600}"
GUNICORN_GRACEFUL_TIMEOUT="${GUNICORN_GRACEFUL_TIMEOUT:-60}"

echo "Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."
until nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 1
done
echo "PostgreSQL is ready."

if [ "$APP_ROLE" = "worker" ]; then
  echo "Starting video worker..."
  exec python manage.py process_videos --poll-interval "$VIDEO_WORKER_POLL_INTERVAL"
fi

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Gunicorn..."
exec gunicorn myflix.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "$GUNICORN_WORKERS" \
  --timeout "$GUNICORN_TIMEOUT" \
  --graceful-timeout "$GUNICORN_GRACEFUL_TIMEOUT"
