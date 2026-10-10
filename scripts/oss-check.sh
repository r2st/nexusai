#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "Running OSS hygiene checks..."

if ! command -v git >/dev/null 2>&1 || ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Warning: git not available; skipping tracked-file scan."
  echo "Tip: run this again in a normal dev environment (or CI) where git works."
  exit 0
fi

PATTERN='(AIzaSy[0-9A-Za-z_-]{20,}|sk-lf-[0-9a-f-]{16,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|xox[baprs]-[A-Za-z0-9-]{20,})'

MATCHES="$(
  git ls-files -z \
    | xargs -0 rg -n -S -I --no-heading --color=never \
        --glob '!**/node_modules/**' \
        --glob '!**/__pycache__/**' \
        --glob '!**/docs/build/**' \
        --glob '!**/frontend/playwright-report/**' \
        --glob '!**/frontend/test-results/**' \
        --glob '!**/backend/tests/**' \
        "$PATTERN" 2>/dev/null || true
)"

if [[ -n "${MATCHES}" ]]; then
  echo ""
  echo "Potential secrets found (review/remove before open-sourcing):"
  echo "${MATCHES}"
  echo ""
  exit 1
fi

echo "OK: no obvious secrets detected in scanned files."
