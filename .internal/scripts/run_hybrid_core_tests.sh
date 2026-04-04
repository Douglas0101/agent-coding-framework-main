#!/usr/bin/env bash
# Run all Hybrid Core 1x/2x tests
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "========================================"
echo "Hybrid Core 1x/2x Test Suite"
echo "========================================"
echo ""

cd "$REPO_ROOT"

echo "[1/6] Running Hybrid Core contract tests..."
python -m pytest .internal/tests/test_hybrid_core_contracts.py -v --tb=short
echo ""

echo "[2/6] Running Scope Detector tests..."
python -m pytest .internal/runtime/tests/test_scope_detector.py -v --tb=short
echo ""

echo "[3/6] Running Profile Activator tests..."
python -m pytest .internal/runtime/tests/test_profile_activator.py -v --tb=short
echo ""

echo "[4/6] Running Gate Executor tests..."
python -m pytest .internal/runtime/tests/test_gate_executor.py -v --tb=short
echo ""

echo "[5/6] Running Output Validator tests..."
python -m pytest .internal/runtime/tests/test_output_validator.py -v --tb=short
echo ""

echo "[6/6] Running Regression Harness tests..."
python -m pytest .internal/runtime/tests/test_regression_harness.py -v --tb=short
echo ""

echo "========================================"
echo "Running calibration analysis..."
echo "========================================"
python "$SCRIPT_DIR/calibrate_scope_detector.py" --verbose
echo ""

echo "========================================"
echo "All Hybrid Core tests passed!"
echo "========================================"
