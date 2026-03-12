# Performance & Load Test

## Tooling
- k6 for HTTP load
- 목표: p95 < 250ms, 5xx < 0.1%

## Browse Test (k6)
```bash
k6 run scripts/k6-browse.js
```

## Metrics to Capture
- `myflix_http_requests_total`
- `myflix_http_request_duration_seconds_bucket`
- `myflix_http_requests_total{status=~"5.."}`

## 기록 템플릿
- 날짜/시간:
- 환경:
- 동시성/지속시간:
- p50/p95/p99:
- 5xx 비율:
- 특이사항/개선안:
