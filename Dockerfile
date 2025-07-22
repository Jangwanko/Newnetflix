FROM python:3.11-slim

# 작업 디렉토리 지정
WORKDIR /code

# 프로젝트 전체 복사
COPY . /code

# 종속성 설치
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 환경 변수 설정
ENV DJANGO_ALLOWED_HOSTS=localhost,web
ENV DJANGO_SECRET_KEY=django-insecure-9dx7bk)jn6)7(8j=!5%y*!=1p-yt8%6qv%i0qi^1-lz2zak!6q
ENV DJANGO_DEBUG=False

# Netcat 설치 (PostgreSQL 연결 확인용)
RUN apt-get update \
    && apt-get install -y netcat-openbsd \
    && apt-get clean

# entrypoint 복사 및 권한 부여
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# entrypoint 실행
ENTRYPOINT ["/bin/sh", "/entrypoint.sh"]