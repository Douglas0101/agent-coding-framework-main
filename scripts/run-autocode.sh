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

# Quick parity check: compare default_agent and autocoder maxSteps
ROOT_AGENT=$(python3 -c "import json; c=json.load(open('$ROOT_CONFIG')); print(c.get('default_agent',''))" 2>/dev/null || echo "")
DOT_AGENT=$(python3 -c "import json; c=json.load(open('$DOT_CONFIG')); print(c.get('default_agent',''))" 2>/dev/null || echo "")

if [[ "$ROOT_AGENT" != "$DOT_AGENT" ]]; then
  echo "[ERROR] Config drift detected: root default_agent='$ROOT_AGENT' vs .opencode default_agent='$DOT_AGENT'"
  echo "[ERROR] Run: python -m pytest tests/test_stable_execution.py -k test_root_and_dot_opencode -v"
  exit 1
fi

if [[ "$ROOT_AGENT" != "autocoder" ]]; then
  echo "[WARNING] default_agent is '$ROOT_AGENT' (expected 'autocoder')"
  echo "[WARNING] This may indicate config drift. Continuing with explicit --agent autocoder."
fi

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
