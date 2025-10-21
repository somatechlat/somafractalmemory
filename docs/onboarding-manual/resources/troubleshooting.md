---
title: "Troubleshooting"
purpose: "| Symptom | Root Cause | Fix | |---------|------------|-----| | `401 Missing bearer token` | Header missing or token blank."
audience:
  - "New Team Members"
last_updated: "2025-10-16"
---

# Troubleshooting

| Symptom | Root Cause | Fix |
|---------|------------|-----|
| `401 Missing bearer token` | Header missing or token blank. | Ensure `Authorization: Bearer <token>` is present; confirm `SOMA_API_TOKEN` value. |
| `403 Invalid token` | Wrong token. | Rotate token via secret manager and redeploy. |
| `429 Rate limit exceeded` | Global limiter triggered. | Increase `SOMA_RATE_LIMIT_MAX` or reduce client concurrency. |

> **CAUTION (DEVELOPMENT ONLY)**: Only increase or disable `SOMA_RATE_LIMIT_MAX` in development or QA environments for controlled load testing. Never change this setting in production without following your organization's change control and monitoring the system closely during the test.
| `500 Vector store upsert failed` | Qdrant unavailable. | Run the [Vector Store runbook](../../technical-manual/runbooks/vector-store.md). |
| CLI fails with `Memory not found` | Coordinate incorrect. | Retrieve the coordinate from the store response and retry. |
