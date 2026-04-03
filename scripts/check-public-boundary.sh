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
if ! python - <<'PY'
import re
import subprocess
from pathlib import Path

from scripts.security_patterns import PROHIBITED_SECRET_PATTERNS, REPO_ROOT, compile_patterns

tracked_files = subprocess.check_output(["git", "ls-files"], cwd=REPO_ROOT, text=True).splitlines()
patterns = compile_patterns(PROHIBITED_SECRET_PATTERNS)
hits = []

for rel_path in tracked_files:
    if rel_path.endswith(".example"):
        continue
    file_path = REPO_ROOT / rel_path
    if not file_path.is_file():
        continue
    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    for line_no, line in enumerate(content.splitlines(), start=1):
        for pattern in patterns:
            if pattern.search(line):
                hits.append(f"{rel_path}:{line_no}:{line.strip()}")

if hits:
    print("Found disallowed sensitive keywords in tracked files:")
    for hit in hits:
        print(hit)
    raise SystemExit(1)
PY
then
  fail=1
fi

if [[ "$fail" -ne 0 ]]; then
  echo "[boundary] FAILED"
  exit 1
fi

echo "[boundary] OK"
