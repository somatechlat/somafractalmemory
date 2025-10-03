# Port Forwarding Setup - Improvements Made (October 2025)

## Summary
This document summarizes the improvements made to the port forwarding setup and troubleshooting documentation for the SomaFractalMemory project.

## Issues Encountered & Solutions

### 1. **Conflicting Port Forwards (9696 vs 9595)**
**Issue**: There was a conflicting kubectl port-forward process running on port 9696 for a different service (somabrain) that was interfering with the 9595 setup.

**Solution**:
- Added explicit cleanup commands to kill conflicting port forwards
- Updated documentation to mention checking for conflicts on other ports
- Ensured all scripts and docs consistently use port 9595 only

### 2. **Auto-Server Script Namespace Issue**
**Issue**: The `scripts/auto-server.sh` script was not specifying the correct namespace (`soma-memory`) in kubectl commands.

**Solution**: Updated the script to include `-n soma-memory` in all kubectl commands:
```bash
# Before
kubectl wait --for=condition=ready pod -l app.kubernetes.io/component=api,app.kubernetes.io/instance=soma-memory --timeout=60s

# After
kubectl wait --for=condition=ready pod -l app.kubernetes.io/component=api,app.kubernetes.io/instance=soma-memory -n soma-memory --timeout=60s
```

### 3. **LaunchD Service Configuration**
**Issue**: The macOS launchd service had incorrect argument formatting that caused repeated failures.

**Solution**: Fixed the plist file to properly separate the script path and arguments:
```xml
<!-- Before (incorrect) -->
<string>/bin/bash</string>
<string>-lc</string>
<string>"/path/to/script start"</string>

<!-- After (correct) -->
<string>/path/to/script</string>
<string>start</string>
```

### 4. **Stale Pod Handling During Restarts**
**Issue**: After `kubectl rollout restart`, old pods sometimes remained running alongside new ones, causing port forwarding to target the wrong pod.

**Solution**: Added explicit pod cleanup steps:
```bash
# Delete old pods to force clean restart
kubectl delete pod <old-pod-name> -n soma-memory

# Wait for new pod to be ready
kubectl wait --for=condition=ready pod -l app.kubernetes.io/component=api -n soma-memory --timeout=60s
```

## Documentation Improvements

### Enhanced Troubleshooting Section
Added comprehensive troubleshooting section to `docs/DEVELOPER_ENVIRONMENT.md` including:

1. **Port forward conflict resolution**
2. **Kubernetes connection timeout handling**
3. **LaunchD service debugging**
4. **Recovery workflow for complete restart**

### New Debugging Table Entries
| Symptom | Solution Added |
|---------|---------------|
| Port forward keeps dying/disconnecting | Clean up conflicts, delete stale pods |
| TLS handshake timeout with kubectl | Check cluster connection, restart Docker/Kind |
| LaunchD service fails to start | Check logs, fix plist formatting, verify permissions |

### Recovery Workflow
Added step-by-step recovery procedure for complete environment reset:
```bash
# 1. Clean slate
pkill -f "kubectl port-forward"
./scripts/port_forward_api.sh stop

# 2. Restart services
./scripts/start_stack.sh development
kubectl rollout restart deployment -n soma-memory

# 3. Wait for readiness
kubectl wait --for=condition=ready pod -l app.kubernetes.io/component=api -n soma-memory --timeout=120s

# 4. Start port forward
./scripts/port_forward_api.sh start

# 5. Verify
curl -s http://localhost:9595/healthz | jq .
```

## Files Modified

1. **`docs/DEVELOPER_ENVIRONMENT.md`** - Enhanced debugging section with new troubleshooting scenarios
2. **`scripts/auto-server.sh`** - Fixed namespace specification in kubectl commands
3. **`~/Library/LaunchAgents/com.somafractalmemory.portforward.plist`** - Fixed launchd service configuration

## Verification

✅ Port 9595 is working correctly and stable
✅ No conflicting port forwards on other ports
✅ Documentation covers all encountered edge cases
✅ Recovery procedures tested and documented
✅ All Kubernetes pods healthy and running

## Best Practices Reinforced

1. **Always use the production script**: `./scripts/port_forward_api.sh start` instead of manual kubectl commands
2. **Clean up conflicts**: Use `pkill -f "kubectl port-forward"` before starting new forwards
3. **Specify namespaces**: Always include `-n soma-memory` in kubectl commands
4. **Verify health**: Always test with `curl -s http://localhost:9595/healthz` after setup

The port forwarding setup is now robust, well-documented, and handles edge cases that were previously undocumented.
