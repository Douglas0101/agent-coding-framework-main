#!/usr/bin/env bash
set -euo pipefail

fail=0

echo "[boundary] Checking disallowed internal directories..."
if disallowed_paths=$(git ls-files | rg -n '(^|/)\.(agent|codex|opencode)(/|$)' || true); then
  if [[ -n "$disallowed_paths" ]]; then
    echo "Found internal artifacts in public repo:"
    echo "$disallowed_paths"
    fail=1
  fi
fi

echo "[boundary] Checking sensitive operational keywords..."
keyword_pattern='OPENAI_API_KEY|ANTHROPIC_API_KEY|AWS_SECRET_ACCESS_KEY|BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|ghp_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}'
# Exclude policy-as-code files that intentionally document detection signatures.
if keyword_hits=$(git grep -nEI "$keyword_pattern" -- . \
  ':(exclude)*.example' \
  ':(exclude)scripts/check-public-boundary.sh' || true); then
  if [[ -n "$keyword_hits" ]]; then
    echo "Found disallowed sensitive keywords in tracked files:"
    echo "$keyword_hits"
    fail=1
  fi
fi

if [[ "$fail" -ne 0 ]]; then
  echo "[boundary] FAILED"
  exit 1
fi

echo "[boundary] OK"
