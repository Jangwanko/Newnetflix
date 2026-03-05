# SLO (MyFlix)

## 1. 실측 Baseline (2026-03-05, localhost 단일 노드)
- 측정 환경: `docker compose` (db/web/worker/nginx), 포트 `18080`
- 부하 방식: 12개 병렬 잡 x 100 요청 = 총 1200 요청
- 대상 URL: `/`, `/movies/`, `/livez`, `/readyz`, `/movie/999999/`
- 결과:
  - Total: 1200
  - 2xx: 945
  - 4xx: 255 (의도된 404 포함)
  - 5xx: 0
  - p50: 10.02ms
  - p95: 25.03ms
  - p99: 201.45ms
  - 평균: 14.57ms
- 업로드 실측(로그인 후 실제 업로드 1건):
  - `myflix_movie_upload_requests_total{result="success"} = 1`
  - `myflix_movie_upload_duration_seconds_sum = 0.0024`
  - 업로드 파일은 더미 바이트를 사용해 worker 처리에서 실패(코덱/파일 손상) 확인

## 2. 현재 SLO 목표(실측 기반 1차)
- Browse API 가용성(5xx 기준): 99.9% (30일)
- Browse API 지연시간: p95 < 250ms (5분)
- Browse API 지연시간: p99 < 1000ms (5분)
- Upload API 성공률: 99.5% (30일)

## 3. SLI 계산식
- Availability: `1 - (5xx / total_requests)`
- Error Rate: `5xx / total_requests`
- Latency p95: `histogram_quantile(0.95, sum(rate(myflix_http_request_duration_seconds_bucket[5m])) by (le))`
- Upload Success: `sum(rate(myflix_movie_upload_requests_total{result="success"}[5m])) / sum(rate(myflix_movie_upload_requests_total[5m]))`

## 4. Error Budget 정책
- Browse API 월간 에러버짓: 0.1%
- Upload API 월간 에러버짓: 0.5%
- 에러버짓 50% 소진: 신규 기능 배포 속도 제한
- 에러버짓 100% 소진: 안정화 작업 우선

## 5. 재측정 주기
- 주간: RED 지표 리포트 (p95/p99/5xx/트래픽)
- 월간: SLO 목표 재설정 검토
- 릴리즈 전: 장애 시나리오 리허설 결과 반영
