# Runbook (MyFlix)

## Alert: MyflixHigh5xxRate
1. Check recent deployments and roll back if error spike coincides.
2. Inspect web pod logs:
   - `kubectl logs -n myflix deploy/web --tail=200`
3. Check DB health and connections:
   - `kubectl exec -n myflix deploy/web -- python manage.py check --database default`
4. If DB is saturated, scale web/worker down to reduce pressure.

## Alert: MyflixHighLatencyP95/P99
1. Check HPA status and CPU throttling:
   - `kubectl get hpa -n myflix`
   - `kubectl top pods -n myflix`
2. Verify Redis cache health:
   - `kubectl exec -n myflix deploy/redis -- redis-cli -a $REDIS_PASSWORD ping`
3. Look for slow DB queries (RDS Performance Insights).

## Alert: MovieUploadFailures
1. Check worker logs:
   - `kubectl logs -n myflix deploy/worker --tail=200`
2. Verify S3 bucket permissions/IRSA:
   - `kubectl describe sa -n myflix myflix-app`
3. Inspect queue backlog:
   - `kubectl get pods -n myflix -l app=worker`

## Standard Response Template
- Detect time:
- Impact scope:
- Root cause:
- Mitigation:
- Follow-up action:
- Owner:
