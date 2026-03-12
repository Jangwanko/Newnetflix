# Security Checklist

## Application & Runtime
- Run as non-root, drop Linux capabilities, enforce seccomp.
- Read-only root filesystem with explicit writable mounts.

## Network
- HTTPS-only ingress with cert-manager.
- Namespace ingress isolation via NetworkPolicy.

## Secrets
- External Secrets + AWS Secrets Manager.
- No secrets committed to Git.
- Redis password enforced in production.

## Supply Chain
- Image scanning on push.
- ECR immutable tags and SHA-based deploys.
