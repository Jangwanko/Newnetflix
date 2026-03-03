# Newnetflix

Django 기반 영상 커뮤니티 프로젝트입니다.
사용자는 회원가입 후 영상을 업로드할 수 있고, 다른 사용자는 영상을 시청하며 좋아요/댓글/알림 기능을 사용할 수 있습니다.

## 주요 기능
- 회원가입 / 로그인 / 로그아웃
- 영상 업로드 / 수정 / 삭제
- 영상 목록 / 상세 / 재생
- 좋아요 / 댓글
- 좋아요/댓글 알림
- 영상 백그라운드 처리(`queued -> processing -> ready/failed`)
- 업로드 진행 상태 표시(하단 고정 상태 바)

## 기술 스택
- Django 5
- PostgreSQL
- Gunicorn + Nginx
- Docker / Docker Compose

---

## 1) 로컬 실행

### 사전 준비
- Docker Desktop
- Docker Compose

### 환경 파일 준비
```bash
cp .env.example .env
```

### 실행
```bash
docker compose up --build -d
```

### 접속
- http://localhost:18080

### 종료
```bash
docker compose down
```

---

## 2) 업로드 동작 방식

- 업로드 시작 시 별도 업로드 탭에서 전송이 진행됩니다.
- 메인 탭에서는 페이지 이동에 제약 없이 계속 탐색할 수 있습니다.
- 진행률은 모든 페이지 하단의 `업로드 상태 바`에서 확인할 수 있습니다.
- 업로드 완료 후 영상은 백그라운드 워커가 처리하며, 처리 상태는 목록/상세에서 확인 가능합니다.

---

## 3) 테스트/점검

```bash
docker compose exec -T web python manage.py check
docker compose exec -T web python manage.py test movies posts users
```

---

## 4) 배포 준비 체크리스트

운영 배포 전 최소한 아래를 맞춰야 합니다.

1. `DJANGO_DEBUG=False`
2. `DJANGO_SECRET_KEY`를 강한 값으로 설정
3. `DJANGO_ALLOWED_HOSTS`를 실제 도메인으로 설정
4. `DJANGO_CSRF_TRUSTED_ORIGINS`를 실제 HTTPS 도메인으로 설정
5. DB 계정/비밀번호 교체
6. 업로드 파일 보관 정책(볼륨 또는 외부 스토리지) 확정

---

## 5) 운영 배포 방법 (Docker Compose)

### 5-1. 서버 준비
- Ubuntu 등 Linux 서버 준비
- Docker / Docker Compose 설치
- 도메인 연결
- 방화벽에서 80/443 허용

### 5-2. 코드 배포
```bash
git clone <your-repo>
cd Newnetflix
cp .env.example .env
# .env 값을 운영 값으로 수정
```

### 5-3. 운영용 실행
```bash
docker compose -f docker-compose.prod.yml up -d
```

### 5-4. 확인
```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f web
```

---

## 6) CI/CD (GitHub Actions)

- `.github/workflows/docker.yml`에서 main push 시 Docker 이미지 빌드/푸시
- 태그: `latest`, `${GITHUB_SHA}`
- 필요한 GitHub Secrets
  - `DOCKER_USERNAME`
  - `DOCKER_PASSWORD`

---

## 7) 주요 환경변수

`.env.example` 참고

- Django
  - `DJANGO_SECRET_KEY`
  - `DJANGO_DEBUG`
  - `DJANGO_ALLOWED_HOSTS`
  - `DJANGO_CSRF_TRUSTED_ORIGINS`
- DB
  - `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- Gunicorn
  - `GUNICORN_WORKERS`
  - `GUNICORN_TIMEOUT`
  - `GUNICORN_GRACEFUL_TIMEOUT`
- Worker
  - `VIDEO_WORKER_POLL_INTERVAL`

---

## 8) 프로젝트 구조

```text
.github/workflows/      CI/CD
movies/                 영상 도메인 + 백그라운드 처리 워커
posts/                  댓글/좋아요/알림
users/                  회원/인증
templates/              UI 템플릿
myflix/                 Django 설정
nginx/                  Nginx 설정
Dockerfile
docker-compose.yml      로컬 실행용
docker-compose.prod.yml 운영 실행용
.env.example
```

---

## 9) 운영 시 권장 추가 작업

- HTTPS(Reverse Proxy + 인증서) 적용
- 외부 오브젝트 스토리지(S3 등)로 media 분리
- 모니터링/알람(Prometheus, Grafana, Sentry 등)
- DB 백업 자동화
- 롤백 절차 문서화
