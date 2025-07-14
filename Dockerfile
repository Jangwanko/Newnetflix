FROM python:3.13-slim

# 작업 디렉토리 지정
WORKDIR /code

# entrypoint 복사 및 권한 부여
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 프로젝트 전체 복사
COPY . /code

# 종속성 설치
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Netcat 설치 (PostgreSQL 연결 확인용)
RUN apt-get update && apt-get install -y netcat-openbsd && apt-get clean

# entrypoint 실행
ENTRYPOINT ["/bin/sh", "/entrypoint.sh"]