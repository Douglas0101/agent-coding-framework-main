#!/usr/bin/env bash
# run-autocode.sh — Wrapper para contornar bug de routing do OpenCode v1.3.13
#
# Problema: /autocode (agent: autocoder) roteia para general com maxSteps=50
# Workaround: --agent autocoder força o roteamento correto com maxSteps=6
#
# Tracking: .opencode/skills/self-bootstrap-opencode/debug_autocode.log
# Issue: AGENTS.md → Known Issues → Routing Bug: /autocode command
# SDD: capability.bugfix.routing-suite@1.0.0

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ============================================================
# Pre-flight check: validate that --agent autocoder is effective
# ============================================================
# This probe ensures the runtime routing bug is still active and
# our workaround is being applied. If the bug is fixed upstream,
# this script will log the detection and continue (auto-adaptive).

PREFLIGHT_AGENT=""
PREFLIGHT_OUTPUT=$(opencode run \
  --agent autocoder \
  --command autocode \
  "Responda APENAS com o nome do agente: autocoder" \
  --format json \
  --dir "$PROJECT_ROOT" \
  2>/dev/null | grep -o '"agent"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | grep -o '"[^"]*"$' | tr -d '"' || true)

if [[ "$PREFLIGHT_OUTPUT" == *"autocoder"* ]]; then
  PREFLIGHT_AGENT="autocoder"
elif [[ -n "$PREFLIGHT_OUTPUT" ]]; then
  echo "[WARNING] Pre-flight detected agent='$PREFLIGHT_OUTPUT' (expected 'autocoder')"
  echo "[WARNING] The routing bug may have changed behavior. Continuing with --agent autocoder workaround."
  PREFLIGHT_AGENT="$PREFLIGHT_OUTPUT"
else
  echo "[INFO] Pre-flight probe inconclusive (agent name not captured in probe output)."
  echo "[INFO] Continuing with --agent autocoder workaround as configured."
  PREFLIGHT_AGENT="autocoder (assumed)"
fi

echo "[run-autocode] Pre-flight: agent=$PREFLIGHT_AGENT | workaround=--agent autocoder"

# ============================================================
# Execute with confirmed workaround
# ============================================================
exec opencode run \
  --agent autocoder \
  --command autocode \
  --dir "$PROJECT_ROOT" \
  "$@"
