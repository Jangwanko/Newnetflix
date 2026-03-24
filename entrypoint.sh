#!/bin/sh
set -e

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
APP_ROLE="${APP_ROLE:-web}"
VIDEO_WORKER_POLL_INTERVAL="${VIDEO_WORKER_POLL_INTERVAL:-3}"
GUNICORN_WORKERS="${GUNICORN_WORKERS:-3}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-600}"
GUNICORN_GRACEFUL_TIMEOUT="${GUNICORN_GRACEFUL_TIMEOUT:-60}"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-true}"
RUN_COLLECTSTATIC="${RUN_COLLECTSTATIC:-true}"
WAIT_FOR_MIGRATIONS="${WAIT_FOR_MIGRATIONS:-false}"
MIGRATION_MAX_ATTEMPTS="${MIGRATION_MAX_ATTEMPTS:-60}"
MIGRATION_RETRY_SECONDS="${MIGRATION_RETRY_SECONDS:-3}"

echo "Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."
until nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 1
done
echo "PostgreSQL is ready."

if [ "$APP_ROLE" = "worker" ]; then
  if [ "$WAIT_FOR_MIGRATIONS" = "true" ]; then
    echo "Waiting for migrations to be applied..."
    until python manage.py migrate --check --noinput >/dev/null 2>&1; do
      sleep 3
    done
    echo "Migrations are ready."
  fi
  echo "Starting video worker..."
  exec python manage.py process_videos --poll-interval "$VIDEO_WORKER_POLL_INTERVAL"
fi

if [ "$RUN_MIGRATIONS" = "true" ]; then
  echo "Running migrations..."
  attempt=1
  until python manage.py migrate --noinput; do
    if [ "$attempt" -ge "$MIGRATION_MAX_ATTEMPTS" ]; then
      echo "Migration failed after $attempt attempts."
      exit 1
    fi
    echo "Migration attempt $attempt failed. Retrying in ${MIGRATION_RETRY_SECONDS}s..."
    attempt=$((attempt + 1))
    sleep "$MIGRATION_RETRY_SECONDS"
  done
fi

if [ "$RUN_COLLECTSTATIC" = "true" ]; then
  echo "Collecting static files..."
  python manage.py collectstatic --noinput
fi

echo "Starting Gunicorn..."
exec gunicorn myflix.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "$GUNICORN_WORKERS" \
  --timeout "$GUNICORN_TIMEOUT" \
  --graceful-timeout "$GUNICORN_GRACEFUL_TIMEOUT"
