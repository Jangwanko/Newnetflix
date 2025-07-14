FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

RUN apt-get update \
    && apt-get install -y netcat-openbsd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh entrypoint.sh
RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]