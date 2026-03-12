# Capacity & Scaling

## Assumptions
- Average browse request: 15ms p50 (local baseline)
- Upload throughput: CPU-bound on worker
- Target p95 latency: < 250ms

## Current Scaling
- Web: HPA target 70% CPU (min 3, max 10)
- Worker: HPA target 75% CPU (min 2, max 6)

## Growth Plan
1. Increase node group size when sustained CPU > 60% for 30m.
2. Scale worker independently to protect browse latency.
3. Introduce read replica for RDS if read QPS increases.
