# Hybrid Core Maintenance

**Reference PRD:** [PRD_Hybrid_Core_Agent_Coding.md](PRD_Hybrid_Core_Agent_Coding.md)

---

## Purpose

This document explains how to maintain the Hybrid Core 1x/2x system safely.

---

## Files You Will Usually Touch

### Scope Detection

- `.internal/specs/core/scope-detection-engine.yaml`
- `.internal/runtime/scope_detector.py`
- `.internal/runtime/regression_harness.py`
- `.internal/scripts/calibrate_scope_detector.py`

### Contracts and Adapters

- `.internal/specs/core/execution-profiles.yaml`
- `.internal/specs/core/universal-quality-contract.yaml`
- `.internal/specs/core/algorithmic-frontier-contract.yaml`
- `.internal/specs/modes/autocoder.yaml`
- `.internal/modes/autocoder/adapters/default-1x.yaml`
- `.internal/modes/autocoder/adapters/performance-2x-tier-2.yaml`
- `.internal/modes/autocoder/adapters/performance-2x-tier-3.yaml`

### Gates and Validation

- `.internal/runtime/gate_executor.py`
- `.internal/domains/ioi-gold-compiler/frontier-validation-gates.yaml`
- `.internal/runtime/output_validator.py`
- `.internal/runtime/hybrid_core_validator.py`

### Observability and Rollout

- `.internal/runtime/hybrid_core_observability.py`
- `.internal/runtime/hybrid_core_config.py`
- `.github/workflows/hybrid-core-regression.yml`

---

## Safe Change Workflow

1. Update the relevant spec or runtime file.
2. Add or update regression scenarios.
3. Run calibration.
4. Run targeted runtime tests.
5. Run framework/contract tests.
6. Review whether rollout behavior changed.
7. Update the PRD compliance matrix if the change affects scope or status.

---

## Updating Triggers and Thresholds

When changing scope detection behavior:

1. Prefer spec changes in `scope-detection-engine.yaml` before runtime logic changes.
2. Avoid raw substring matching for short technical words.
3. Add regression cases for:
   - intended positive match
   - near-miss false positive
   - Tier 1 non-technical usage
4. Re-run calibration and compare pass rate.

### Trigger Change Checklist

- Does it create a new Tier 1 false positive?
- Does it collapse a Tier 3 case into Tier 2?
- Does it rely on an ambiguous short token?
- Does it need a structural-pattern test and a plain-language test?

---

## Updating Gates

When modifying gates:

1. Confirm the change still respects `NOU > NOE` precedence.
2. Add a failing and passing test for the new rule.
3. Check that auto-reject behavior still matches the PRD.
4. Re-run runtime tests, especially:

```bash
python -m pytest .internal/runtime/tests/test_gate_executor.py -v
python -m pytest .internal/runtime/tests/test_output_validator.py -v
python -m pytest .internal/runtime/tests/test_hybrid_core_validator.py -v
```

---

## Updating the Algorithm Catalog

When adding or changing frontier techniques:

1. Update `frontier-algorithmic-core.yaml`.
2. Update `algorithm-selection-map.yaml` if routing should change.
3. Add or update Tier 2/Tier 3 classification tests.
4. Ensure the new technique has:
   - applicability
   - complexity
   - preconditions
   - limitations
   - pitfalls
   - usage example
   - reasons not to use

---

## Rollout Operations

### Disable rollout

```bash
export OPENCODE_HYBRID_CORE=disabled
```

### Enable rollout

```bash
export OPENCODE_HYBRID_CORE=enabled
```

### Set acceptance target

```bash
export OPENCODE_TARGET_ACCURACY=0.95
```

---

## Required Validation Commands

Minimum before merge:

```bash
python .internal/scripts/calibrate_scope_detector.py --verbose
python -m pytest .internal/runtime/tests/ -q
python -m pytest .internal/tests/ -q
```

---

## Known Maintenance Risks

1. Short ambiguous keywords can cause classification drift.
2. CI can drift from local scripts if command-line interfaces change.
3. The `autocoder` contract, adapters, and validator must stay schema-aligned.
4. Rollout behavior must remain explicit because `opencode.json` cannot hold custom feature keys.

---

## Source of Truth

- Product intent: `docs/PRD_Hybrid_Core_Agent_Coding.md`
- Runtime contracts: `.internal/specs/core/`
- Mode contract: `.internal/specs/modes/autocoder.yaml`
- Implementation log: `.internal/artifacts/hybrid-core/IMPLEMENTATION_LOG.md`
