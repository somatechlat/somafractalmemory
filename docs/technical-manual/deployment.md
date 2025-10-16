# Deployment Guide

## Overview

This guide covers deploying Soma Fractal Memory in production environments.

## Prerequisites

- Kubernetes cluster
- Helm 3.x
- kubectl configured

## Deployment Options

### 1. Kubernetes with Helm (Recommended)

```bash
# Add Helm repository
helm repo add soma https://charts.somatech.lat
helm repo update

# Install with default values
helm install memory soma/somafractalmemory

# Install with custom values
helm install memory soma/somafractalmemory -f values-prod.yaml
```

### 2. Docker Compose (Small Scale)

```bash
# Production mode
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|----------|
| `SOMA_API_TOKEN` | API authentication token | Required |
| `POSTGRES_PASSWORD` | Database password | Required |
| `REDIS_PASSWORD` | Redis password | Required |

### Resource Requirements

| Component | CPU | Memory | Storage |
|-----------|-----|---------|----------|
| API | 1-2 cores | 2-4GB | - |
| PostgreSQL | 2-4 cores | 4-8GB | 100GB |
| Redis | 1-2 cores | 2-4GB | 20GB |
| Qdrant | 2-4 cores | 4-8GB | 50GB |

## Monitoring Setup

```bash
# Install monitoring stack
helm install prometheus prometheus-community/kube-prometheus-stack

# Configure Grafana
kubectl apply -f monitoring/
```

## Security Considerations

1. Set strong passwords
2. Enable TLS
3. Configure network policies
4. Set up RBAC

## Scaling Guidelines

### Horizontal Scaling

```bash
# Scale API pods
kubectl scale deployment memory-api --replicas=3

# Scale Redis cluster
helm upgrade memory soma/somafractalmemory --set redis.replicas=3
```

## Verification

```bash
# Check pod status
kubectl get pods

# Test API health
curl https://api.example.com/healthz

# View logs
kubectl logs -l app=memory-api
```

## Rollback Procedure

```bash
# List Helm revisions
helm history memory

# Rollback to previous version
helm rollback memory 1
```
