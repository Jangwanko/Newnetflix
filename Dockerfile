FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ✅ netcat 설치 추가
RUN apt-get update && apt-get install -y netcat-openbsd

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh
COPY . .

ENTRYPOINT ["./entrypoint.sh"]