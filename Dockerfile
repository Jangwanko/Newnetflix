FROM python:3.13-slim

# 루트에 복사
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Netcat 설치
RUN apt-get update \
    && apt-get install -y netcat-openbsd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 실행 스크립트 복사
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x entrypoint.sh

# 프로젝트 소스 전체 복사 (기존 manage.py 등 포함)
COPY . . 

ENTRYPOINT ["./entrypoint.sh"]