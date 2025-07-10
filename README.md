```text
# 🎬 Newnetflix - 웹 기반 영상 스트리밍 서비스

## 📌 소개
Newnetflix는 Django + Channels + Docker를 기반으로 제작된
**영상 스트리밍 & 업로드 서비스 플랫폼**입니다.
실시간 WebSocket 처리, 영상 클립 관리, 사용자 인증까지 포함된
**Full-stack 백엔드 프로젝트**입니다.

## ⚙️ 주요 기술 스택

| 항목 | 사용 기술 |
|------|-----------|
| 백엔드 | Django 5, DRF, JWT, Channels, moviepy |
| DB | PostgreSQL |
| 인프라 | Docker, Docker Hub, GitHub Actions |
| 배포 | Docker 자동 배포 (main 브랜치 기준) |
| 협업 | Git 브랜치 전략 + 기능 단위 작업

## 🚀 브랜치 전략


┌── main      # 운영 배포용
├── dev       # 개발 통합 테스트
├── users     # 회원 관련 기능
├── posts     # 게시물 CRUD 기능
└── movies    # 영상 처리 기능
모든 기능은 users/posts/movies 브랜치에서 개발 → dev 병합 후 → 테스트 완료 시 main 병합 → GitHub Actions로 Docker 자동 배포

🛠️ 배포 흐름 요약
개발자가 기능 브랜치에서 작업

dev 브랜치에 병합 → 통합 테스트

main 브랜치 병합 → 자동으로 Docker 이미지 생성

Docker Hub에 jangwan/newnetflix:latest 푸시

서버에서 이미지 pull → 배포 완성

📦 Docker 구성
Dockerfile로 이미지 빌드

docker-compose.override.yml로 개발용 마운트 설정

GitHub Secrets에 Docker 로그인 정보 저장

.github/workflows/docker.yml → 자동 배포 YAML 구성


📁 주요 앱 구조
/users      → 회원가입, 로그인, JWT 인증
/posts      → 게시물 작성/조회/수정/삭제
/movies     → 영상 업로드, 클립 분할, 썸네일 생성

🧪 테스트 & 로컬 실행
docker-compose up --build
# 또는 개발 컨테이너에서 코드 수정 시 자동 반영됨

🤝 협업 전략
기능별 브랜치 관리

Pull Request 기반 리뷰

main 브랜치에 병합 후만 배포 진행

README.md와 .env.example 공유

## 🗺️ 2. 개발 흐름도
[개발자1 - users 기능] ↓ [개발자2 - posts 기능] ↓ [개발자3 - movies 기능] ↓
                            ┌────────────────────────────┐
                            │ 통합 기능 테스트 진행        │
                            │ dev 브랜치 통합             │
                            └────────────────────────────┘
                            ↓ main 브랜치 병합 ↓
GitHub Actions 실행 (.yml) ↓ Docker Hub에 이미지 푸시 ↓ 서버에서 pull + run → 배포 완료
```
