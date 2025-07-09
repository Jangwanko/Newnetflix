# Django 앱을 위한 Dockerfile
FROM python:3.13-slim

# 환경 설정
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 작업 디렉터리 설정
WORKDIR /app

# 패키지 설치
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# 프로젝트 코드 복사
COPY entrypoint.sh .

# 엔트리포인트 설정
RUN chmod +x entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]