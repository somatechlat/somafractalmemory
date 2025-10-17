---
title: "Runbook: API Service"
purpose: "Standard operating procedure when the HTTP API degrades or fails."
audience:
  - "Operators and SREs"
last_updated: "2025-10-17"
---

# Runbook: API Service

## When to use this runbook

- Alert `SOMAApiHighErrorRate` fires.
- `/health` or `/readyz` returns non-200.
- Clients report failures from `/memories` routes.

## Immediate Actions

1. **Confirm the alert**
   ```bash
   curl -s http://somafractalmemory.internal/readyz
   curl -s -H "Authorization: Bearer $SOMA_API_TOKEN" http://somafractalmemory.internal/stats
   ```

2. **Check logs**
   ```bash
   kubectl logs deploy/somafractalmemory-api --since=10m | jq -r '.message'
   ```

3. **Validate dependencies**
   ```bash
   nc -zv postgres.svc 40021
   nc -zv redis.svc 40022
   nc -zv qdrant.svc 40023
   ```

4. **Run synthetic request**
   ```bash
   curl -s -X POST http://somafractalmemory.internal/memories \
     -H "Authorization: Bearer $SOMA_API_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"coord":"1,1","payload":{"probe":true}}'
   ```

5. **Roll the deployment**
   ```bash
   kubectl rollout restart deploy/somafractalmemory-api
   kubectl rollout status deploy/somafractalmemory-api
   ```

## Post-incident

- Delete the synthetic probe memory: `curl -X DELETE http://.../memories/1,1`.
- File an incident report capturing timeline, root cause, and remediation.
- Review dashboards to ensure errors/latency returned to baseline.
