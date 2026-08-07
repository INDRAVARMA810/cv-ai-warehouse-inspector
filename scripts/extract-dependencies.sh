#!/usr/bin/env bash
# =====================================================================
# Extract the backend's real inter-module import graph.
#
# The dependency diagram in docs/architecture/06-folder-dependencies.md
# is generated from this, so it reflects the imports that actually
# exist rather than the ones the architecture intends. Re-run it after
# any refactor and update the diagram if the output changes.
#
#   ./scripts/extract-dependencies.sh              # edge list
#   ./scripts/extract-dependencies.sh --mermaid    # mermaid fragment
# =====================================================================
set -euo pipefail

cd "$(dirname "$0")/../backend"

edges() {
    for file in $(find app -name "*.py" -not -path "*__pycache__*" | sort); do
        module=$(echo "$file" | sed 's|app/||; s|/[^/]*\.py$||; s|\.py$||')
        grep -oE "^from app\.[a-z_]+" "$file" 2>/dev/null \
            | sed "s|^from app\.|${module} -> |" || true
    done

    # The composition root sits at the backend root, not under app/.
    grep -oE "^from app\.[a-z_]+" run_detection.py 2>/dev/null \
        | sed 's|^from app\.|run_detection -> |' || true
}

# Self-edges are package __init__ re-exports, not real dependencies.
result=$(edges | sort -u | awk '$1 != $3')

if [[ "${1:-}" == "--mermaid" ]]; then
    echo "flowchart BT"
    echo "$result" | while read -r from _ to; do
        echo "    ${from//\//_} --> ${to//\//_}"
    done
else
    echo "$result"
fi
