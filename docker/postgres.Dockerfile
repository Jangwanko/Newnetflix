FROM postgres:15

RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-contrib \
    && rm -rf /var/lib/apt/lists/*

COPY docker/postgres/init/01-extensions.sql /docker-entrypoint-initdb.d/01-extensions.sql
