---
title: "Runbook: Vector Store"
purpose: "## Trigger Conditions"
audience:
  - "Operators and SREs"
last_updated: "2025-10-16"
---

# Runbook: Vector Store

## Trigger Conditions

- Qdrant pod unhealthy.
- `/memories/search` latency spikes beyond SLO.
- Error messages referencing `vector_store upsert failed`.

## Diagnostic Steps

1. **Check Qdrant health**
   ```bash
   kubectl port-forward svc/qdrant 6333:6333
   curl -s http://localhost:6333/collections
   ```

2. **Inspect API logs for vector errors**
   ```bash
   kubectl logs deploy/somafractalmemory-api --since=5m | grep vector_store
   ```

3. **Verify disk utilisation**
   ```bash
   kubectl exec statefulset/qdrant -- df -h /qdrant/storage
   ```

4. **Run functional probe**
   ```bash
   soma search --query "health check" --top-k 1
   ```

## Recovery Steps

- If Qdrant is offline, restart: `kubectl rollout restart statefulset/qdrant`.
- If corruption detected, restore the latest snapshot and re-run synthetic smoke tests.
- If capacity limits reached, scale the StatefulSet and update volume claims.

## Follow-Up

- Confirm dashboard `SOMA Search Latency` returns below threshold.
- Document cause and remediation in the incident tracking system.
