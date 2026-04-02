---
description: Run the ITCH 5.0 data processing pipeline on raw files
---

# Run ITCH Pipeline

// turbo-all

1. **Pre-flight check** — Validate the environment before running:
```bash
python .agent/skills/itch-pipeline/scripts/validate_env.py
```
> If any check fails, fix the issue before proceeding.

2. **Single file execution** — Run the pipeline on a specific ITCH file:
```bash
python scripts/run_itch_pipeline.py \
    --input data/raw/<FILE> \
    --config config/itch_pipeline.yml
```
> Replace `<FILE>` with the actual filename (e.g., `01302019.NASDAQ_ITCH50`).

3. **With ticker filter** — Process only specific tickers:
```bash
python scripts/run_itch_pipeline.py \
    --input data/raw/<FILE> \
    --config config/itch_pipeline.yml \
    --tickers AAPL,MSFT,TSLA
```

4. **Batch execution** — Process all files in a directory:
```bash
python scripts/run_itch_pipeline.py \
    --input data/raw/ \
    --config config/itch_pipeline.yml
```

5. **Dry run** — Detect file formats and validate without processing:
```bash
python scripts/run_itch_pipeline.py \
    --input data/raw/ \
    --config config/itch_pipeline.yml \
    --dry-run --json
```
> Dry runs detect file format and report file info. No data is written.

6. **Post-run validation** — Inspect output data for integrity:
```bash
python .agent/skills/itch-pipeline/scripts/inspect_data.py
```

7. **Strict ETL contract gate** — Validate ML-readiness invariants:
```bash
python .agent/skills/etl-ml-readiness/scripts/check_etl_contract.py \
    --base data/processed/itch \
    --contract contracts/pipeline/itch_etl_contract_nasdaq_v1.yml \
    --max-quarantine-ratio 0.0 \
    --require-snapshots
```

8. **Engine override (optional)** — Force execution mode:
```bash
python scripts/run_itch_pipeline.py \
    --input data/raw/<FILE> \
    --config config/itch_pipeline.yml \
    --engine cpp
```

9. **Build C++ shared scanner (optional)** — No CMake required:
```bash
bash scripts/build_cpp_engine_shared.sh
```

### Interpreting Exit Codes

| Exit Code | Meaning |
|-----------|---------|
| `0` | Success — all files processed |
| `1` | Runtime error — check stderr for details |
| `2` | CLI argument error — invalid flags or missing required args |

### Interpreting Output

The pipeline reports a JSON summary per file:
```json
{"status": "success", "messages": 300000000, "elapsed_s": 180.5}
```

| Field | Meaning |
|-------|---------|
| `status` | `"success"` or `"error"` |
| `messages` | Total ITCH messages decoded |
| `elapsed_s` | Wall-clock seconds |
| `tickers_processed` | Number of unique tickers written |

If `status` is `"error"`, check the `error` field for the exception message.
