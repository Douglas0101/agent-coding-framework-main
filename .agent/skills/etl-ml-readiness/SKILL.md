---
name: etl-ml-readiness
description: ETL-first execution protocol for low-latency ITCH processing with strict data contract checks before ML training
---

# ETL ML Readiness - Agent Skill

> Purpose: run ETL with performance discipline and strict quality gates so
> model training only starts from deterministic, audit-ready datasets.

---

## 1. Scope

This skill is ETL-only.

- In scope: ingest, decode, normalize, validate, persist, benchmark.
- Out of scope: online inference, strategy logic, execution routing.

This keeps the current sprint focused on the data foundation.

---

## 2. Golden Path (recommended)

Run these steps in order.

```bash
# 1) Environment pre-flight
python .agent/skills/itch-pipeline/scripts/validate_env.py

# 2) ETL execution (performance profile + strict quarantine policy)
python scripts/run_itch_pipeline.py \
    --input data/raw/<FILE_OR_DIR> \
    --perf-profile \
    --operational \
    --strict-quality \
    --json

# 3) Data contract gate (ML readiness)
python .agent/skills/etl-ml-readiness/scripts/check_etl_contract.py \
    --base data/processed/itch \
    --contract contracts/pipeline/itch_etl_contract_nasdaq_v1.yml \
    --max-quarantine-ratio 0.0 \
    --require-snapshots

# 4) Throughput and resource benchmark
python .agent/skills/itch-pipeline/scripts/benchmark.py \
    --input data/raw/<FILE_OR_DIR> \
    --config config/itch_pipeline_perf.yml
```

If any step fails, stop and fix before moving forward.

---

## 3. Mandatory Quality Gates

| Gate | What It Enforces | Pass Condition |
|------|------------------|----------------|
| `validate_env.py` | Runtime + dependencies + config integrity | Exit code `0` |
| `run_itch_pipeline.py --strict-quality` | No silent quality loss during ETL | No quarantine-triggered failure |
| `check_etl_contract.py` | Post-write structural and domain integrity | `passed=true` |
| `benchmark.py` | Performance visibility and regressions | Metrics generated and tracked |

No ML experiment should run if these gates are not green.

---

## 4. Data Contract Gate (strict)

The contract checker validates:

1. **Trades schema + domain**
   - Required columns and Arrow-compatible types
   - `price > 0`, `shares > 0`, `order_ref > 0`
   - `buy_sell in {"B", "S"}`
   - Nulls in critical columns are rejected

2. **Trades temporal ordering**
   - `timestamp` monotonic non-decreasing inside each Parquet partition file

3. **OHLCV schema + consistency**
   - Required columns and expected types
   - `high >= low`
   - `open` and `close` inside `[low, high]`
   - `volume >= 0`, `trade_count >= 0`

4. **Book snapshot sanity**
   - `ask_price_0 >= bid_price_0`
   - `bid_size_0 >= 0`, `ask_size_0 >= 0`

5. **Quarantine budget**
    - `quarantine_rows / trade_rows <= max_quarantine_ratio`
    - For strict institutional datasets use `0.0`

6. **Quarantine reason contract**
   - Every quarantined row must include `quarantine_reason`
   - `quarantine_reason` must belong to
     `quarantine.allowed_reason_codes`
     in `contracts/pipeline/itch_etl_contract_nasdaq_v1.yml`

---

## 5. Hardware-aware defaults (IdeaPad i3 / 20 GB RAM)

Use performance profile:

- `--perf-profile` in CLI
- `config/itch_pipeline_perf.yml`

This profile is tuned for constrained local hardware:

- lower parser chunk size
- more frequent garbage collection
- periodic flush during parsing
- reduced snapshot depth
- faster write compression profile

---

## 6. Failure policy

If a gate fails:

1. Fix root cause.
2. Re-run the failed gate.
3. Re-run the full Golden Path before declaring ETL ready.

Do not patch around validation errors to force model training.

---

## 7. Useful variants

```bash
# JSON output for CI
python .agent/skills/etl-ml-readiness/scripts/check_etl_contract.py \
    --base data/processed/itch \
    --contract contracts/pipeline/itch_etl_contract_nasdaq_v1.yml \
    --json

# Allow tiny quarantine budget (example)
python .agent/skills/etl-ml-readiness/scripts/check_etl_contract.py \
    --base data/processed/itch \
    --contract contracts/pipeline/itch_etl_contract_nasdaq_v1.yml \
    --max-quarantine-ratio 0.001

# Skip snapshot requirement when running schema that does not emit snapshots
python .agent/skills/etl-ml-readiness/scripts/check_etl_contract.py \
    --base data/processed/itch \
    --contract contracts/pipeline/itch_etl_contract_nasdaq_v1.yml \
    --no-require-snapshots
```

---

## 8. Exit code contract

- `0` -> all ETL quality gates passed
- `1` -> one or more contract checks failed

This allows direct use in CI and release validation.
