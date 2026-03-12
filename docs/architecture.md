# Architecture (MyFlix)

```mermaid
flowchart LR
  user[User] --> ingress[NGINX Ingress / TLS]
  ingress --> web[Web Pods]
  web --> rds[(RDS PostgreSQL)]
  web --> redis[(Redis Cache)]
  web --> s3[(S3 Media Bucket)]
  worker[Worker Pods] --> rds
  worker --> s3
  web --> metrics[/metrics/]
  metrics --> prom[Prometheus]
  prom --> grafana[Grafana]
  web --> logs[App Logs]
  logs --> promtail[Promtail]
  promtail --> loki[Loki]
```

## Key Points
- Public ingress is HTTPS-only with cert-manager managed certificates.
- App runs on EKS with HPA, PDB, and NetworkPolicy enabled.
- Secrets are delivered via External Secrets + AWS Secrets Manager (IRSA).
- Observability includes RED metrics, dashboards, and log aggregation.
