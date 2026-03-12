# Disaster Recovery (MyFlix)

## RPO/RTO Targets
- RPO: 15 minutes (RDS automated backups + binlog)
- RTO: 1 hour (restore + app redeploy)

## RDS Restore Procedure
1. Restore a new DB instance from latest snapshot.
2. Update `DB_HOST` in `k8s/prod/configmap.yaml` (or Secrets Manager) to new endpoint.
3. Restart web/worker deployments.

현재 RDS 백업 보존 기간은 7일입니다.

## S3 Recovery
- S3 versioning enabled.
- Use object version restore for accidental deletes.

## EKS Rebuild
1. Run `terraform apply` for infra recreation.
2. Reinstall cert-manager and external-secrets.
3. Re-deploy `k8s/prod` manifests via CI/CD.

## DR Drill
- Quarterly restore test with documented MTTD/MTTR.
- Capture lessons learned and update runbook.
