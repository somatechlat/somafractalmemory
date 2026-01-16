#!/bin/bash
set -e

# SOMA 10-Cycle Resilience Orchestrator
NAMESPACE="sfm"
DEPLOYMENT="sfm-api"
TEST_SCRIPT="tests/verify_sfm_resilience_e2e.py"

echo "=== STARTING 10-CYCLE RESILIENCE TEST FOR SFM ==="

for i in {1..10}
do
    echo "------------------------------------------------"
    echo "CYCLE $i/10: Triggering Rolling Restart..."
    echo "------------------------------------------------"

    kubectl rollout restart deployment/$DEPLOYMENT -n $NAMESPACE

    echo "Waiting for rollout to complete..."
    kubectl rollout status deployment/$DEPLOYMENT -n $NAMESPACE --timeout=120s

    # Wait for the health endpoint to be actually ready (Grace period)
    echo "Waiting for API warm-up (10s)..."
    sleep 10

    echo "Executing E2E Memory Verification..."
    python3 $TEST_SCRIPT

    if [ $? -eq 0 ]; then
        echo "CYCLE $i SUCCESS: Functional Sovereignty Maintained."
    else
        echo "CYCLE $i FAILED: Functional Sovereignty BREACHED."
        exit 1
    fi
done

echo "=== 10-CYCLE RESILIENCE TEST COMPLETE | STATUS: PERFECT ==="
