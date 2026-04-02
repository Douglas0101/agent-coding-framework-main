---
name: itch-pipeline
description: Complete Nasdaq ITCH 5.0 data processing pipeline — environment authentication, execution, quality gate, and troubleshooting
---

# ITCH 5.0 Pipeline — Agent Skill

> **Purpose**: Operate the entire ITCH data pipeline with authenticated execution, uniform parameterization, and zero context breaks.

---

## 1. Project Layout

```
quant-trading-project/
├── config/itch_pipeline.yml          # ← Single source of truth for ALL params
├── src/data/itch/
│   ├── protocol.py                   # 21 ITCH 5.0 message type definitions
│   ├── parser.py                     # Streaming binary parser (64 MB chunks)
│   ├── detector.py                   # File format detection (5 variants)
│   ├── validators.py                 # Schema + timestamp + anomaly checks
│   ├── order_book.py                 # L3 LOB reconstruction (SortedDict)
│   ├── storage.py                    # Parquet writer (Zstd + Hive partitioning)
│   └── pipeline.py                   # AsyncIO orchestrator
├── src/features/
│   ├── microstructure.py             # VPIN, Kyle's Lambda, OI, Spread, RV
│   └── ohlcv.py                      # Time/Volume/Dollar bars
├── scripts/run_itch_pipeline.py      # CLI entry point
└── tests/                            # 47 unit + integration tests
```

---

## 2. Environment Authentication (Pre-Flight)

**ALWAYS run the environment validator before any pipeline operation:**

```bash
python .agent/skills/itch-pipeline/scripts/validate_env.py
```

This script checks:

| Check | What It Validates |
|-------|-------------------|
| **Python Version** | Python ≥ 3.14 (project baseline for tooling + LSP) |
| **Dependencies** | All packages in `requirements.txt` importable |
| **Protocol Integrity** | `struct.calcsize(fmt) == declared_size` for all 21 message types |
| **PyArrow Compat** | `pyarrow >= 14.0` and `pa.schema()` callable |
| **Config Schema** | All required YAML keys present with correct types |
| **Directories** | `data/raw/`, `data/processed/itch/` exist and are writable |
| **Disk Space** | ≥ 10 GB free (a daily ITCH file is ~5 GB; output can be 2×) |
| **Quality Tools** | `ruff`, `mypy` and `basedpyright` are available for quality gate |

> [!CAUTION]
> If the validator fails, **DO NOT proceed** with pipeline execution. Fix the reported issue first.

**Diagnostic flags:**
```bash
python .agent/skills/itch-pipeline/scripts/validate_env.py --verbose  # Show package versions + timing
python .agent/skills/itch-pipeline/scripts/validate_env.py --json     # Machine-readable output
```

### Manual Dependency Install

```bash
pip install -r requirements.txt
pip install -e .
```

---

## 3. Uniform Parameterization

**All parameters flow from a single config file:** `config/itch_pipeline.yml`

### Parameter Mapping

| YAML Key | Module | Parameter | Default |
|----------|--------|-----------|---------|
| `paths.raw_dir` | `pipeline.py → run_batch()` | input directory | `data/raw` |
| `paths.processed_dir` | `storage.py → ParquetWriter` | `base_dir` | `data/processed/itch` |
| `paths.interim_dir` | `pipeline.py` | reserved | `data/interim` |
| `parser.chunk_size_mb` | `parser.py → ITCHParser` | `chunk_size` (bytes = mb × 1048576) | `64` |
| `parser.skip_unknown_types` | `parser.py → ITCHParser` | `skip_unknown` | `true` |
| `pipeline.max_workers` | `pipeline.py` | reserved (sequential processing) | `2` |
| `pipeline.queue_maxsize` | `parser.py → async_parse_file` | async queue depth (hardcoded) | `10000` |
| `pipeline.gc_interval` | `pipeline.py → ITCHPipeline.run()` | GC every N messages | `50000` |
| `order_book.snapshot_interval_ms` | `order_book.py → BookBuilder` | `snapshot_interval_ns` (ms × 1e6) | `1000` |
| `order_book.depth` | `order_book.py → BookBuilder` | `depth` | `10` |
| `features.vpin_buckets` | `microstructure.py` | `n_buckets` | `50` |
| `features.volatility_window` | `microstructure.py` | `window` | `5min` |
| `features.ohlcv_freq` | `ohlcv.py` | `freq` | `1min` |
| `storage.compression` | `storage.py → ParquetWriter` | `compression` | `zstd` |
| `storage.compression_level` | `storage.py → ParquetWriter` | `compression_level` | `3` |
| `storage.row_group_size` | `storage.py → ParquetWriter` | `row_group_size` | `131072` |
| `storage.partitioning` | `storage.py → ParquetWriter._write()` | Hive partition columns | `["date", "ticker"]` |
| `tickers` | CLI / `pipeline.py` | ticker filter set | `[]` (all) |
| `engine.mode` | `pipeline.py → ITCHPipeline` | `engine_mode` (`python|cpp`) | `python` |
| `engine.fallback_to_python` | `pipeline.py → ITCHPipeline` | fallback behavior | `true` |
| `engine.shared_library_path` | `cpp_adapter.py` | optional `.so` path | `null` |

> [!IMPORTANT]
> Never hardcode parameters in module code. Always read from the YAML config via `ITCHPipeline(config_path)`. The canonical parameter reference is at `.agent/skills/itch-pipeline/resources/params_reference.yml`.

### CLI Flags (override config at runtime)

```bash
python scripts/run_itch_pipeline.py \
    --input <PATH>           # Required: file or directory
    --output <DIR>           # Optional: overrides paths.processed_dir
    --tickers AAPL,MSFT      # Optional: comma-separated filter
    --config <YAML>          # Optional: defaults to config/itch_pipeline.yml
    --engine cpp             # Optional: force C++ path (with safe fallback)
    --dry-run                # Optional: detect + validate only
    --json                   # Optional: JSON output to stdout
```

To build shared C++ scanner without CMake:

```bash
bash scripts/build_cpp_engine_shared.sh
```

---

## 4. Pipeline Execution

### 4.1 Single File

```bash
python scripts/run_itch_pipeline.py \
    --input data/raw/01302019.NASDAQ_ITCH50 \
    --tickers AAPL,MSFT,TSLA
```

### 4.2 Batch (entire directory)

```bash
python scripts/run_itch_pipeline.py \
    --input data/raw/ \
    --output data/processed/itch/
```

### 4.3 Dry Run (detect + validate only)

```bash
python scripts/run_itch_pipeline.py \
    --input data/raw/ --dry-run --json
```

### 4.4 Programmatic Execution

```python
import asyncio
from src.data.itch.pipeline import ITCHPipeline

pipeline = ITCHPipeline("config/itch_pipeline.yml")
result = asyncio.run(pipeline.run(
    "data/raw/01302019.NASDAQ_ITCH50",
    tickers={"AAPL", "MSFT"},
))
print(result)
# {"status": "success", "messages": 300000000, "elapsed_s": 180.5, ...}
```

### Pipeline Flow

```
detect_file_format()
        │
        ▼
ITCHParser.parse_file()   ──►   BookBuilder.process_message()
                                         │
                         ┌───────────────┼────────────────────┐
                         ▼               ▼                    ▼
                    trades_df      snapshots_df          (per-ticker)
                         │               │               aggregate_ohlcv()
                         │               │                    │
                         ▼               ▼                    ▼
              write_trades()   write_book_snapshots()   write_ohlcv()
```

---

## 5. Memory Management

> [!NOTE]
> ITCH files can exceed 5 GB (300M+ messages). The pipeline uses several strategies to control memory:

| Strategy | Location | Config Key |
|----------|----------|------------|
| **Streaming parser** | `parser.py` — generator, never loads full file | `parser.chunk_size_mb` |
| **Periodic GC** | `pipeline.py` — `gc.collect()` every N messages | `pipeline.gc_interval` |
| **Per-ticker release** | `pipeline.py → _write_results()` — DataFrames written and released per ticker | — |
| **Post-file cleanup** | `pipeline.py` — `gc.collect()` after each file completes | — |

**For low-memory environments (< 8 GB RAM):**
- Reduce `pipeline.gc_interval` to `10000`
- Reduce `parser.chunk_size_mb` to `32`
- Filter to specific tickers with `--tickers`

---

## 6. Output Schemas

The pipeline produces 3 Parquet datasets, each with its own PyArrow schema:

### Trades (`storage.TRADE_SCHEMA`)

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | `uint64` | Nanoseconds since midnight |
| `stock` | `string` | Ticker symbol |
| `price` | `float64` | Execution price (scaled ×1e-4) |
| `shares` | `int64` | Number of shares |
| `order_ref` | `uint64` | Order reference number |
| `match_number` | `uint64` | Match number |
| `buy_sell` | `string` | `"B"` or `"S"` |

### OHLCV (`storage.OHLCV_SCHEMA`)

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | `timestamp[ns]` | Bar open time |
| `stock` | `string` | Ticker symbol |
| `open` | `float64` | Opening price |
| `high` | `float64` | High price |
| `low` | `float64` | Low price |
| `close` | `float64` | Closing price |
| `volume` | `int64` | Total volume |
| `vwap` | `float64` | Volume-weighted average price |
| `trade_count` | `int64` | Number of trades |

### Book Snapshots (dynamic schema)

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | `uint64` | Snapshot time (ns) |
| `stock` | `string` | Ticker symbol |
| `bid_price_{i}` | `float64` | Bid price at level *i* (0 = best) |
| `bid_size_{i}` | `int64` | Bid volume at level *i* |
| `ask_price_{i}` | `float64` | Ask price at level *i* (0 = best) |
| `ask_size_{i}` | `int64` | Ask volume at level *i* |

Where *i* ranges from `0` to `order_book.depth - 1` (default 10 levels per side).

---

## 7. Quality Gate

**Run the full quality gate with a single command:**

```bash
bash .agent/skills/itch-pipeline/scripts/quality_gate.sh
```

This executes in strict order (fail-fast):

| Step | Command | Pass Criteria |
|------|---------|---------------|
| 1. Tests | `pytest tests/ -v --tb=short` | 47/47 pass |
| 2. Coverage | `pytest --cov=src --cov-fail-under=60` | ≥ 60% coverage |
| 3. Lint | `ruff check src/ tests/ scripts/` | 0 errors |
| 4. Types | `mypy src/ --ignore-missing-imports` | 0 errors |
| 5. LSP Types | `basedpyright` | 0 errors |

**Additional flags:**
```bash
bash .agent/skills/itch-pipeline/scripts/quality_gate.sh --fix   # Auto-fix ruff issues first
bash .agent/skills/itch-pipeline/scripts/quality_gate.sh --json  # Machine-readable output
```

### Individual Commands

```bash
# Tests only
pytest tests/ -v --tb=short

# Lint only
ruff check src/ tests/ scripts/

# Type check only
mypy src/ --ignore-missing-imports

# LSP type check only
basedpyright
```

---

## 8. Data Validation (Post-Pipeline)

### Quick Inspection

```bash
python .agent/skills/itch-pipeline/scripts/inspect_data.py
python .agent/skills/itch-pipeline/scripts/inspect_data.py --json
python .agent/skills/itch-pipeline/scripts/inspect_data.py --dataset trades
```

### Programmatic Validation

```python
from src.data.itch.validators import validate_schema, TRADE_SCHEMA
from src.data.itch.storage import read_dataset

# Read back processed data
trades = read_dataset("data/processed/itch", "trades", date_str="2019-01-30", ticker="AAPL")

# Validate schema
result = validate_schema(trades, TRADE_SCHEMA)
assert result["valid"], f"Schema errors: {result}"

# Check for anomalies
from src.data.itch.validators import AnomalyDetector
detector = AnomalyDetector(sigma_threshold=5.0)
spikes = detector.detect_price_spikes(trades["price"])
print(f"Price spikes: {spikes.sum()}")
```

---

## 9. Performance Profiling

```bash
python .agent/skills/itch-pipeline/scripts/benchmark.py
python .agent/skills/itch-pipeline/scripts/benchmark.py --input data/raw/01302019.NASDAQ_ITCH50
python .agent/skills/itch-pipeline/scripts/benchmark.py --config config/itch_pipeline.yml --json
```

### Expected Throughput

| Metric | Target | Benchmark Stage |
|--------|--------|-----------------|
| Parse speed | ~2–5 M messages/s | `protocol_decode` |
| Memory peak | < 4 GB for standard daily file | `parsing_memory` |
| Book operations | ~2 M events/s | `order_book` |
| Parquet write | ~500K rows/s with Zstd | `parquet_write` |

The benchmark compares actual results against these targets and prints `✅ ABOVE TARGET` / `⚠️ BELOW TARGET`.

---

## 10. Supported File Formats

| Pattern | Format | Schema |
|---------|--------|--------|
| `MMDDYYYY.NASDAQ_ITCH50` | standard | itch50 |
| `SMMDDYY-v50.txt` | legacy_v50 | itch50 |
| `SMMDDYY-v50-NOII.txt` | noii | itch50 |
| `SMMDDYY-v2.txt` | v2_text | itch_v2 |
| `*tvagg*` | tvagg | tvagg |

All formats support `.gz` compression transparently.

---

## 11. ITCH 5.0 Message Types

| Type | Name | Payload (bytes) | Category |
|------|------|-----------------|----------|
| `S` | System Event | 11 | System |
| `R` | Stock Directory | 38 | System |
| `H` | Stock Trading Action | 24 | System |
| `Y` | Reg SHO Restriction | 19 | System |
| `L` | Market Participant Position | 26 | System |
| `V` | MWCB Decline Level | 34 | System |
| `W` | MWCB Status | 11 | System |
| `K` | IPO Quoting Period Update | 27 | System |
| `J` | LULD Auction Collar | 34 | System |
| `h` | Operational Halt | 20 | System |
| `A` | Add Order (no MPID) | 35 | Order |
| `F` | Add Order (with MPID) | 39 | Order |
| `E` | Order Executed | 30 | Order |
| `C` | Order Executed with Price | 35 | Order |
| `X` | Order Cancel | 22 | Order |
| `D` | Order Delete | 18 | Order |
| `U` | Order Replace | 34 | Order |
| `P` | Non-Cross Trade | 43 | Trade |
| `Q` | Cross Trade | 39 | Trade |
| `B` | Broken Trade | 18 | Trade |
| `I` | NOII | 49 | NOII |

---

## 12. Troubleshooting Matrix

| Error | Root Cause | Fix |
|-------|------------|-----|
| `struct.error: unpack requires buffer of N bytes` | Payload size mismatch | Run `validate_env.py` — check protocol integrity |
| `AttributeError: pyarrow.lib.PyExtensionType` | PyArrow version < 14 | `pip install 'pyarrow>=14.0'` |
| `ImportError: cannot import ParquetWriter` | Eager import hitting PyArrow | Verify `src/data/itch/__init__.py` uses lazy `__getattr__` |
| `KeyError: 'stock_locate'` | Parsing wrong message section | Check `MESSAGE_SPECS` field tuple order matches format string |
| `FileNotFoundError` on config | Wrong CWD | Always run from project root: `cd quant-trading-project/` |
| `MemoryError` on large file | GC interval too high | Reduce `pipeline.gc_interval` in config (e.g. `10000`) |
| `test_all_specs_compile` failure | Declared size ≠ struct size | Fix `MESSAGE_SPECS[type][2]` to match `struct.calcsize(fmt)` |
| Slow parsing (< 1M msg/s) | Small chunk size | Increase `parser.chunk_size_mb` to `128` or `256` |

---

## 13. Key Design Decisions

1. **Lazy imports in `__init__.py`** — Prevents PyArrow import crashes at module load time
2. **Payload size = message body WITHOUT the 1-byte type indicator** — The parser strips the type byte before calling `decode_message()`
3. **Price scaling** — All ITCH prices are 4-decimal fixed-point integers, scaled by `× 1e-4` in `decode_message()`
4. **Timestamps** — 6-byte big-endian nanoseconds-since-midnight, stored as `np.uint64`
5. **SortedDict for order book** — O(log n) insert/delete, instant best-bid/ask via `peekitem(0)`
6. **Hive partitioning** — `date=YYYY-MM-DD/ticker=XXXX/` enables predicate pushdown on reads
7. **Sequential batch processing** — `run_batch()` processes files one at a time because each file saturates I/O and memory
