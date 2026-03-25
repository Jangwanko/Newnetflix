# Newnetflix

`kind` 기반 로컬 Kubernetes에서 Django 서비스를 운영하고, PostgreSQL HA(`repmgr + pgpool`) failover를 반복 검증하는 프로젝트입니다.

## 현재 구성
- App: `web`, `worker`, `nginx`
- DB HA: `postgres-ha-0`, `postgres-ha-1`, `postgres-ha-2` (P1 + S2)
- DB Proxy: `postgres-proxy` (`Service: postgres`)
- Monitoring: Prometheus + Grafana + `postgres-exporter`
- Fencing: `postgres-fencer` (split-brain 자동 감지/격리)

## 실행 방법

### 1) Docker Compose
```bash
cp .env.example .env
docker compose up --build -d
```

### 2) Local Kubernetes (kind)
```bash
./tools/kind.exe create cluster --name newnetflix-local
docker build --platform linux/amd64 --provenance=false -f docker/backend.Dockerfile -t newnetflix:local .
./tools/kind.exe load docker-image newnetflix:local --name newnetflix-local
kubectl apply -k k8s/local-ha
kubectl apply -k k8s/monitoring
kubectl apply -k k8s/observability
```

## HA Drill 자동 검증
```bash
python scripts/ha_drill.py --iterations 10
```

빠른 확인:
```bash
python scripts/ha_drill.py --fast --iterations 3 --scenarios standby_recovery --poll-interval-seconds 5
```

## 측정 산출물
- 1차: `docs/ha-drill-runs-1st.csv`, `docs/ha-drill-summary-1st.json`
- 2차: `docs/ha-drill-runs-2nd.csv`, `docs/ha-drill-summary-2nd.json`
- 3차: `docs/ha-drill-runs-3rd.csv`, `docs/ha-drill-summary-3rd.json`
- 4차: `docs/ha-drill-runs-4th.csv`, `docs/ha-drill-summary-4th.json`
- 5차: `docs/ha-drill-runs-5th.csv`, `docs/ha-drill-summary-5th.json`
- 6차: `docs/ha-drill-runs-6th.csv`, `docs/ha-drill-summary-6th.json`
- 7차: `docs/ha-drill-runs-7th.csv`, `docs/ha-drill-summary-7th.json`

## 성공 기준과 용어 정의

### `core_success` (핵심 성공)
아래 핵심 안정성 조건을 만족하면 성공으로 계산합니다.
- split-brain 없음 (`primary == 1`)
- 승격/재조인 완료
- 데이터 무결성 OK
- 역할 수렴(P1+S2) OK
- pgpool 복구 시간 임계 내

### `extended_success` (확장 성공, 인스텐드)
`core_success`를 만족한 상태에서 운영 품질 조건까지 만족한 경우입니다.
- 알람이 정상 발생/해제됨 (`alert_cleared_after = true`)
- `/readyz` 5xx가 0

### 기준
- 기본은 5회 반복(빠른 개선 루프)
- 성공률이 안정적으로 올라가면 10회로 확장
- `RTO`, `재조인`, `pgpool 복구`, `/readyz`, 알람 해제 지연을 함께 기록

## 1~7차 결과 요약

| 회차 | primary 성공률 | standby 성공률 | split-brain(primary) | 비고 |
|---|---:|---:|---:|---|
| 1차 | 60% (6/10) | 0% (0/10) | 2 | 초기 기준 |
| 2차 | 40% (4/10) | 0% (0/10) | 3 | 기준 강화 후 하락 |
| 3차 | 90% (9/10) | 0% (0/10) | 0 | 감지/펜싱 반영 |
| 4차 | 50% (5/10) | 100% (10/10) | 2 | 재생성 판정 반영 |
| 5차 | 20% (1/5) | 80% (4/5) | 1 | 5회 단축 실험 |
| 6차 | core 100% (5/5), ext 0% (0/5) | core/ext 100% (5/5) | 0 | primary의 운영품질 지표 미충족 |
| 7차 | core 80% (8/10), ext 20% (2/10) | core 100% (10/10), ext 90% (9/10) | 2 | primary 구간 변동성 재확인 |

### 1차
- 관찰: primary 60%, standby 0%, split-brain/무결성 이슈 동반.
- 가설: 단순 승격만으로는 안정화가 부족하며, 재조인/역할수렴 검증이 필요.
- 다음 조치: split-brain 판정과 무결성 검증을 강화.

### 2차
- 관찰: primary 40%, standby 0%, split-brain 빈도 증가.
- 가설: 장애 직후 다중 승격 경합이 발생하고 fencing 부재가 치명적.
- 다음 조치: fencing 및 감지 로직 도입.

### 3차
- 관찰: primary 90%, split-brain 0으로 개선, standby는 여전히 0%.
- 가설: primary 승격은 안정화되지만 standby 재생성/재조인 수렴 판정이 불충분.
- 다음 조치: 재생성 Pod 기준(UID/개수/역할) 검증 추가.

### 4차
- 관찰: primary 50%, standby 100%.
- 가설: standby 경로는 안정화되었고, primary 경로는 postcheck/운영품질 지표(알람 해제, readyz, pgpool)가 병목.
- 다음 조치: primary 검증을 단계별로 분해하고 병목 시간을 계측.

### 5차
- 관찰: 5회 단축 실험에서 primary 20%, standby 80%로 변동성 확대.
- 가설: 빠른 반복 실험에서 타이밍 민감도(감지 주기/수렴 대기)가 성공률에 직접 영향.
- 다음 조치: 감지/폴링 주기와 검증 타임아웃 재튜닝.

## 6차 시간표(평균)
어디에서 시간이 오래 걸리는지 알기 위해 타임라인도 추가했고, 수집 항목은 `precheck`, `failure_action`, `recovery_wait`, `verification`, `wall`입니다.

| 시나리오 | precheck | failure_action | recovery_wait | verification | 총 소요(wall) |
|---|---:|---:|---:|---:|---:|
| primary_failover | 3.00s | 25.12s | 60.17s | 82.01s | 170.29s |
| standby_recovery | 3.05s | 120.85s | 1.15s | 4.44s | 129.48s |

### 6차
- 관찰: primary core 100%(5/5)지만 extended 0%(0/5), standby core/ext 100%(5/5).
- 가설: DB 자체 failover는 성공했으나 alert 해제 지연, `/readyz` 5xx, pgpool 복구 지연이 운영품질 실패를 유발.
- 다음 조치: core/extended를 분리 운영하고, fencer/pgpool/alert 해제 구간 집중 튜닝 후 7차 진행.



## 7차 시간표(평균)
6차와 동일하게 `precheck`, `failure_action`, `recovery_wait`, `verification`, `wall`을 분리 계측했습니다.

| 시나리오 | precheck | failure_action | recovery_wait | verification | 총 소요(wall) |
|---|---:|---:|---:|---:|---:|
| primary_failover | 3.02s | 25.59s | 92.26s | 31.73s | 152.59s |
| standby_recovery | 3.73s | 120.78s | 1.23s | 4.46s | 130.20s |

## 7차 결과 분석 및 가설
- primary는 `core_success_rate=0.8`까지 회복됐지만, `extended_success_rate=0.2`로 낮았습니다.
- 주요 실패코드: `FAIL_ALERT_UNCLEARED(7)`, `FAIL_READYZ_5XX(5)`, `FAIL_PGPOOL_RECOVERY_TIMEOUT(2)`, `FAIL_SPLIT_BRAIN(2)`.
- 해석: DB 승격 자체(RTO 평균 23.71s)는 비교적 안정적이지만, alert 해제 지연/pgpool 백엔드 수렴 지연이 사용자 관점 품질을 악화시킵니다.
- 다음 가설: fencer hold-down/쿨다운과 pgpool backend health-check 튜닝을 같이 조정해야 `extended_success`가 개선됩니다.

## 참고
- 실험 세부 로그/근거: `docs/ha-drill-runs-*.csv`, `docs/ha-drill-summary-*.json`
- 장애 대응 문서: `docs/runbook.md`, `docs/dr.md`, `docs/incident-report.md`

