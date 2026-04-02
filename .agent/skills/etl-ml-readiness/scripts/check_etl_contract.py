#!/usr/bin/env python3
"""ETL data contract validator for ML-ready ITCH datasets.

This checker runs strict post-write validations on the processed Parquet
datasets before any model training step.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as pds
import pyarrow.parquet as pq


_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent.parent.parent
_DEFAULT_CONTRACT_PATH = (
    _PROJECT_ROOT
    / "contracts"
    / "pipeline"
    / "itch_etl_contract_nasdaq_v1.yml"
)
sys.path.insert(0, str(_PROJECT_ROOT))

from src.data.itch.storage import OHLCV_SCHEMA, TRADE_SCHEMA  # noqa: E402
from src.skill_hex_core import (  # noqa: E402
    CheckRecord,
    CheckStatus,
    ValidationReport,
    load_yaml_mapping,
)


_BATCH_SIZE = 262_144
_SNAPSHOT_REQUIRED = (
    "bid_price_0",
    "ask_price_0",
    "bid_size_0",
    "ask_size_0",
)


@dataclass(slots=True)
class ContractContext:
    """Runtime context for ETL contract checks."""

    base_dir: Path
    max_quarantine_ratio: float
    require_snapshots: bool
    verbose: bool
    contract_path: Path
    allowed_quarantine_reasons: frozenset[str]
    strict_quarantine_reasons: bool
    contract_load_error: str | None = None


def _record(
    check: str,
    status: CheckStatus,
    detail: str,
    elapsed_ms: float,
) -> CheckRecord:
    """Create normalized check record."""
    return CheckRecord(
        check=check,
        status=status,
        detail=detail,
        elapsed_ms=round(elapsed_ms, 1),
    )


def _summary(report: ValidationReport, *, verbose: bool) -> str:
    """Build human-readable summary."""
    status_header = "PASS" if report.passed else "FAIL"
    lines = [f"ETL contract gate: {status_header}"]
    for check in report.checks:
        detail = f" - {check.detail}" if check.detail else ""
        timing = f" [{check.elapsed_ms:.1f}ms]" if verbose else ""
        lines.append(f"[{check.status.value}] {check.check}{detail}{timing}")
    return "\n".join(lines)


def _dataset(dataset_path: Path) -> pds.FileSystemDataset | None:
    """Open Parquet dataset with Hive partitions."""
    if not dataset_path.exists():
        return None
    return pds.dataset(
        str(dataset_path),
        format="parquet",
        partitioning="hive",
    )


def _count_true(mask: pa.Array | pa.ChunkedArray) -> int:
    """Count True values in nullable boolean mask."""
    normalized = pc.fill_null(mask, False)
    as_int = pc.cast(normalized, pa.int64())
    raw = pc.call_function("sum", [as_int]).as_py()
    return int(raw or 0)


def _schema_map(schema: pa.Schema) -> dict[str, str]:
    """Map field names to Arrow dtype string."""
    return {field.name: str(field.type) for field in schema}


def _fmt_list(values: list[str], *, max_items: int = 5) -> str:
    """Compact list formatter for details."""
    if not values:
        return "none"
    shown = values[:max_items]
    extra = len(values) - len(shown)
    suffix = f" (+{extra} more)" if extra > 0 else ""
    return ", ".join(shown) + suffix


def _as_mapping(value: object) -> dict[str, Any]:
    """Best-effort conversion from unknown object to mapping."""
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items()}


def _as_float(value: object, *, default: float) -> float:
    """Parse threshold-like value as float with fallback."""
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _as_bool(value: object, *, default: bool) -> bool:
    """Parse flag-like value as bool with fallback."""
    if isinstance(value, bool):
        return value
    return default


def _extract_allowed_quarantine_reasons(
    contract_mapping: dict[str, Any],
) -> frozenset[str]:
    """Extract allowed quarantine reason codes from contract mapping."""
    quarantine = _as_mapping(contract_mapping.get("quarantine"))
    raw_codes = quarantine.get("allowed_reason_codes")
    if not isinstance(raw_codes, list):
        return frozenset()
    normalized = {str(code).strip() for code in raw_codes if str(code).strip()}
    return frozenset(normalized)


def _extract_contract_thresholds(
    contract_mapping: dict[str, Any],
) -> tuple[float, bool]:
    """Extract quality gate thresholds from contract mapping."""
    thresholds = _as_mapping(contract_mapping.get("contract_thresholds"))
    max_ratio = _as_float(
        thresholds.get("max_quarantine_ratio"),
        default=0.0,
    )
    require_snapshots = _as_bool(
        thresholds.get("require_snapshots"),
        default=False,
    )
    return max_ratio, require_snapshots


def _check_contract_configuration(ctx: ContractContext) -> CheckRecord:
    """Validate contract configuration loading and required fields."""
    t0 = time.perf_counter()

    if ctx.contract_load_error is not None:
        elapsed = (time.perf_counter() - t0) * 1000
        status = (
            CheckStatus.FAIL
            if ctx.strict_quarantine_reasons
            else CheckStatus.WARN
        )
        return _record(
            "contract_configuration",
            status,
            ctx.contract_load_error,
            elapsed,
        )

    if not ctx.allowed_quarantine_reasons:
        elapsed = (time.perf_counter() - t0) * 1000
        status = (
            CheckStatus.FAIL
            if ctx.strict_quarantine_reasons
            else CheckStatus.WARN
        )
        return _record(
            "contract_configuration",
            status,
            "contract does not define quarantine.allowed_reason_codes",
            elapsed,
        )

    elapsed = (time.perf_counter() - t0) * 1000
    detail = (
        f"contract={ctx.contract_path}, "
        f"reason_codes={len(ctx.allowed_quarantine_reasons)}"
    )
    return _record("contract_configuration", CheckStatus.PASS, detail, elapsed)


def _check_schema(
    *,
    check_name: str,
    dataset_path: Path,
    expected_schema: pa.Schema,
    required_fields: tuple[str, ...],
    require_non_empty: bool,
) -> CheckRecord:
    """Validate required fields and Arrow types for one dataset."""
    t0 = time.perf_counter()
    if not dataset_path.exists():
        elapsed = (time.perf_counter() - t0) * 1000
        return _record(
            check_name,
            CheckStatus.FAIL,
            f"dataset missing: {dataset_path}",
            elapsed,
        )

    try:
        dataset = _dataset(dataset_path)
        if dataset is None:
            raise ValueError("dataset not available")
        rows = int(dataset.count_rows())
        actual = _schema_map(dataset.schema)
        expected = _schema_map(expected_schema)
    except Exception as exc:
        elapsed = (time.perf_counter() - t0) * 1000
        return _record(
            check_name,
            CheckStatus.FAIL,
            f"dataset load error: {exc}",
            elapsed,
        )

    missing = [name for name in required_fields if name not in actual]
    mismatches = [
        f"{name}:{actual[name]}!={expected[name]}"
        for name in expected
        if name in actual and actual[name] != expected[name]
    ]

    if missing or mismatches:
        elapsed = (time.perf_counter() - t0) * 1000
        detail = (
            f"missing={_fmt_list(missing)}; "
            f"type_mismatch={_fmt_list(mismatches)}"
        )
        return _record(check_name, CheckStatus.FAIL, detail, elapsed)

    if require_non_empty and rows == 0:
        elapsed = (time.perf_counter() - t0) * 1000
        return _record(
            check_name,
            CheckStatus.FAIL,
            "dataset is empty",
            elapsed,
        )

    elapsed = (time.perf_counter() - t0) * 1000
    return _record(check_name, CheckStatus.PASS, f"rows={rows}", elapsed)


def _check_trades_domain(trades_path: Path) -> CheckRecord:
    """Validate domain constraints for trades dataset."""
    t0 = time.perf_counter()
    dataset = _dataset(trades_path)
    if dataset is None:
        elapsed = (time.perf_counter() - t0) * 1000
        return _record(
            "trades_domain",
            CheckStatus.FAIL,
            f"dataset missing: {trades_path}",
            elapsed,
        )

    required = (
        "timestamp",
        "stock",
        "price",
        "shares",
        "order_ref",
        "buy_sell",
    )
    schema_names = set(dataset.schema.names)
    missing = [name for name in required if name not in schema_names]
    if missing:
        elapsed = (time.perf_counter() - t0) * 1000
        return _record(
            "trades_domain",
            CheckStatus.FAIL,
            f"missing columns: {_fmt_list(missing)}",
            elapsed,
        )

    scanner = dataset.scanner(columns=list(required), batch_size=_BATCH_SIZE)
    rows = 0
    null_critical = 0
    invalid_price = 0
    invalid_shares = 0
    invalid_order_ref = 0
    invalid_side = 0

    allowed = pa.array(["B", "S"], type=pa.string())

    for batch in scanner.to_batches():
        rows += batch.num_rows

        timestamp_col = batch.column(batch.schema.get_field_index("timestamp"))
        stock_col = batch.column(batch.schema.get_field_index("stock"))
        price_col = batch.column(batch.schema.get_field_index("price"))
        shares_col = batch.column(batch.schema.get_field_index("shares"))
        order_ref_col = batch.column(batch.schema.get_field_index("order_ref"))
        side_col = batch.column(batch.schema.get_field_index("buy_sell"))

        null_critical += timestamp_col.null_count
        null_critical += stock_col.null_count
        null_critical += price_col.null_count
        null_critical += shares_col.null_count
        null_critical += order_ref_col.null_count
        null_critical += side_col.null_count

        price_mask = pc.call_function(
            "less_equal",
            [price_col, pa.scalar(0)],
        )
        if pa.types.is_floating(price_col.type):
            nan_mask = pc.call_function("is_nan", [price_col])
            price_mask = pc.call_function("or_kleene", [price_mask, nan_mask])
        invalid_price += _count_true(price_mask)

        invalid_shares += _count_true(
            pc.call_function(
                "less_equal",
                [shares_col, pa.scalar(0)],
            )
        )
        invalid_order_ref += _count_true(
            pc.call_function(
                "less_equal",
                [order_ref_col, pa.scalar(0)],
            )
        )

        side_valid = pc.call_function(
            "is_in",
            [side_col],
            options=pc.SetLookupOptions(value_set=allowed),
        )
        side_invalid = pc.call_function(
            "invert",
            [pc.fill_null(side_valid, False)],
        )
        invalid_side += _count_true(side_invalid)

    has_failures = any(
        (
            null_critical > 0,
            invalid_price > 0,
            invalid_shares > 0,
            invalid_order_ref > 0,
            invalid_side > 0,
        )
    )

    elapsed = (time.perf_counter() - t0) * 1000
    if has_failures:
        detail = (
            f"rows={rows}, nulls={null_critical}, "
            f"price_invalid={invalid_price}, "
            f"shares_invalid={invalid_shares}, "
            f"order_ref_invalid={invalid_order_ref}, "
            f"side_invalid={invalid_side}"
        )
        return _record("trades_domain", CheckStatus.FAIL, detail, elapsed)

    return _record("trades_domain", CheckStatus.PASS, f"rows={rows}", elapsed)


def _check_trade_timestamps(trades_path: Path) -> CheckRecord:
    """Validate monotonic non-decreasing trade timestamps per file."""
    t0 = time.perf_counter()
    if not trades_path.exists():
        elapsed = (time.perf_counter() - t0) * 1000
        return _record(
            "trades_timestamp_order",
            CheckStatus.FAIL,
            f"dataset missing: {trades_path}",
            elapsed,
        )

    files = sorted(trades_path.rglob("*.parquet"))
    if not files:
        elapsed = (time.perf_counter() - t0) * 1000
        return _record(
            "trades_timestamp_order",
            CheckStatus.FAIL,
            "no parquet files found",
            elapsed,
        )

    violations: list[str] = []
    for file_path in files:
        parquet = pq.ParquetFile(file_path)
        last_ts: int | None = None
        file_has_violation = False

        for row_group_idx in range(parquet.num_row_groups):
            chunk = parquet.read_row_group(
                row_group_idx, columns=["timestamp"]
            )
            ts = chunk.column("timestamp").to_numpy(zero_copy_only=False)
            if ts.size == 0:
                continue

            ts_i64 = ts.astype(np.int64, copy=False)
            if np.any(np.diff(ts_i64) < 0):
                file_has_violation = True
                break

            first_ts = int(ts_i64[0])
            last_chunk_ts = int(ts_i64[-1])
            if last_ts is not None and first_ts < last_ts:
                file_has_violation = True
                break
            last_ts = last_chunk_ts

        if file_has_violation:
            rel = str(file_path.relative_to(trades_path))
            violations.append(rel)

    elapsed = (time.perf_counter() - t0) * 1000
    if violations:
        detail = f"violations={_fmt_list(violations)}"
        return _record(
            "trades_timestamp_order",
            CheckStatus.FAIL,
            detail,
            elapsed,
        )

    return _record(
        "trades_timestamp_order",
        CheckStatus.PASS,
        f"files_checked={len(files)}",
        elapsed,
    )


def _check_ohlcv_domain(ohlcv_path: Path) -> CheckRecord:
    """Validate OHLCV consistency constraints."""
    t0 = time.perf_counter()
    dataset = _dataset(ohlcv_path)
    if dataset is None:
        elapsed = (time.perf_counter() - t0) * 1000
        return _record(
            "ohlcv_domain",
            CheckStatus.FAIL,
            f"dataset missing: {ohlcv_path}",
            elapsed,
        )

    required = (
        "timestamp",
        "stock",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "trade_count",
    )
    schema_names = set(dataset.schema.names)
    missing = [name for name in required if name not in schema_names]
    if missing:
        elapsed = (time.perf_counter() - t0) * 1000
        return _record(
            "ohlcv_domain",
            CheckStatus.FAIL,
            f"missing columns: {_fmt_list(missing)}",
            elapsed,
        )

    scanner = dataset.scanner(columns=list(required), batch_size=_BATCH_SIZE)
    rows = 0
    null_critical = 0
    invalid_high_low = 0
    invalid_open_range = 0
    invalid_close_range = 0
    invalid_volume = 0
    invalid_trade_count = 0

    for batch in scanner.to_batches():
        rows += batch.num_rows
        timestamp_col = batch.column(batch.schema.get_field_index("timestamp"))
        stock_col = batch.column(batch.schema.get_field_index("stock"))
        open_col = batch.column(batch.schema.get_field_index("open"))
        high_col = batch.column(batch.schema.get_field_index("high"))
        low_col = batch.column(batch.schema.get_field_index("low"))
        close_col = batch.column(batch.schema.get_field_index("close"))
        volume_col = batch.column(batch.schema.get_field_index("volume"))
        count_col = batch.column(batch.schema.get_field_index("trade_count"))

        null_critical += timestamp_col.null_count
        null_critical += stock_col.null_count
        null_critical += open_col.null_count
        null_critical += high_col.null_count
        null_critical += low_col.null_count
        null_critical += close_col.null_count
        null_critical += volume_col.null_count
        null_critical += count_col.null_count

        invalid_high_low += _count_true(
            pc.call_function("less", [high_col, low_col])
        )

        open_outside = pc.call_function(
            "or_kleene",
            [
                pc.call_function("less", [open_col, low_col]),
                pc.call_function("greater", [open_col, high_col]),
            ],
        )
        invalid_open_range += _count_true(open_outside)

        close_outside = pc.call_function(
            "or_kleene",
            [
                pc.call_function("less", [close_col, low_col]),
                pc.call_function("greater", [close_col, high_col]),
            ],
        )
        invalid_close_range += _count_true(close_outside)

        invalid_volume += _count_true(
            pc.call_function("less", [volume_col, pa.scalar(0)])
        )
        invalid_trade_count += _count_true(
            pc.call_function("less", [count_col, pa.scalar(0)])
        )

    has_failures = any(
        (
            null_critical > 0,
            invalid_high_low > 0,
            invalid_open_range > 0,
            invalid_close_range > 0,
            invalid_volume > 0,
            invalid_trade_count > 0,
        )
    )
    elapsed = (time.perf_counter() - t0) * 1000

    if has_failures:
        detail = (
            f"rows={rows}, nulls={null_critical}, "
            f"high_low_invalid={invalid_high_low}, "
            f"open_range_invalid={invalid_open_range}, "
            f"close_range_invalid={invalid_close_range}, "
            f"volume_invalid={invalid_volume}, "
            f"trade_count_invalid={invalid_trade_count}"
        )
        return _record("ohlcv_domain", CheckStatus.FAIL, detail, elapsed)

    return _record("ohlcv_domain", CheckStatus.PASS, f"rows={rows}", elapsed)


def _check_snapshot_sanity(ctx: ContractContext) -> CheckRecord:
    """Validate best-level spread and sizes for book snapshots."""
    t0 = time.perf_counter()
    snapshots_path = ctx.base_dir / "book_snapshots"
    if not snapshots_path.exists():
        elapsed = (time.perf_counter() - t0) * 1000
        status = (
            CheckStatus.FAIL if ctx.require_snapshots else CheckStatus.WARN
        )
        return _record(
            "snapshot_sanity",
            status,
            "book_snapshots dataset not found",
            elapsed,
        )

    dataset = _dataset(snapshots_path)
    if dataset is None:
        elapsed = (time.perf_counter() - t0) * 1000
        return _record(
            "snapshot_sanity",
            CheckStatus.FAIL,
            "unable to open book_snapshots dataset",
            elapsed,
        )

    names = set(dataset.schema.names)
    missing = [name for name in _SNAPSHOT_REQUIRED if name not in names]
    if missing:
        elapsed = (time.perf_counter() - t0) * 1000
        status = (
            CheckStatus.FAIL if ctx.require_snapshots else CheckStatus.WARN
        )
        return _record(
            "snapshot_sanity",
            status,
            f"missing columns: {_fmt_list(missing)}",
            elapsed,
        )

    scanner = dataset.scanner(
        columns=list(_SNAPSHOT_REQUIRED),
        batch_size=_BATCH_SIZE,
    )
    rows = 0
    crossed_book = 0
    invalid_bid_size = 0
    invalid_ask_size = 0

    for batch in scanner.to_batches():
        rows += batch.num_rows
        bid_price = batch.column(batch.schema.get_field_index("bid_price_0"))
        ask_price = batch.column(batch.schema.get_field_index("ask_price_0"))
        bid_size = batch.column(batch.schema.get_field_index("bid_size_0"))
        ask_size = batch.column(batch.schema.get_field_index("ask_size_0"))

        crossed_book += _count_true(
            pc.call_function("less", [ask_price, bid_price])
        )
        invalid_bid_size += _count_true(
            pc.call_function("less", [bid_size, pa.scalar(0)])
        )
        invalid_ask_size += _count_true(
            pc.call_function("less", [ask_size, pa.scalar(0)])
        )

    has_failures = any(
        (
            crossed_book > 0,
            invalid_bid_size > 0,
            invalid_ask_size > 0,
        )
    )
    elapsed = (time.perf_counter() - t0) * 1000
    if has_failures:
        detail = (
            f"rows={rows}, crossed_book={crossed_book}, "
            f"invalid_bid_size={invalid_bid_size}, "
            f"invalid_ask_size={invalid_ask_size}"
        )
        return _record("snapshot_sanity", CheckStatus.FAIL, detail, elapsed)

    return _record(
        "snapshot_sanity", CheckStatus.PASS, f"rows={rows}", elapsed
    )


def _count_rows(dataset_path: Path) -> int:
    """Count rows of one dataset, returning zero on load failure."""
    dataset = _dataset(dataset_path)
    if dataset is None:
        return 0
    try:
        return int(dataset.count_rows())
    except Exception:
        return 0


def _check_quarantine_reason_codes(ctx: ContractContext) -> CheckRecord:
    """Validate quarantine reasons against contract reason-code list."""
    t0 = time.perf_counter()

    if not ctx.allowed_quarantine_reasons:
        elapsed = (time.perf_counter() - t0) * 1000
        status = (
            CheckStatus.FAIL
            if ctx.strict_quarantine_reasons
            else CheckStatus.WARN
        )
        return _record(
            "quarantine_reason_codes",
            status,
            "no allowed quarantine reason codes configured",
            elapsed,
        )

    quarantine_root = ctx.base_dir / "quarantine"
    if not quarantine_root.exists():
        elapsed = (time.perf_counter() - t0) * 1000
        return _record(
            "quarantine_reason_codes",
            CheckStatus.PASS,
            "quarantine dataset not present",
            elapsed,
        )

    category_dirs = [
        path for path in sorted(quarantine_root.iterdir()) if path.is_dir()
    ]
    missing_reason_column: list[str] = []
    unknown_reasons: set[str] = set()
    rows_scanned = 0

    for category_dir in category_dirs:
        dataset = _dataset(category_dir)
        if dataset is None:
            continue

        if "quarantine_reason" not in dataset.schema.names:
            missing_reason_column.append(category_dir.name)
            continue

        scanner = dataset.scanner(
            columns=["quarantine_reason"],
            batch_size=_BATCH_SIZE,
        )
        for batch in scanner.to_batches():
            rows_scanned += batch.num_rows
            reason_col = batch.column(
                batch.schema.get_field_index("quarantine_reason")
            )
            normalized = pc.cast(
                pc.fill_null(reason_col, ""),
                pa.string(),
            )
            unique_reasons = pc.call_function(
                "unique", [normalized]
            ).to_pylist()
            for reason in unique_reasons:
                reason_text = str(reason).strip()
                if not reason_text:
                    continue
                if reason_text not in ctx.allowed_quarantine_reasons:
                    unknown_reasons.add(reason_text)

    elapsed = (time.perf_counter() - t0) * 1000
    if missing_reason_column or unknown_reasons:
        status = (
            CheckStatus.FAIL
            if ctx.strict_quarantine_reasons
            else CheckStatus.WARN
        )
        detail = (
            f"missing_column={_fmt_list(sorted(missing_reason_column))}; "
            f"unknown_codes={_fmt_list(sorted(unknown_reasons))}; "
            f"rows_scanned={rows_scanned}"
        )
        return _record("quarantine_reason_codes", status, detail, elapsed)

    detail = (
        f"rows_scanned={rows_scanned}, "
        f"allowed_codes={len(ctx.allowed_quarantine_reasons)}"
    )
    return _record(
        "quarantine_reason_codes", CheckStatus.PASS, detail, elapsed
    )


def _check_quarantine_budget(ctx: ContractContext) -> CheckRecord:
    """Validate quarantine ratio against allowed budget."""
    t0 = time.perf_counter()
    trades_rows = _count_rows(ctx.base_dir / "trades")
    quarantine_root = ctx.base_dir / "quarantine"

    category_rows: dict[str, int] = {}
    if quarantine_root.exists():
        for category_dir in sorted(quarantine_root.iterdir()):
            if not category_dir.is_dir():
                continue
            category_rows[category_dir.name] = _count_rows(category_dir)

    quarantine_rows = sum(category_rows.values())
    ratio = 0.0
    if trades_rows > 0:
        ratio = quarantine_rows / trades_rows

    elapsed = (time.perf_counter() - t0) * 1000
    if ratio > ctx.max_quarantine_ratio:
        detail = (
            f"ratio={ratio:.6f} > max={ctx.max_quarantine_ratio:.6f}, "
            f"trades_rows={trades_rows}, quarantine_rows={quarantine_rows}, "
            f"categories={category_rows}"
        )
        return _record(
            "quarantine_budget",
            CheckStatus.FAIL,
            detail,
            elapsed,
        )

    detail = (
        f"ratio={ratio:.6f}, trades_rows={trades_rows}, "
        f"quarantine_rows={quarantine_rows}"
    )
    return _record("quarantine_budget", CheckStatus.PASS, detail, elapsed)


def run_contract_gate(ctx: ContractContext) -> ValidationReport:
    """Execute all contract checks."""
    report = ValidationReport()
    report.add(_check_contract_configuration(ctx))
    report.add(
        _check_schema(
            check_name="trades_schema",
            dataset_path=ctx.base_dir / "trades",
            expected_schema=TRADE_SCHEMA,
            required_fields=tuple(field.name for field in TRADE_SCHEMA),
            require_non_empty=True,
        )
    )
    report.add(_check_trades_domain(ctx.base_dir / "trades"))
    report.add(_check_trade_timestamps(ctx.base_dir / "trades"))
    report.add(
        _check_schema(
            check_name="ohlcv_schema",
            dataset_path=ctx.base_dir / "ohlcv",
            expected_schema=OHLCV_SCHEMA,
            required_fields=tuple(field.name for field in OHLCV_SCHEMA),
            require_non_empty=True,
        )
    )
    report.add(_check_ohlcv_domain(ctx.base_dir / "ohlcv"))
    report.add(_check_snapshot_sanity(ctx))
    report.add(_check_quarantine_reason_codes(ctx))
    report.add(_check_quarantine_budget(ctx))
    return report


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Validate ETL data contract before ML training",
    )
    parser.add_argument(
        "--base",
        default=str(_PROJECT_ROOT / "data" / "processed" / "itch"),
        help="Base processed directory",
    )
    parser.add_argument(
        "--max-quarantine-ratio",
        type=float,
        default=None,
        help=(
            "Maximum allowed quarantine/trades ratio. "
            "When omitted, uses contract_thresholds.max_quarantine_ratio."
        ),
    )
    parser.add_argument(
        "--require-snapshots",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Whether missing book snapshots fail the gate. "
            "When omitted, uses contract_thresholds.require_snapshots."
        ),
    )
    parser.add_argument(
        "--contract",
        default=str(_DEFAULT_CONTRACT_PATH),
        help="Path to Nasdaq ITCH ETL contract YAML.",
    )
    parser.add_argument(
        "--strict-quarantine-reasons",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=("Fail when quarantine_reason contains unknown reason codes."),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show per-check timing in text output",
    )
    args = parser.parse_args()

    contract_path = Path(args.contract).resolve()
    contract_mapping: dict[str, Any] = {}
    contract_error: str | None = None
    if contract_path.exists():
        try:
            contract_mapping = load_yaml_mapping(contract_path)
        except Exception as exc:
            contract_error = f"failed to load contract: {exc}"
    else:
        contract_error = f"contract file not found: {contract_path}"

    contract_max_ratio, contract_require_snapshots = (
        _extract_contract_thresholds(contract_mapping)
    )
    max_quarantine_ratio = (
        float(args.max_quarantine_ratio)
        if args.max_quarantine_ratio is not None
        else contract_max_ratio
    )
    require_snapshots = (
        bool(args.require_snapshots)
        if args.require_snapshots is not None
        else contract_require_snapshots
    )

    context = ContractContext(
        base_dir=Path(args.base),
        max_quarantine_ratio=max_quarantine_ratio,
        require_snapshots=require_snapshots,
        verbose=bool(args.verbose),
        contract_path=contract_path,
        allowed_quarantine_reasons=_extract_allowed_quarantine_reasons(
            contract_mapping
        ),
        strict_quarantine_reasons=bool(args.strict_quarantine_reasons),
        contract_load_error=contract_error,
    )
    report = run_contract_gate(context)

    if args.json:
        output = report.to_dict()
        output["base_dir"] = str(context.base_dir)
        output["max_quarantine_ratio"] = context.max_quarantine_ratio
        output["require_snapshots"] = context.require_snapshots
        output["contract_path"] = str(context.contract_path)
        output["strict_quarantine_reasons"] = context.strict_quarantine_reasons
        print(json.dumps(output, indent=2, default=str))
    else:
        print(_summary(report, verbose=context.verbose))

    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
