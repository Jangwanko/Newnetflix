# Newnetflix

`kind` 기반 로컬 Kubernetes 환경에서 Django 서비스를 운영하고, PostgreSQL HA(`repmgr + pgpool`) failover를 반복 검증하는 프로젝트입니다.

## 현재 구성
- App: `web`, `worker`, `nginx`
- DB HA: `postgres-ha-0`, `postgres-ha-1`, `postgres-ha-2` (P1 + S2)
- DB Proxy: `postgres-proxy` (`Service: postgres`)
- Monitoring: Prometheus + Grafana + postgres-exporter
- Fencing: `postgres-fencer` (split-brain 자동 감지/격리)

## 실행 방법

### 1) Docker Compose
```bash
cp .env.example .env
docker compose up --build -d
```

### 2) Local Kubernetes (kind)
```bash
kind create cluster --name newnetflix-local
docker build --platform linux/amd64 --provenance=false -f docker/backend.Dockerfile -t newnetflix:local .
kind load docker-image newnetflix:local --name newnetflix-local
kubectl apply -k k8s/local-ha
kubectl apply -k k8s/monitoring
kubectl apply -k k8s/observability
```

## HA Drill 자동 검증
```bash
python scripts/ha_drill.py --iterations 10
```

빠른 로컬 확인:
```bash
python scripts/ha_drill.py --fast --iterations 3 --scenarios standby_recovery --poll-interval-seconds 5
```

## 측정 산출물
- 1차: `docs/ha-drill-runs-1st.csv`, `docs/ha-drill-summary-1st.json`
- 2차: `docs/ha-drill-runs-2nd.csv`, `docs/ha-drill-summary-2nd.json`
- 3차: `docs/ha-drill-runs-3rd.csv`, `docs/ha-drill-summary-3rd.json`
- 4차: `docs/ha-drill-runs-4th.csv`, `docs/ha-drill-summary-4th.json`

## 성공 기준 (Acceptance)
- 시나리오별 10회 실행
- `RTO`, `재조인`, `pgpool 복구`의 `max/avg/p95` 기록
- 매 회차 `primary 개수 == 1` 강제 체크(split-brain 즉시 실패)
- failover 전후 데이터 무결성(marker row) 검증
- `/readyz` 5xx/지연 기록
- DB 다운 알람 발생/해제 여부 기록

## 측정 결과

### 1차 측정
- primary_failover: `60%` (6/10), split-brain `2회`
- standby_recovery: `0%` (0/10)

### 2차 측정 (2026-03-25)
- primary_failover: `40%` (4/10), split-brain `3회`
- standby_recovery: `0%` (0/10)

### 3차 측정 (2026-03-25, 감지/펜싱 적용 후)
- primary_failover: `90%` (9/10), split-brain `0회`
- standby_recovery: `0%` (0/10)

### 4차 측정 (2026-03-25, 재생성 기반 판정 적용 후)

#### primary_failover (10회)
- 성공률: `50%` (5/10)
- RTO: `max 33.12s / avg 23.13s / p95 33.12s`
- old primary 재조인: `max 36.09s / avg 18.37s / p95 36.09s`
- pgpool 복구: `max 64.36s / avg 47.07s / p95 64.36s`
- split-brain: `2회`
- 무결성 실패: `0회`
- `/readyz` 5xx 합계: `5`

#### standby_recovery (10회)
- 성공률: `100%` (10/10)
- 재조인: `max 0.91s / avg 0.85s / p95 0.91s`
- pgpool 복구: `max 0.31s / avg 0.28s / p95 0.31s`
- split-brain: `0회`
- 무결성 실패: `0회`
- `/readyz` 5xx 합계: `0`

## 4차 실험 분석및 가설

### 분석
- standby_recovery는 “DB 개수(3) + 재생성 확인 + 역할(P1+S2)” 기준으로 전환하면서 안정적으로 통과
- primary_failover는 여전히 `postcheck criteria not met`가 반복되어 성공률이 50%에 머무름
- split-brain은 줄었지만 완전히 제거되지 않음(`2회`)

### 가설
- 가설 1: primary 시나리오의 postcheck가 실제 장애 특성 대비 과도하게 엄격해 실패를 유발한다
- 가설 2: pgpool 복구 지연과 alert 해제 지연이 primary_failover 성공률 하락의 핵심 요인이다
- 가설 3: fencer는 split-brain 억제에는 효과가 있으나, primary 승격 직후 수렴 안정화에는 추가 튜닝이 필요하다

### 다음 개선
- primary_failover 전용 postcheck 조건 분리(핵심 SLO와 부가 지표 분리)
- pgpool 상태 동기화/복구 시간 단축
- fencer hold-down 및 leader 고정 전략 보강
