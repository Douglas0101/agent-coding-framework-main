---
description: ETL-first flow for latency tuning and ML-ready data contract validation
---

# ETL ML Readiness

// turbo-all

1. Run pre-flight environment checks:
```bash
python .agent/skills/itch-pipeline/scripts/validate_env.py
```

2. Run ETL with performance profile and strict quality mode:
```bash
python scripts/run_itch_pipeline.py \
    --input data/raw/<FILE_OR_DIR> \
    --perf-profile \
    --operational \
    --strict-quality \
    --json
```

3. Run strict data contract gate before any ML training:
```bash
python .agent/skills/etl-ml-readiness/scripts/check_etl_contract.py \
    --base data/processed/itch \
    --contract contracts/pipeline/itch_etl_contract_nasdaq_v1.yml \
    --max-quarantine-ratio 0.0 \
    --require-snapshots
```

4. Run benchmark and capture throughput and memory metrics:
```bash
python .agent/skills/itch-pipeline/scripts/benchmark.py \
    --input data/raw/<FILE_OR_DIR> \
    --config config/itch_pipeline_perf.yml
```

5. Optional CI-friendly JSON checks:
```bash
python .agent/skills/etl-ml-readiness/scripts/check_etl_contract.py \
    --base data/processed/itch \
    --contract contracts/pipeline/itch_etl_contract_nasdaq_v1.yml \
    --json
```

### Exit Criteria

- `validate_env.py` returns code `0`
- ETL run does not fail strict quality gate
- `check_etl_contract.py` returns code `0`
- Benchmark output is generated for tracking regressions
