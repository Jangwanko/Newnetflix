# Cost & Controls

## Major Cost Drivers
- EKS worker nodes
- RDS PostgreSQL (Multi-AZ)
- S3 storage + transfer
- NAT Gateway

## Controls
- Use autoscaling to cap peak nodes.
- S3 lifecycle to transition old media to IA/Glacier.
- Right-size RDS instance by CPU/memory metrics.
- Alert on monthly budget thresholds (AWS Budgets).
