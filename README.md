# Newnetflix

Newnetflix는 영상 업로드/시청/댓글/좋아요를 제공하는 Django 서비스입니다.
이 저장소는 로컬 개발용 구성뿐 아니라, AWS 운영 배포를 위한 IaC(Terraform)와 Kubernetes 매니페스트를 포함합니다.

## 운영 목표 아키텍처
- EKS: 애플리케이션(web/worker) 실행
- RDS PostgreSQL: 운영 DB
- S3: 영상 파일 저장소
- ECR: 컨테이너 이미지 저장소
- Secrets Manager + External Secrets: 시크릿 주입
- Prometheus: RED 메트릭 수집/알람

---

## 빠른 시작 (로컬)

```bash
cp .env.example .env
docker compose up --build -d
```

접속: http://localhost:18080

기본 검증:
```bash
docker compose exec -T web python manage.py check
docker compose exec -T web python manage.py test movies posts users
```

---

## AWS 운영 배포 (Terraform + EKS)

### 1) 사전 준비
- AWS 계정, IAM 권한(Administrator 수준 또는 동등 권한)
- `terraform >= 1.7`
- `aws cli`, `kubectl`, `helm`

### 2) Terraform 상태 저장소 준비(최초 1회)
- S3 버킷 (terraform state)
- DynamoDB 테이블 (state lock)

`infra/terraform/backend.hcl.example` 값을 실제로 채워 `backend.hcl` 생성

### 3) 인프라 생성
```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
# terraform.tfvars 값 수정
terraform init -backend-config=backend.hcl
terraform plan
terraform apply
```

생성 리소스:
- VPC
- EKS
- RDS PostgreSQL
- ECR Repository
- S3 media bucket
- Secrets Manager(앱 시크릿)

### 4) kubeconfig 연결
```bash
aws eks update-kubeconfig --region <region> --name <cluster_name>
```

`cluster_name`은 `terraform output cluster_name`으로 확인

### 5) 앱 이미지 빌드/푸시
```bash
aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
docker build -t <account>.dkr.ecr.<region>.amazonaws.com/myflix-prod-app:latest .
docker push <account>.dkr.ecr.<region>.amazonaws.com/myflix-prod-app:latest
```

### 6) External Secrets Operator 설치
```bash
helm repo add external-secrets https://charts.external-secrets.io
helm repo update
helm install external-secrets external-secrets/external-secrets -n external-secrets --create-namespace
```

### 7) 프로덕션 매니페스트 배포
`k8s/prod/configmap.yaml`의 아래 값을 먼저 수정
- `DB_HOST` (terraform output의 RDS endpoint)
- `AWS_STORAGE_BUCKET_NAME`
- 도메인 값
- ECR 이미지 경로

배포:
```bash
kubectl apply -f k8s/prod/namespace.yaml
kubectl apply -f k8s/prod/serviceaccount.yaml
kubectl apply -f k8s/prod/secret-store.yaml
kubectl apply -f k8s/prod/external-secret.yaml
kubectl apply -f k8s/prod/configmap.yaml
kubectl apply -f k8s/prod/web.yaml
kubectl apply -f k8s/prod/worker.yaml
kubectl apply -f k8s/prod/hpa-web.yaml
kubectl apply -f k8s/prod/ingress.yaml
```

상태 확인:
```bash
kubectl get pods -n myflix
kubectl get svc -n myflix
kubectl get ingress -n myflix
```

---

## Observability

앱 엔드포인트:
- `/metrics`
- `/livez`
- `/readyz`

RED 지표:
- `myflix_http_requests_total`
- `myflix_http_request_duration_seconds`
- `myflix_movie_upload_requests_total`
- `myflix_movie_upload_duration_seconds`

Prometheus 템플릿:
- `k8s/monitoring/prometheus.yaml`
- `k8s/monitoring/prometheus-rules.yaml`

### 데이터 파이프라인 연동 가이드

- `/metrics`: 파이프라인 입력 소스로 사용
  - 예: Prometheus 수집 -> Remote Write -> 장기 저장소(예: ClickHouse, BigQuery, Managed Prometheus)
- `/livez`, `/readyz`: 파이프라인 데이터보다는 상태 점검/오케스트레이션 용도
  - 예: Ingress/LB 헬스체크, K8s readiness/liveness probe

권장 흐름:
1. 앱이 `/metrics` 노출
2. Prometheus가 scrape
3. Alert rule로 실시간 감지
4. 필요 시 Remote Write로 분석용 저장소에 전송

---

## CI/CD

`main` 브랜치 push 시 GitHub Actions가 ECR로 이미지 푸시합니다.

필수 GitHub Secret:
- `AWS_ROLE_TO_ASSUME` (OIDC AssumeRole ARN)

워크플로우 파일:
- `.github/workflows/docker.yml`

---

## 주요 디렉터리

```text
infra/terraform/           AWS IaC (VPC/EKS/RDS/ECR/S3/Secrets)
k8s/prod/                  EKS 운영 매니페스트
k8s/monitoring/            Prometheus 설정
movies/                    영상 도메인 + worker 처리
myflix/                    Django 설정/metrics/middleware
```
