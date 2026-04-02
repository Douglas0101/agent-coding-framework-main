---
description: Validate output Parquet data integrity and quality after pipeline runs
---

# Validate Output Data

// turbo-all

1. **Pre-flight** — Ensure environment is ready:
```bash
python .agent/skills/itch-pipeline/scripts/validate_env.py
```

2. **Quick inspection** — Scan all output datasets for partitions, row counts, and sizes:
```bash
python .agent/skills/itch-pipeline/scripts/inspect_data.py
```

3. **Run strict ETL contract check** — Structural + domain + quarantine budget gate:
```bash
python .agent/skills/etl-ml-readiness/scripts/check_etl_contract.py \
    --base data/processed/itch \
    --contract contracts/pipeline/itch_etl_contract_nasdaq_v1.yml \
    --max-quarantine-ratio 0.0
```

4. **Check for Parquet files** — Verify output exists:
```bash
find data/processed/itch -name "*.parquet" -type f | head -20
```
> If no files are found, the pipeline has not been run yet.

5. **Validate trades schema** — Check that trade data matches the expected schema:
```python
python3 -c "
from src.data.itch.validators import validate_schema, TRADE_SCHEMA
from src.data.itch.storage import read_dataset

trades = read_dataset('data/processed/itch', 'trades')
result = validate_schema(trades, TRADE_SCHEMA)
print('Trades valid:', result['valid'])
if not result['valid']:
    print('  Missing columns:', result['missing_columns'])
    print('  Type mismatches:', result['type_mismatches'])
print('  Null counts:', {k: v for k, v in result['null_counts'].items() if v > 0})
print('  Row count:', len(trades))
"
```

6. **Validate OHLCV output** — Check aggregated bar data:
```python
python3 -c "
from src.data.itch.storage import read_dataset

ohlcv = read_dataset('data/processed/itch', 'ohlcv')
print('OHLCV rows:', len(ohlcv))
print('Columns:', list(ohlcv.columns))
print('Tickers:', sorted(ohlcv['stock'].unique()) if 'stock' in ohlcv.columns else 'N/A')
# Sanity check: high >= low
if {'high', 'low'}.issubset(ohlcv.columns):
    violations = (ohlcv['high'] < ohlcv['low']).sum()
    print(f'High < Low violations: {violations}')
"
```

7. **Validate book snapshots** — Check order book snapshot data:
```python
python3 -c "
from src.data.itch.storage import read_dataset

snaps = read_dataset('data/processed/itch', 'book_snapshots')
print('Book snapshot rows:', len(snaps))
print('Columns:', list(snaps.columns))
# Check for expected bid/ask columns
bid_cols = [c for c in snaps.columns if c.startswith('bid_price')]
ask_cols = [c for c in snaps.columns if c.startswith('ask_price')]
print(f'Bid levels: {len(bid_cols)}, Ask levels: {len(ask_cols)}')
# Sanity: best ask > best bid
if 'bid_price_0' in snaps.columns and 'ask_price_0' in snaps.columns:
    valid_rows = snaps.dropna(subset=['bid_price_0', 'ask_price_0'])
    crossings = (valid_rows['ask_price_0'] < valid_rows['bid_price_0']).sum()
    print(f'Crossed book violations (ask < bid): {crossings}')
"
```

8. **Cross-dataset consistency** — Verify trade and OHLCV counts are consistent:
```python
python3 -c "
from src.data.itch.storage import read_dataset

trades = read_dataset('data/processed/itch', 'trades')
ohlcv = read_dataset('data/processed/itch', 'ohlcv')
print(f'Trades:     {len(trades):>10,} rows')
print(f'OHLCV bars: {len(ohlcv):>10,} rows')
ratio = len(trades) / max(len(ohlcv), 1)
print(f'Ratio:      {ratio:.1f} trades per bar')

# Ticker consistency
trade_tickers = set(trades['stock'].unique()) if 'stock' in trades.columns else set()
ohlcv_tickers = set(ohlcv['stock'].unique()) if 'stock' in ohlcv.columns else set()
missing_in_ohlcv = trade_tickers - ohlcv_tickers
if missing_in_ohlcv:
    print(f'WARNING: Tickers in trades but not OHLCV: {missing_in_ohlcv}')
else:
    print(f'Tickers consistent: {len(trade_tickers)} tickers in both datasets')
"
```

9. **Anomaly detection** — Check for price spikes and volume outliers:
```python
python3 -c "
from src.data.itch.validators import AnomalyDetector
from src.data.itch.storage import read_dataset

trades = read_dataset('data/processed/itch', 'trades')
detector = AnomalyDetector(sigma_threshold=5.0)

if 'price' in trades.columns:
    spikes = detector.detect_price_spikes(trades['price'])
    print(f'Price spikes (>5σ): {spikes.sum()} / {len(trades)}')

if 'shares' in trades.columns:
    outliers = detector.detect_volume_outliers(trades['shares'])
    print(f'Volume outliers (>5σ): {outliers.sum()} / {len(trades)}')
"
```
