# Hybrid Core Usage

**Reference PRD:** [PRD_Hybrid_Core_Agent_Coding.md](PRD_Hybrid_Core_Agent_Coding.md)

---

## Overview

The Hybrid Core Execution Engine provides two execution profiles for agent coding:

- `default_1x`: universal engineering baseline (NOU only)
- `performance_2x`: specialized algorithmic/performance mode (NOU + NOE)

The system classifies tasks into:

- `tier_1_universal`
- `tier_2_algorithmic`
- `tier_3_competitive`

---

## Rollout Control

Hybrid Core rollout is controlled via environment variables.

### Enable Hybrid Core

```bash
export OPENCODE_HYBRID_CORE=enabled
```

Accepted truthy values:

- `enabled`
- `true`
- `1`
- `yes`

### Disable Hybrid Core

```bash
export OPENCODE_HYBRID_CORE=disabled
```

When disabled, the runtime forces:

- `execution_profile = default_1x`
- `scope_classification = tier_1_universal`

### Target Accuracy

```bash
export OPENCODE_TARGET_ACCURACY=0.95
```

This value is used by CI and calibration tooling as the expected minimum acceptance threshold.

---

## Running Calibration

### Human-readable output

```bash
python .internal/scripts/calibrate_scope_detector.py --verbose
```

### JSON output for CI or automation

```bash
python .internal/scripts/calibrate_scope_detector.py --json
```

The report includes:

- total scenarios
- passed/failed counts
- pass rate
- false positives
- tier 2 misses
- tier 3 misses
- over-engineering issues
- under-engineering issues
- failed scenarios

---

## Running Tests

### Full Hybrid Core runtime suite

```bash
python -m pytest .internal/runtime/tests/ -q
```

### Framework/contract suite

```bash
python -m pytest .internal/tests/ -q
```

### Convenience script

```bash
.internal/scripts/run_hybrid_core_tests.sh
```

---

## Inspecting Classification

Use the CLI to inspect scope classification directly.

### Human-readable

```bash
python .internal/runtime/hybrid_core_cli.py classify --task "Range minimum query with updates, n=200000"
```

### JSON

```bash
python .internal/runtime/hybrid_core_cli.py classify --task "Dynamic forest with link/cut operations" --output-format json
```

---

## Validating Agent Output

Validate structured output through the Hybrid Core validator:

```bash
python .internal/runtime/hybrid_core_cli.py validate \
  --task "Create a REST API endpoint for user registration" \
  --code-file path/to/source.py \
  --output-format text
```

The validator checks:

- scope/profile consistency
- universal quality gates
- specialized gates when `performance_2x` is active
- required output fields for the active profile

---

## Profile Expectations

### `default_1x`

Expected base output fields:

- `execution_profile`
- `scope_classification`
- `summary`
- `code_changes`
- `compliance_notes`
- `tests`
- `risks`
- `evidence_trail`

### `performance_2x`

Expected additional fields:

- `problem_analysis`
- `algorithm_selection_rationale`
- `complexity_certificate`
- `edge_case_analysis`
- `stress_test_plan`
- `memory_bound_estimate`

---

## Current Operational Notes

- The Hybrid Core contracts, adapters, validator, gates, and calibration tooling are implemented and tested.
- Rollout is environment-variable based because the OpenCode config schema does not accept custom repository feature keys.
- The repository wrapper `run-autocode.sh` now integrates the native autocode output with Hybrid Core validation — it delegates to `python .internal/runtime/hybrid_core_cli.py run-autocode`, which captures the final JSON event stream, parses the structured payload, and validates it through the HybridCoreValidator.
- The CLI `run-autocode` command provides full end-to-end operational proof of the 1x/2x Hybrid Core execution engine.
