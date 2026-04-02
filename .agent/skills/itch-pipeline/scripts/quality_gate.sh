#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# ITCH Pipeline — Quality Gate (fail-fast)
#
# Runs: pytest → ruff → mypy → basedpyright in strict sequence.
# Stops on first failure and reports the failing stage.
#
# Usage:
#   bash .agent/skills/itch-pipeline/scripts/quality_gate.sh
#   bash .agent/skills/itch-pipeline/scripts/quality_gate.sh --json
#   bash .agent/skills/itch-pipeline/scripts/quality_gate.sh --fix
#   bash .agent/skills/itch-pipeline/scripts/quality_gate.sh --fix --json
# ──────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
cd "$PROJECT_ROOT"

JSON_MODE=false
FIX_MODE=false

for arg in "$@"; do
    case "$arg" in
        --json) JSON_MODE=true ;;
        --fix)  FIX_MODE=true ;;
    esac
done

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

RESULTS=()
STAGE_TIMES=()
OVERALL_STATUS=0

run_stage() {
    local name="$1"
    shift
    local cmd="$*"

    if ! $JSON_MODE; then
        echo -e "\n${CYAN}━━━ Stage: ${name} ━━━${NC}"
        echo -e "${YELLOW}$ ${cmd}${NC}\n"
    fi

    local start_time
    start_time=$(date +%s%N)

    local exit_code=0
    local output
    output=$(eval "$cmd" 2>&1) || exit_code=$?

    local end_time
    end_time=$(date +%s%N)
    local elapsed_ms=$(( (end_time - start_time) / 1000000 ))

    STAGE_TIMES+=("${name}:${elapsed_ms}")

    if $JSON_MODE; then
        RESULTS+=("{\"stage\": \"${name}\", \"status\": \"$([ $exit_code -eq 0 ] && echo PASS || echo FAIL)\", \"exit_code\": ${exit_code}, \"elapsed_ms\": ${elapsed_ms}}")
    else
        echo "$output"
        if [ $exit_code -eq 0 ]; then
            echo -e "\n${GREEN}✅ ${name}: PASS${NC} (${elapsed_ms}ms)"
        else
            echo -e "\n${RED}❌ ${name}: FAIL (exit ${exit_code})${NC} (${elapsed_ms}ms)"
        fi
    fi

    if [ $exit_code -ne 0 ]; then
        OVERALL_STATUS=1
        if ! $JSON_MODE; then
            echo -e "\n${RED}🛑 Quality gate FAILED at stage: ${name}${NC}"
        fi
        # Fail fast — don't run remaining stages
        if $JSON_MODE; then
            echo "{\"passed\": false, \"failed_at\": \"${name}\", \"stages\": [$(IFS=,; echo "${RESULTS[*]}")]}"
        fi
        exit 1
    fi
}

skip_stage() {
    local name="$1"
    local reason="$2"

    STAGE_TIMES+=("${name}:0")

    if $JSON_MODE; then
        RESULTS+=("{\"stage\": \"${name}\", \"status\": \"SKIP\", \"reason\": \"${reason}\", \"elapsed_ms\": 0}")
    else
        echo -e "\n${YELLOW}⏭  ${name}: SKIPPED — ${reason}${NC}"
    fi
}

# ── Stage 0: Auto-fix (optional) ─────────────
if $FIX_MODE; then
    if command -v ruff &>/dev/null || python -m ruff --version &>/dev/null 2>&1; then
        if ! $JSON_MODE; then
            echo -e "\n${CYAN}━━━ Auto-fix: ruff ━━━${NC}"
            echo -e "${YELLOW}$ python -m ruff check src/ tests/ scripts/ --fix${NC}\n"
        fi
        python -m ruff check src/ tests/ scripts/ --fix 2>&1 || true
        if ! $JSON_MODE; then
            echo -e "${GREEN}Auto-fix applied${NC}"
        fi
    fi
fi

# ── Stage 1: Tests ────────────────────────────
run_stage "pytest" "python -m pytest tests/ -v --tb=short -q"

# ── Stage 2: Tests with coverage ──────────────
# Try coverage; if pytest-cov is unavailable, skip
if python -c "import pytest_cov" 2>/dev/null; then
    run_stage "coverage" "python -m pytest tests/ -q --cov=src --cov-report=term-missing --cov-fail-under=60 --no-header 2>/dev/null"
else
    skip_stage "coverage" "pytest-cov not installed"
fi

# ── Stage 3: Lint ─────────────────────────────
if command -v ruff &>/dev/null || python -m ruff --version &>/dev/null 2>&1; then
    run_stage "ruff" "python -m ruff check src/ tests/ scripts/ --output-format=concise 2>/dev/null || python -m ruff check src/ tests/ scripts/"
else
    skip_stage "ruff" "ruff not installed (pip install ruff)"
fi

# ── Stage 4: Type Check ──────────────────────
if command -v mypy &>/dev/null || python -m mypy --version &>/dev/null 2>&1; then
    run_stage "mypy" "python -m mypy src/ --ignore-missing-imports --no-error-summary 2>/dev/null || python -m mypy src/ --ignore-missing-imports"
else
    skip_stage "mypy" "mypy not installed (pip install mypy)"
fi

# ── Stage 5: LSP Type Check (Pyright) ─────────
if command -v basedpyright &>/dev/null || python -m basedpyright --version &>/dev/null 2>&1; then
    run_stage "basedpyright" "python -m basedpyright"
else
    skip_stage "basedpyright" "basedpyright not installed (pip install basedpyright)"
fi

# ── Final Report ──────────────────────────────
if $JSON_MODE; then
    echo "{\"passed\": true, \"stages\": [$(IFS=,; echo "${RESULTS[*]}")]}"
else
    echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}🟢 QUALITY GATE PASSED — All stages OK${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # Timing summary
    echo -e "\n${CYAN}  ⏱  Stage Timing Summary:${NC}"
    for entry in "${STAGE_TIMES[@]}"; do
        stage_name="${entry%%:*}"
        stage_ms="${entry##*:}"
        if [ "$stage_ms" -eq 0 ]; then
            echo -e "     ${stage_name}: skipped"
        else
            echo -e "     ${stage_name}: ${stage_ms}ms"
        fi
    done
    echo ""
fi

exit $OVERALL_STATUS
