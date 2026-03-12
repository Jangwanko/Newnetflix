# Release Strategy

## Current
- GitHub Actions로 빌드/테스트/배포 자동화
- SHA 기반 이미지 태그 사용

## Target Enhancements
- 배포 전 스모크 테스트 (health/ready 체크)
- 카나리 배포(소량 트래픽 → 전체)
- 실패 시 자동 롤백
- 배포 승인 게이트(환경 보호 룰)

## Basic Rollback
1. 이전 이미지 태그 확인
2. `kustomize edit set image myflix-app=<previous-tag>`
3. `kubectl rollout status deployment/web -n myflix`
