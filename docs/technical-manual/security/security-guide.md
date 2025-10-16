# Security Guide

## Overview

This guide covers security practices and configurations for Soma Fractal Memory.

## Authentication

### API Authentication

1. **Bearer Token**
```bash
# Set token
export SOMA_API_TOKEN=your_secure_token

# Use in requests
curl -H "Authorization: Bearer $SOMA_API_TOKEN" \
  http://localhost:9595/api/v1/memory
```

2. **Token Management**
```bash
# Generate secure token
openssl rand -base64 32

# Store in file
echo "token_value" > /path/to/token/file

# Use token file
export SOMA_API_TOKEN_FILE=/path/to/token/file
```

## Authorization

### RBAC Configuration

```yaml
# rbac.yaml
roles:
  - name: admin
    permissions:
      - read
      - write
      - delete
  - name: reader
    permissions:
      - read
```

### Role Assignment
```bash
# Assign role
curl -X POST http://localhost:9595/admin/roles \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"user": "user1", "role": "reader"}'
```

## Network Security

### TLS Configuration

```yaml
# config.yaml
tls:
  enabled: true
  cert_file: /path/to/cert.pem
  key_file: /path/to/key.pem
```

### Network Policies

```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-policy
spec:
  podSelector:
    matchLabels:
      app: soma-memory-api
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: frontend
```

## Data Security

### Encryption at Rest

1. **Database Encryption**
```sql
-- Enable encryption
ALTER SYSTEM SET encryption_key = 'key_value';
```

2. **File Encryption**
```python
from cryptography.fernet import Fernet
key = Fernet.generate_key()
```

### Data Classification

| Data Type | Classification | Storage | Encryption |
|-----------|----------------|---------|------------|
| Memory Content | Confidential | Encrypted | Required |
| Metadata | Internal | Standard | Optional |
| Metrics | Public | Standard | No |

## Monitoring & Auditing

### Security Logs

```bash
# Enable audit logging
export SOMA_AUDIT_LOG=true

# View audit logs
docker compose exec api tail -f /var/log/audit.log
```

### Metrics

| Metric | Warning | Critical |
|--------|----------|----------|
| Failed Auth | >10/min | >50/min |
| Invalid Tokens | >5/min | >20/min |
| Unauthorized Access | >1/min | >10/min |

## Compliance

### Data Retention

```yaml
# retention-policy.yaml
policies:
  - type: memory_data
    retain_days: 90
  - type: audit_logs
    retain_days: 365
```

### Access Control Matrix

| Role | Read | Write | Delete | Admin |
|------|------|-------|---------|-------|
| Admin | ✓ | ✓ | ✓ | ✓ |
| Writer | ✓ | ✓ | - | - |
| Reader | ✓ | - | - | - |

## Incident Response

### Security Incidents

1. **Unauthorized Access**
```bash
# 1. Block IP
iptables -A INPUT -s $IP -j DROP

# 2. Revoke tokens
curl -X POST /admin/revoke-all-tokens

# 3. Enable enhanced logging
export SOMA_DEBUG=true
```

2. **Data Breach**
```bash
# 1. Enable read-only mode
curl -X POST /admin/readonly

# 2. Rotate encryption keys
./scripts/rotate-keys.sh

# 3. Audit access logs
grep "unauthorized" /var/log/audit.log
```

## Security Checklist

- [ ] Strong API tokens in use
- [ ] TLS enabled
- [ ] Network policies configured
- [ ] Data encryption enabled
- [ ] Audit logging active
- [ ] Access controls implemented
- [ ] Monitoring alerts configured
- [ ] Incident response plan tested
