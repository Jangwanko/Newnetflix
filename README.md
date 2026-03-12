# Newnetflix

Newnetflix는 영상 업로드/시청/댓글/좋아요를 제공하는 Django 서비스입니다.
이 저장소는 로컬 개발용 구성뿐 아니라, AWS 운영 배포를 위한 IaC(Terraform)와 Kubernetes 매니페스트를 포함합니다.

## 운영 목표 아키텍처
- EKS: 애플리케이션(web/worker) 실행
- RDS PostgreSQL: 운영 DB
- S3: 영상 파일 저장소
- ECR: 컨테이너 이미지 저장소
- Secrets Manager + External Secrets: 시크릿 주입
- Prometheus + Grafana: RED 메트릭/대시보드
- Loki + Promtail: 로그 수집
- NGINX Ingress + TLS: HTTPS 제공

아키텍처 다이어그램: `docs/architecture.md`

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
- RDS PostgreSQL (Multi-AZ 옵션)
- ECR Repository (immutable tag)
- S3 media bucket (versioning + SSE)
- Secrets Manager(앱 시크릿)

### 4) kubeconfig 연결
```bash
aws eks update-kubeconfig --region <region> --name <cluster_name>
```

`cluster_name`은 `terraform output cluster_name`으로 확인

### 5) 필수 애드온 설치
- cert-manager (TLS)
- External Secrets Operator

```bash
helm repo add jetstack https://charts.jetstack.io
helm repo update
helm install cert-manager jetstack/cert-manager -n cert-manager --create-namespace --set crds.enabled=true

helm repo add external-secrets https://charts.external-secrets.io
helm repo update
helm install external-secrets external-secrets/external-secrets -n external-secrets --create-namespace
```

### 6) 앱 이미지 빌드/푸시
```bash
aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
docker build -t <account>.dkr.ecr.<region>.amazonaws.com/myflix-prod-app:<git-sha> .
docker push <account>.dkr.ecr.<region>.amazonaws.com/myflix-prod-app:<git-sha>
```

### 7) 프로덕션 매니페스트 배포
`k8s/prod/configmap.yaml`의 아래 값을 먼저 수정
- `DB_HOST` (terraform output의 RDS endpoint)
- `AWS_STORAGE_BUCKET_NAME`
- 도메인 값
- ECR 이미지 경로

`k8s/prod/cluster-issuer.yaml`의 이메일 값 수정

배포:
```bash
kubectl apply -k k8s/prod
```

DB 마이그레이션 (1회):
```bash
kubectl apply -f k8s/prod/migrate-job.yaml
kubectl wait --for=condition=complete job/db-migrate -n myflix --timeout=300s
kubectl delete job db-migrate -n myflix
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
ServiceMonitor 사용을 위해 Prometheus Operator가 필요합니다.

로그 스택 (Loki + Promtail + Grafana):
- `k8s/observability/`

배포:
```bash
kubectl apply -k k8s/observability
```

권장 흐름:
1. 앱이 `/metrics` 노출
2. Prometheus가 scrape
3. Alert rule로 실시간 감지
4. 필요 시 Remote Write로 분석용 저장소에 전송

---

## CI/CD

`main` 브랜치 push 시 GitHub Actions가 아래를 수행합니다.
- 테스트/체크
- Terraform fmt/validate
- Trivy filesystem scan
- ECR 이미지 빌드/푸시
- EKS 배포

필수 GitHub Secret:
- `AWS_ROLE_TO_ASSUME` (OIDC AssumeRole ARN)
- `EKS_CLUSTER_NAME`

워크플로우 파일:
- `.github/workflows/docker.yml`

---

## 운영 문서

- 아키텍처: `docs/architecture.md`
- SLO: `docs/slo.md`
- 장애 시나리오: `docs/failure-scenarios.md`
- Runbook: `docs/runbook.md`
- DR: `docs/dr.md`
- Capacity: `docs/capacity.md`
- Cost: `docs/cost.md`
- Security: `docs/security.md`

---

## 주요 디렉터리

```text
infra/terraform/           AWS IaC (VPC/EKS/RDS/ECR/S3/Secrets)
k8s/prod/                  EKS 운영 매니페스트
k8s/monitoring/            Prometheus 설정
k8s/observability/         Grafana/Loki/Promtail
movies/                    영상 도메인 + worker 처리
myflix/                    Django 설정/metrics/middleware
```
