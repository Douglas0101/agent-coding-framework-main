#!/usr/bin/env python3
"""ITCH Pipeline — Data Inspector.

Quick post-pipeline diagnostic tool that inspects Parquet output.

Checks:
  1. Lists all partitions with row counts and file sizes
  2. Shows schema for each dataset
  3. Computes basic stats (timestamps, tickers, nulls)
  4. Cross-dataset consistency checks

Usage:
    python .agent/skills/itch-pipeline/scripts/inspect_data.py
    python .agent/skills/itch-pipeline/scripts/inspect_data.py --json
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path


_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from src.skill_hex_core import (  # noqa: E402
    JsonMap,
    to_float,
    to_int,
    to_str_map,
)


_DATASETS = ("trades", "book_snapshots", "ohlcv")


def _ticker_keys(record: JsonMap) -> set[str]:
    """Return ticker keys from ticker_distribution field."""
    ticker_dist = to_str_map(record.get("ticker_distribution"))
    return set(ticker_dist)


def _scan_partitions(
    base: Path,
    dataset: str,
) -> list[JsonMap]:
    """Scan Hive-partitioned directory for Parquet files."""
    ds_dir = base / dataset
    if not ds_dir.exists():
        return []

    partitions: list[JsonMap] = []
    for pf in sorted(ds_dir.rglob("*.parquet")):
        rel = pf.relative_to(ds_dir)
        parts = {
            p.split("=")[0]: p.split("=")[1]
            for p in rel.parts[:-1]
            if "=" in p
        }
        size_mb = pf.stat().st_size / 1e6
        partitions.append(
            {
                "path": str(rel),
                "size_mb": round(size_mb, 3),
                **parts,
            }
        )
    return partitions


def _inspect_dataset(base: Path, dataset: str) -> JsonMap:
    """Inspect a single dataset."""
    ds_dir = base / dataset
    result: JsonMap = {
        "dataset": dataset,
        "exists": ds_dir.exists(),
    }

    if not ds_dir.exists():
        return result

    partitions = _scan_partitions(base, dataset)
    result["partition_count"] = len(partitions)
    total = sum(to_float(partition.get("size_mb")) for partition in partitions)
    result["total_size_mb"] = round(total, 3)

    try:
        pq = importlib.import_module("pyarrow.parquet")

        table = pq.read_table(str(ds_dir))
        df = table.to_pandas()

        result["row_count"] = len(df)
        result["columns"] = list(df.columns)
        result["dtypes"] = {col: str(df[col].dtype) for col in df.columns}

        null_counts = {col: int(df[col].isna().sum()) for col in df.columns}
        result["null_counts"] = {k: v for k, v in null_counts.items() if v > 0}

        if "timestamp" in df.columns:
            ts = df["timestamp"]
            result["timestamp_min"] = str(ts.min())
            result["timestamp_max"] = str(ts.max())

        if "stock" in df.columns:
            dist = df["stock"].value_counts().to_dict()
            ticker_dist = {str(k): int(v) for k, v in dist.items()}
            result["ticker_distribution"] = ticker_dist

        if dataset == "trades" and "price" in df.columns:
            result["price_range"] = {
                "min": round(float(df["price"].min()), 4),
                "max": round(float(df["price"].max()), 4),
                "mean": round(
                    float(df["price"].mean()),
                    4,
                ),
            }

        if dataset == "ohlcv" and "vwap" in df.columns:
            result["vwap_range"] = {
                "min": round(float(df["vwap"].min()), 4),
                "max": round(float(df["vwap"].max()), 4),
            }

    except Exception as exc:
        result["error"] = str(exc)

    return result


def _cross_dataset_check(
    inspections: dict[str, JsonMap],
) -> list[JsonMap]:
    """Check consistency across datasets."""
    checks: list[JsonMap] = []

    trades = inspections.get("trades", {})
    ohlcv = inspections.get("ohlcv", {})
    snapshots = inspections.get("book_snapshots", {})

    t_count = to_int(trades.get("row_count"))
    o_count = to_int(ohlcv.get("row_count"))
    if t_count and o_count:
        if t_count < o_count:
            checks.append(
                {
                    "check": "trades_vs_ohlcv",
                    "status": "WARN",
                    "detail": (f"OHLCV bars ({o_count}) > trades ({t_count})"),
                }
            )
        else:
            ratio = round(t_count / o_count, 1)
            checks.append(
                {
                    "check": "trades_vs_ohlcv",
                    "status": "OK",
                    "detail": (f"Ratio: {ratio} trades per bar"),
                }
            )

    t_tickers = _ticker_keys(trades)
    o_tickers = _ticker_keys(ohlcv)
    s_tickers = _ticker_keys(snapshots)

    all_tickers = t_tickers | o_tickers | s_tickers
    if all_tickers:
        missing_t = all_tickers - t_tickers if t_tickers else set()
        missing_o = all_tickers - o_tickers if o_tickers else set()

        if missing_t or missing_o:
            checks.append(
                {
                    "check": "ticker_consistency",
                    "status": "WARN",
                    "detail": (
                        f"Missing in trades: "
                        f"{missing_t or 'none'}, "
                        f"in ohlcv: "
                        f"{missing_o or 'none'}"
                    ),
                }
            )
        else:
            n = len(all_tickers)
            checks.append(
                {
                    "check": "ticker_consistency",
                    "status": "OK",
                    "detail": (f"{n} tickers consistent"),
                }
            )

    return checks


def main() -> int:
    """Run data inspection."""
    ap = argparse.ArgumentParser(
        description="ITCH Pipeline data inspector",
    )
    ap.add_argument(
        "--base",
        default=str(
            _PROJECT_ROOT / "data" / "processed" / "itch",
        ),
        help="Base output directory",
    )
    ap.add_argument(
        "--dataset",
        default=None,
        choices=_DATASETS,
        help="Inspect a specific dataset only",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="JSON output",
    )
    args = ap.parse_args()

    base = Path(args.base)
    datasets = [args.dataset] if args.dataset else list(_DATASETS)

    inspections: dict[str, JsonMap] = {}
    for ds in datasets:
        inspections[ds] = _inspect_dataset(base, ds)

    if len(datasets) > 1:
        consistency = _cross_dataset_check(inspections)
    else:
        consistency = []

    if args.json:
        output = {
            "base_dir": str(base),
            "datasets": inspections,
            "consistency_checks": consistency,
        }
        print(json.dumps(output, indent=2, default=str))
    else:
        sep = "=" * 55
        print(f"\n{sep}")
        print("  ITCH Pipeline — Data Inspector")
        print(f"  Base: {base}")
        print(sep)

        for ds, info in inspections.items():
            print(f"\n  📊 {ds}")
            if not info.get("exists"):
                print("     ⏭  Not found")
                continue

            if "error" in info:
                print(f"     ❌ Error: {info['error']}")
                continue

            rows = info.get("row_count", "?")
            parts = info.get("partition_count", "?")
            size = info.get("total_size_mb", "?")
            cols = info.get("columns", [])
            rows_display = f"{rows:,}" if isinstance(rows, int) else str(rows)
            print(f"     Rows:       {rows_display}")
            print(f"     Partitions: {parts}")
            print(f"     Size:       {size} MB")
            print(f"     Columns:    {cols}")

            nc = info.get("null_counts")
            if nc:
                print(f"     Nulls:      {nc}")

            td = info.get("ticker_distribution")
            if td:
                td_map = to_str_map(td)
                preview = dict(list(td_map.items())[:5])
                extra = len(td_map) - 5
                suffix = f" ... +{extra} more" if extra > 0 else ""
                print(f"     Tickers:    {preview}{suffix}")

            pr = info.get("price_range")
            if pr:
                pr_map = to_str_map(pr)
                mn = pr_map.get("min", "?")
                mx = pr_map.get("max", "?")
                av = pr_map.get("mean", "?")
                print(f"     Price:      [{mn}, {mx}] mean={av}")

        if consistency:
            print("\n  🔗 Cross-Dataset Checks")
            for c in consistency:
                icon = "✅" if c["status"] == "OK" else "⚠️"
                print(f"     {icon} {c['check']}: {c['detail']}")

        print(f"\n{sep}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
