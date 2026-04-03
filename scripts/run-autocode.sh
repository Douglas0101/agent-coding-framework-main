#!/usr/bin/env bash
# run-autocode.sh — Wrapper para contornar bug de routing do OpenCode v1.3.13
#
# Problema: /autocode (agent: autocoder) roteia para general com maxSteps=50
# Workaround: --agent autocoder força o roteamento correto com maxSteps=6
#
# Tracking: .opencode/skills/self-bootstrap-opencode/debug_autocode.log
# Issue: AGENTS.md → Known Issues → Routing Bug: /autocode command
# SDD: capability.stable-execution@1.0.0

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ============================================================
# Pre-flight: validate config parity
# ============================================================
# Before executing, verify that root and .opencode configs are in sync.
# A drift here indicates a potential routing problem.

ROOT_CONFIG="$PROJECT_ROOT/opencode.json"
DOT_CONFIG="$PROJECT_ROOT/.opencode/opencode.json"

if [[ ! -f "$ROOT_CONFIG" ]]; then
  echo "[ERROR] Missing $ROOT_CONFIG — config drift risk"
  exit 1
fi

if [[ ! -f "$DOT_CONFIG" ]]; then
  echo "[ERROR] Missing $DOT_CONFIG — causes silent routing failure"
  exit 1
fi

validate_config_parity() {
  local result
  if ! result="$(python3 - "$ROOT_CONFIG" "$DOT_CONFIG" <<'PY'
import json
import sys
from pathlib import Path

root_path = Path(sys.argv[1])
dot_path = Path(sys.argv[2])

try:
    root_cfg = json.loads(root_path.read_text())
    dot_cfg = json.loads(dot_path.read_text())
except Exception as exc:  # explicit pre-flight failure with context
    print(f"ERROR:invalid_json:{exc}")
    raise SystemExit(1)

root_agent = str(root_cfg.get("default_agent", ""))
dot_agent = str(dot_cfg.get("default_agent", ""))

if root_agent != dot_agent:
    print(f"ERROR:default_agent_mismatch:{root_agent}:{dot_agent}")
    raise SystemExit(1)

# Keep shell output parsing stable and machine-friendly.
print(f"OK:{root_agent}")
PY
)"; then
    case "$result" in
      ERROR:invalid_json:*)
        echo "[ERROR] Invalid JSON in config: ${result#ERROR:invalid_json:}"
        ;;
      ERROR:default_agent_mismatch:*)
        IFS=':' read -r _ _ root_agent dot_agent <<< "$result"
        echo "[ERROR] Config drift detected: root default_agent='$root_agent' vs .opencode default_agent='$dot_agent'"
        ;;
      *)
        echo "[ERROR] Unexpected parity-check failure: $result"
        ;;
    esac
    echo "[ERROR] Run: python -m pytest tests/test_stable_execution.py -k test_root_and_dot_opencode -v"
    exit 1
  fi

  ROOT_AGENT="${result#OK:}"
  if [[ "$ROOT_AGENT" != "autocoder" ]]; then
    echo "[WARNING] default_agent is '$ROOT_AGENT' (expected 'autocoder')"
    echo "[WARNING] This may indicate config drift. Continuing with explicit --agent autocoder."
  fi
}

validate_config_parity
echo "[run-autocode] Pre-flight: config parity OK | default_agent=$ROOT_AGENT"

# ============================================================
# Execute with confirmed workaround
# ============================================================
# --agent autocoder is REQUIRED due to upstream routing bug in OpenCode v1.3.13
# The command frontmatter specifies agent: autocoder, but runtime ignores it
# without the explicit flag.

exec opencode run \
  --agent autocoder \
  --command autocode \
  --dir "$PROJECT_ROOT" \
  "$@"
