#!/usr/bin/env python3
"""ITCH Pipeline — Performance Benchmark.

Measures throughput and resource usage for the pipeline stages:
  1. Protocol decoding speed (messages/second)
  2. Order book operation speed (events/second)
  3. Parquet write throughput (rows/second)
  4. C++ frame scanner throughput (optional, requires input file)
  5. C++ decoder throughput (optional, requires input file)
  6. Memory peak during parsing (optional, requires input file)

Usage:
    python .agent/skills/itch-pipeline/scripts/benchmark.py
    python .agent/skills/itch-pipeline/scripts/benchmark.py \
        --input data/raw/FILE
    python .agent/skills/itch-pipeline/scripts/benchmark.py \
        --config config/itch_pipeline.yml
    python .agent/skills/itch-pipeline/scripts/benchmark.py --json
"""

from __future__ import annotations

import argparse
import gc
import json
import struct
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path


_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from src.skill_hex_core import (  # noqa: E402
    JsonMap,
    load_yaml_mapping,
    to_int,
    to_str_map,
)


# ── Performance targets from SKILL.md §7 ─────
_TARGETS = {
    "protocol_decode": {"messages_per_sec": 2_000_000, "label": "Parse speed"},
    "order_book": {"events_per_sec": 2_000_000, "label": "Book operations"},
    "parquet_write": {"rows_per_sec": 500_000, "label": "Parquet write"},
    "cpp_frame_scan": {
        "messages_per_sec": 200_000,
        "label": "C++ frame scanner",
    },
    "cpp_decode": {
        "messages_per_sec": 100_000,
        "label": "C++ decoder",
    },
    "parsing_memory": {"peak_memory_mb": 4096, "label": "Memory peak"},
}

_WARMUP_FRACTION = 0.1  # 10% of iterations used for warm-up


def _target_int(stage: str, metric: str) -> int:
    """Read an integer target from target catalog."""
    stage_cfg = to_str_map(_TARGETS.get(stage, {}))
    raw = stage_cfg.get(metric)
    target = to_int(raw, default=-1)
    if target >= 0:
        return target
    raise ValueError(f"Invalid target {stage}.{metric}: {raw!r}")


def _load_storage_config(
    config_path: str,
    *,
    compression: str,
    compression_level: int,
    row_group_size: int,
) -> tuple[str, int, int]:
    """Load storage tuning values from YAML config safely."""
    try:
        cfg = load_yaml_mapping(Path(config_path))
        storage = to_str_map(cfg.get("storage"))
        loaded_compression = storage.get("compression", compression)
        loaded_level = storage.get("compression_level", compression_level)
        loaded_row_group = storage.get("row_group_size", row_group_size)
        if isinstance(loaded_compression, str):
            compression = loaded_compression
        compression_level = to_int(loaded_level, default=compression_level)
        row_group_size = to_int(loaded_row_group, default=row_group_size)
    except Exception:  # noqa: S110
        pass
    return compression, compression_level, row_group_size


def _benchmark_protocol_decoding(n_iterations: int = 500_000) -> JsonMap:
    """Benchmark raw struct unpacking speed for Add Order (type A)."""
    from src.data.itch.protocol import MESSAGE_SPECS, decode_message

    fmt = MESSAGE_SPECS["A"][0]
    # Construct a valid payload
    payload = struct.pack(
        fmt,
        1,  # stock_locate
        0,  # tracking_number
        b"\x00" * 6,  # timestamp_raw
        12345,  # order_ref
        b"B",  # buy_sell
        100,  # shares
        b"AAPL    ",  # stock
        1500000,  # price (150.0000 in fixed-point)
    )

    # Warm-up phase (excluded from timing)
    warmup_n = max(1, int(n_iterations * _WARMUP_FRACTION))
    for _ in range(warmup_n):
        decode_message("A", payload)

    gc.disable()
    t0 = time.perf_counter()
    for _ in range(n_iterations):
        decode_message("A", payload)
    elapsed = time.perf_counter() - t0
    gc.enable()

    msgs_per_sec = round(n_iterations / elapsed)
    target = _target_int("protocol_decode", "messages_per_sec")
    status = "ABOVE_TARGET" if msgs_per_sec >= target else "BELOW_TARGET"

    return {
        "stage": "protocol_decode",
        "iterations": n_iterations,
        "warmup": warmup_n,
        "elapsed_s": round(elapsed, 4),
        "messages_per_sec": msgs_per_sec,
        "target_per_sec": target,
        "vs_target": status,
    }


def _benchmark_order_book(n_events: int = 200_000) -> JsonMap:
    """Benchmark order book add/delete cycle."""
    import numpy as np

    from src.data.itch.order_book import OrderBook

    book = OrderBook("BENCH", depth=10)

    # Pre-generate messages
    adds = [
        {
            "message_type": "A",
            "order_ref": i,
            "buy_sell": "B" if i % 2 == 0 else "S",
            "price": 150.0 + (i % 100) * 0.01,
            "shares": 100,
            "timestamp": np.uint64(i * 1_000_000),
        }
        for i in range(n_events)
    ]
    deletes = [
        {
            "message_type": "D",
            "order_ref": i,
        }
        for i in range(n_events)
    ]

    # Warm-up
    warmup_book = OrderBook("WARMUP", depth=10)
    warmup_n = max(1, int(n_events * _WARMUP_FRACTION))
    for warmup_msg in adds[:warmup_n]:
        warmup_book.process_message(warmup_msg)
    del warmup_book

    gc.disable()
    t0 = time.perf_counter()
    for add_msg in adds:
        book.process_message(add_msg)
    for delete_msg in deletes:
        book.process_message(delete_msg)
    elapsed = time.perf_counter() - t0
    gc.enable()

    total_ops = n_events * 2  # add + delete
    events_per_sec = round(total_ops / elapsed)
    target = _target_int("order_book", "events_per_sec")
    status = "ABOVE_TARGET" if events_per_sec >= target else "BELOW_TARGET"

    return {
        "stage": "order_book",
        "operations": total_ops,
        "warmup": warmup_n,
        "elapsed_s": round(elapsed, 4),
        "events_per_sec": events_per_sec,
        "target_per_sec": target,
        "vs_target": status,
    }


def _benchmark_parquet_write(
    n_rows: int = 500_000,
    compression: str = "zstd",
    compression_level: int = 3,
    row_group_size: int = 131_072,
) -> JsonMap:
    """Benchmark Parquet write throughput with Zstd compression."""
    import numpy as np
    import pandas as pd

    # Generate synthetic trade-like data
    df = pd.DataFrame(
        {
            "timestamp": np.arange(n_rows, dtype=np.uint64) * 1_000_000,
            "stock": "AAPL",
            "price": np.random.default_rng(42).normal(150.0, 2.0, n_rows),
            "shares": np.random.default_rng(42).integers(1, 1000, n_rows),
            "order_ref": np.arange(n_rows, dtype=np.uint64),
            "match_number": np.arange(n_rows, dtype=np.uint64),
            "buy_sell": np.where(np.arange(n_rows) % 2 == 0, "B", "S"),
        }
    )

    import pyarrow as pa
    import pyarrow.parquet as pq

    table = pa.Table.from_pandas(df, preserve_index=False)

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "bench.parquet"

        gc.disable()
        t0 = time.perf_counter()
        pq.write_table(
            table,
            out_path,
            compression=compression,
            compression_level=compression_level,
            row_group_size=row_group_size,
        )
        elapsed = time.perf_counter() - t0
        gc.enable()

        file_size_mb = round(out_path.stat().st_size / 1e6, 2)

    rows_per_sec = round(n_rows / elapsed)
    target = _target_int("parquet_write", "rows_per_sec")
    status = "ABOVE_TARGET" if rows_per_sec >= target else "BELOW_TARGET"

    return {
        "stage": "parquet_write",
        "rows": n_rows,
        "compression": compression,
        "compression_level": compression_level,
        "elapsed_s": round(elapsed, 4),
        "rows_per_sec": rows_per_sec,
        "file_size_mb": file_size_mb,
        "target_per_sec": target,
        "vs_target": status,
    }


def _benchmark_parsing_memory(file_path: Path | None) -> JsonMap:
    """Measure memory usage during file parsing (if file available)."""
    if file_path is None or not file_path.exists():
        return {
            "stage": "parsing_memory",
            "skipped": True,
            "reason": "No input file provided or file not found",
        }

    from src.data.itch.parser import ITCHParser

    tracemalloc.start()
    parser = ITCHParser(file_path, show_progress=False)

    t0 = time.perf_counter()
    msg_count = 0
    for _ in parser.parse_file():
        msg_count += 1
    elapsed = time.perf_counter() - t0

    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    peak_mb = round(peak_bytes / 1e6, 2)
    target = _target_int("parsing_memory", "peak_memory_mb")
    status = "ABOVE_TARGET" if peak_mb <= target else "BELOW_TARGET"

    return {
        "stage": "parsing_memory",
        "file": str(file_path),
        "messages": msg_count,
        "elapsed_s": round(elapsed, 4),
        "messages_per_sec": round(msg_count / elapsed) if elapsed > 0 else 0,
        "peak_memory_mb": peak_mb,
        "target_memory_mb": target,
        "vs_target": status,
    }


def _benchmark_cpp_frame_scan(file_path: Path | None) -> JsonMap:
    """Benchmark C++ mmap frame scanner via ctypes backend."""
    if file_path is None or not file_path.exists():
        return {
            "stage": "cpp_frame_scan",
            "skipped": True,
            "reason": "No input file provided or file not found",
        }

    from src.data.itch.cpp_adapter import CppEngineAdapter

    adapter = CppEngineAdapter()
    if not adapter.scanner_available:
        return {
            "stage": "cpp_frame_scan",
            "skipped": True,
            "reason": (
                "C++ shared scanner unavailable; build via "
                "scripts/build_cpp_engine_shared.sh"
            ),
        }

    # Warm-up
    adapter.scan_frames(input_path=str(file_path))

    t0 = time.perf_counter()
    scan = adapter.scan_frames(input_path=str(file_path))
    elapsed = time.perf_counter() - t0

    raw_messages = scan.get("messages", 0)
    messages = raw_messages if isinstance(raw_messages, int) else 0
    raw_malformed = scan.get("malformed_frames", 0)
    malformed = raw_malformed if isinstance(raw_malformed, int) else 0
    throughput = round(messages / elapsed) if elapsed > 0 else 0

    target = _target_int("cpp_frame_scan", "messages_per_sec")
    status = (
        "ABOVE_TARGET"
        if throughput >= target and malformed == 0
        else "BELOW_TARGET"
    )

    return {
        "stage": "cpp_frame_scan",
        "file": str(file_path),
        "messages": messages,
        "elapsed_s": round(elapsed, 4),
        "messages_per_sec": throughput,
        "malformed_frames": malformed,
        "target_per_sec": target,
        "vs_target": status,
        "backend": scan.get("backend", "unknown"),
    }


def _benchmark_cpp_decode(file_path: Path | None) -> JsonMap:
    """Benchmark C++ decoder over supported ITCH message types."""
    if file_path is None or not file_path.exists():
        return {
            "stage": "cpp_decode",
            "skipped": True,
            "reason": "No input file provided or file not found",
        }

    from src.data.itch.cpp_adapter import CppEngineAdapter

    adapter = CppEngineAdapter()
    if not adapter.decode_available:
        return {
            "stage": "cpp_decode",
            "skipped": True,
            "reason": "C++ decode API unavailable in shared library",
        }

    # Warm-up
    adapter.decode_file_stats(input_path=str(file_path))

    t0 = time.perf_counter()
    decoded = adapter.decode_file_stats(input_path=str(file_path))
    elapsed = time.perf_counter() - t0

    raw_messages = decoded.get("messages_total", 0)
    messages = raw_messages if isinstance(raw_messages, int) else 0
    raw_decoded = decoded.get("decoded_messages", 0)
    decoded_messages = raw_decoded if isinstance(raw_decoded, int) else 0
    raw_malformed = decoded.get("malformed_frames", 0)
    malformed = raw_malformed if isinstance(raw_malformed, int) else 0

    throughput = round(messages / elapsed) if elapsed > 0 else 0
    target = _target_int("cpp_decode", "messages_per_sec")
    status = (
        "ABOVE_TARGET"
        if throughput >= target and malformed == 0
        else "BELOW_TARGET"
    )

    return {
        "stage": "cpp_decode",
        "file": str(file_path),
        "messages_total": messages,
        "decoded_messages": decoded_messages,
        "elapsed_s": round(elapsed, 4),
        "messages_per_sec": throughput,
        "malformed_frames": malformed,
        "target_per_sec": target,
        "vs_target": status,
        "backend": decoded.get("backend", "unknown"),
        "digest": decoded.get("digest", 0),
    }


def _format_vs_target(status: str) -> str:
    """Return colored target comparison string."""
    if status == "ABOVE_TARGET":
        return "✅ ABOVE TARGET"
    return "⚠️  BELOW TARGET"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ITCH Pipeline performance benchmark"
    )
    parser.add_argument(
        "--input",
        default=None,
        help="Path to ITCH file for parsing benchmark (optional)",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Pipeline config YAML for storage params (optional)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="JSON output",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=500_000,
        help="Protocol decode iterations (default: 500000)",
    )
    args = parser.parse_args()

    # Load storage params from config if provided
    compression = "zstd"
    compression_level = 3
    row_group_size = 131_072

    if args.config:
        compression, compression_level, row_group_size = _load_storage_config(
            args.config,
            compression=compression,
            compression_level=compression_level,
            row_group_size=row_group_size,
        )

    results: list[JsonMap] = []

    # 1. Protocol decode
    results.append(_benchmark_protocol_decoding(args.iterations))

    # 2. Order book
    results.append(_benchmark_order_book())

    # 3. Parquet write (NEW)
    results.append(
        _benchmark_parquet_write(
            compression=compression,
            compression_level=compression_level,
            row_group_size=row_group_size,
        )
    )

    # 4. C++ frame scan (optional)
    input_path = Path(args.input) if args.input else None
    results.append(_benchmark_cpp_frame_scan(input_path))

    # 5. C++ decode (optional)
    results.append(_benchmark_cpp_decode(input_path))

    # 6. Parsing memory (optional)
    results.append(_benchmark_parsing_memory(input_path))

    if args.json:
        print(json.dumps({"benchmarks": results}, indent=2))
    else:
        print("\n" + "=" * 60)
        print("  ITCH Pipeline — Performance Benchmark")
        print("=" * 60)
        for r in results:
            stage = str(r.get("stage", "unknown"))
            if r.get("skipped"):
                print(f"\n  ⏭  {stage}: skipped ({r.get('reason', '')})")
                continue

            vs = str(r.get("vs_target", ""))
            vs_str = f"  {_format_vs_target(vs)}" if vs else ""
            print(f"\n  🔬 {stage}{vs_str}")

            for k, v in r.items():
                if k in ("stage", "vs_target"):
                    continue
                label = k.replace("_", " ").title()
                print(
                    f"     {label}: {v:,}"
                    if isinstance(v, int)
                    else f"     {label}: {v}"
                )
        print("\n" + "=" * 60 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
