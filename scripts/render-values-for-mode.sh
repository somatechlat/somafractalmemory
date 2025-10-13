#!/usr/bin/env bash
# Render Helm values for a given mode by merging base + mode values when possible.
# Usage: scripts/render-values-for-mode.sh <mode>

set -euo pipefail
MODE=${1:-dev}
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHART_DIR="$REPO_ROOT/infra/helm/soma-infra"
BASE_VALUES="$CHART_DIR/values.yaml"
MODE_VALUES="$CHART_DIR/values-${MODE}.yaml"

if [[ ! -f "$BASE_VALUES" ]]; then
  echo "Base values not found: $BASE_VALUES" >&2
  exit 1
fi

if [[ ! -f "$MODE_VALUES" ]]; then
  echo "Mode values not found for '$MODE' at $MODE_VALUES; emitting base only" >&2
  cat "$BASE_VALUES"
  exit 0
fi

# Prefer yq if available for a three-way merge (yq eval-all 'select(fileIndex == 0) * select(fileIndex == 1)')
if command -v yq >/dev/null 2>&1; then
  yq eval-all 'select(fileIndex == 0) * select(fileIndex == 1)' "$BASE_VALUES" "$MODE_VALUES"
else
  # Fallback: concatenate with a comment; acceptable for simple overrides but not a merge.
  cat <<EOF
# NOTE: yq not found; this output is base values with mode values appended. Install yq for a guaranteed merge.
# base: $BASE_VALUES
# mode: $MODE_VALUES

EOF
  cat "$BASE_VALUES"
  echo -e "\n# --- mode overrides ($MODE) ---\n"
  cat "$MODE_VALUES"
fi
