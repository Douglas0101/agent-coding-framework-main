#!/usr/bin/env bash
# run-autocode.sh — Wrapper com pre-flight de paridade para o schema suportado.
#
# Root cause corrigida: configs antigas usavam schema invalido/incompleto para
# OpenCode v1.3.13. Com schema valido (`default_agent`, `agent`, `command`),
# o runtime roteia `/autocode` nativamente para `autocoder` sem `--agent`.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

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
  echo "[ERROR] Missing $DOT_CONFIG — config resolution will diverge"
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

CRITICAL_PATHS = [
    "default_agent",
    "command.autocode.agent",
    "agent.autocoder.maxSteps",
    "agent.general.maxSteps",
]


def get_path(data: dict, path: str):
    current = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return False, None
        current = current[part]
    return True, current


try:
    root_cfg = json.loads(root_path.read_text())
    dot_cfg = json.loads(dot_path.read_text())
except Exception as exc:  # explicit pre-flight failure with context
    print(f"ERROR:invalid_json:{exc}")
    raise SystemExit(1)

for path in CRITICAL_PATHS:
    root_found, root_value = get_path(root_cfg, path)
    dot_found, dot_value = get_path(dot_cfg, path)

    if not root_found or not dot_found:
        print(
            "ERROR:missing_field:"
            f"{path}:"
            f"opencode.json({'present' if root_found else 'missing'}):"
            f".opencode/opencode.json({'present' if dot_found else 'missing'})"
        )
        raise SystemExit(1)

    if root_found != dot_found:
        print(
            "ERROR:missing_field:"
            f"{path}:"
            f"opencode.json({'present' if root_found else 'missing'}):"
            f".opencode/opencode.json({'present' if dot_found else 'missing'})"
        )
        raise SystemExit(1)

    if root_value != dot_value:
        print(
            "ERROR:value_mismatch:"
            f"{path}:"
            f"opencode.json={root_value!r}:"
            f".opencode/opencode.json={dot_value!r}"
        )
        raise SystemExit(1)

print(f"OK:{root_cfg['default_agent']}")
PY
)"; then
    case "$result" in
      ERROR:invalid_json:*)
        echo "[ERROR] Invalid JSON in config: ${result#ERROR:invalid_json:}"
        ;;
      ERROR:missing_field:*)
        IFS=':' read -r _ _ path root_state dot_state <<< "$result"
        echo "[ERROR] Config drift detected: required field '$path' differs in presence ($root_state vs $dot_state)"
        ;;
      ERROR:value_mismatch:*)
        IFS=':' read -r _ _ path root_value dot_value <<< "$result"
        echo "[ERROR] Config drift detected: field '$path' mismatch ($root_value vs $dot_value)"
        ;;
      *)
        echo "[ERROR] Unexpected parity-check failure: $result"
        ;;
    esac
    echo "[ERROR] Run: python -m pytest .internal/tests/test_stable_execution.py -k parity -v"
    exit 1
  fi

  ROOT_AGENT="${result#OK:}"
  if [[ "$ROOT_AGENT" != "autocoder" ]]; then
    echo "[WARNING] default_agent is '$ROOT_AGENT' (expected 'autocoder')"
    echo "[WARNING] This may indicate config drift. Native command routing may differ."
  fi
}

validate_config_parity
echo "[run-autocode] Pre-flight: config parity OK | default_agent=$ROOT_AGENT"

if ! (cd "$PROJECT_ROOT" && opencode debug config >/dev/null 2>&1); then
  echo "[ERROR] OpenCode rejected the project config schema"
  echo "[ERROR] Run: opencode debug config --print-logs"
  exit 1
fi

echo "[run-autocode] Pre-flight: runtime schema validation OK"

exec opencode run \
  --command autocode \
  --dir "$PROJECT_ROOT" \
  "$@"
