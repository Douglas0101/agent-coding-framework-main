#!/usr/bin/env python3
"""ITCH Pipeline environment validation.

Hexagonal shape used here:
  - domain: CheckStatus, CheckRecord, ValidationReport
  - application: run_validation orchestrator
  - adapters: concrete environment checks + CLI output
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import shutil
import struct
import sys
import time
from dataclasses import dataclass
from pathlib import Path


_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from src.skill_hex_core import (  # noqa: E402
    CheckRecord,
    CheckStatus,
    ValidationReport,
    load_yaml_mapping,
)


_MIN_DISK_GB = 10
_REQUIRED_PACKAGES = (
    "numpy",
    "pandas",
    "pyarrow",
    "sortedcontainers",
    "yaml",  # pyyaml
    "structlog",
    "tqdm",
    "pytest",
)
_REQUIRED_CONFIG_KEYS: dict[str, tuple[str, ...]] = {
    "paths": ("raw_dir", "processed_dir", "interim_dir"),
    "parser": ("chunk_size_mb", "skip_unknown_types"),
    "pipeline": ("max_workers", "queue_maxsize", "gc_interval"),
    "order_book": ("snapshot_interval_ms", "depth"),
    "features": ("vpin_buckets", "volatility_window", "ohlcv_freq"),
    "storage": ("compression", "compression_level", "row_group_size"),
    "engine": (
        "mode",
        "fallback_to_python",
        "module_name",
        "shared_library_path",
    ),
}


def _summary(report: ValidationReport, *, verbose: bool = False) -> str:
    """Human-readable summary string."""
    icons = {
        CheckStatus.PASS: "✅",
        CheckStatus.FAIL: "❌",
        CheckStatus.WARN: "⚠️",
    }
    lines: list[str] = []
    for record in report.checks:
        detail = f" - {record.detail}" if record.detail else ""
        timing = f" [{record.elapsed_ms:.1f}ms]" if verbose else ""
        icon = icons[record.status]
        lines.append(f"  {icon}  {record.check}{detail}{timing}")

    header = (
        "🟢 ALL CHECKS PASSED" if report.passed else "🔴 VALIDATION FAILED"
    )
    return f"\n{header}\n" + "\n".join(lines) + "\n"


@dataclass(slots=True)
class ValidationContext:
    """Application context passed into checks."""

    project_root: Path
    min_disk_gb: int
    verbose: bool


def _record(
    check: str,
    status: CheckStatus,
    detail: str,
    elapsed_ms: float,
) -> CheckRecord:
    """Create a normalized check record."""
    return CheckRecord(
        check=check,
        status=status,
        detail=detail,
        elapsed_ms=round(elapsed_ms, 1),
    )


def _check_python_version(_: ValidationContext) -> list[CheckRecord]:
    """Validate Python runtime version."""
    t0 = time.perf_counter()
    major, minor = sys.version_info[:2]
    elapsed = (time.perf_counter() - t0) * 1000
    if (major, minor) < (3, 14):
        return [
            _record(
                "python_version",
                CheckStatus.FAIL,
                (
                    f"Python {major}.{minor} < 3.14 "
                    "(required by project tooling and LSP baseline)"
                ),
                elapsed,
            )
        ]
    return [
        _record(
            "python_version",
            CheckStatus.PASS,
            f"Python {major}.{minor}",
            elapsed,
        )
    ]


def _check_dependencies(ctx: ValidationContext) -> list[CheckRecord]:
    """Validate required packages and optional versions."""
    t0 = time.perf_counter()
    missing: list[str] = []
    versions: dict[str, str] = {}

    for package in _REQUIRED_PACKAGES:
        try:
            module = importlib.import_module(package)
            if ctx.verbose:
                version = getattr(
                    module,
                    "__version__",
                    getattr(module, "VERSION", "?"),
                )
                versions[package] = str(version)
        except ImportError:
            missing.append(package)

    elapsed = (time.perf_counter() - t0) * 1000
    if missing:
        return [
            _record(
                "dependencies",
                CheckStatus.FAIL,
                f"Missing: {', '.join(missing)}",
                elapsed,
            )
        ]

    detail = f"{len(_REQUIRED_PACKAGES)} packages OK"
    if ctx.verbose and versions:
        versions_detail = ", ".join(
            f"{pkg}={version}" for pkg, version in versions.items()
        )
        detail = f"{detail} ({versions_detail})"

    return [_record("dependencies", CheckStatus.PASS, detail, elapsed)]


def _check_protocol_integrity(_: ValidationContext) -> list[CheckRecord]:
    """Validate protocol struct declared sizes."""
    t0 = time.perf_counter()
    try:
        from src.data.itch.protocol import MESSAGE_SPECS
    except ImportError as exc:
        elapsed = (time.perf_counter() - t0) * 1000
        return [
            _record(
                "protocol_integrity",
                CheckStatus.FAIL,
                f"Cannot import protocol: {exc}",
                elapsed,
            )
        ]

    mismatches: list[str] = []
    for msg_type, (fmt, _fields, declared) in sorted(MESSAGE_SPECS.items()):
        actual = struct.calcsize(fmt)
        if actual != declared:
            mismatches.append(
                f"Type {msg_type}: struct={actual}, declared={declared}"
            )

    elapsed = (time.perf_counter() - t0) * 1000
    if mismatches:
        return [
            _record(
                "protocol_integrity",
                CheckStatus.FAIL,
                "; ".join(mismatches),
                elapsed,
            )
        ]

    return [
        _record(
            "protocol_integrity",
            CheckStatus.PASS,
            f"{len(MESSAGE_SPECS)} message types OK",
            elapsed,
        )
    ]


def _check_pyarrow(_: ValidationContext) -> list[CheckRecord]:
    """Validate pyarrow version and basic schema creation."""
    t0 = time.perf_counter()
    try:
        import pyarrow as pa
    except ImportError:
        elapsed = (time.perf_counter() - t0) * 1000
        return [
            _record(
                "pyarrow_compat",
                CheckStatus.FAIL,
                "pyarrow not installed",
                elapsed,
            )
        ]

    version = tuple(int(x) for x in pa.__version__.split(".")[:2])
    if version < (14, 0):
        elapsed = (time.perf_counter() - t0) * 1000
        return [
            _record(
                "pyarrow_compat",
                CheckStatus.FAIL,
                f"Version {pa.__version__} < 14.0 (required)",
                elapsed,
            )
        ]

    try:
        schema = pa.schema([pa.field("test", pa.uint64())])
        assert schema is not None
    except Exception as exc:
        elapsed = (time.perf_counter() - t0) * 1000
        return [
            _record(
                "pyarrow_compat",
                CheckStatus.FAIL,
                f"Schema creation failed: {exc}",
                elapsed,
            )
        ]

    elapsed = (time.perf_counter() - t0) * 1000
    return [
        _record(
            "pyarrow_compat",
            CheckStatus.PASS,
            f"v{pa.__version__}",
            elapsed,
        )
    ]


def _load_config(project_root: Path) -> dict[str, object]:
    """Load config YAML with dynamic adapter import."""
    config_path = project_root / "config" / "itch_pipeline.yml"
    return load_yaml_mapping(config_path)


def _check_config(ctx: ValidationContext) -> list[CheckRecord]:
    """Validate config structure and required keys."""
    t0 = time.perf_counter()
    config_path = ctx.project_root / "config" / "itch_pipeline.yml"
    if not config_path.exists():
        elapsed = (time.perf_counter() - t0) * 1000
        return [
            _record(
                "config_schema",
                CheckStatus.FAIL,
                f"Config not found: {config_path}",
                elapsed,
            )
        ]

    try:
        cfg = _load_config(ctx.project_root)
    except Exception as exc:
        elapsed = (time.perf_counter() - t0) * 1000
        return [
            _record(
                "config_schema",
                CheckStatus.FAIL,
                f"YAML parse error: {exc}",
                elapsed,
            )
        ]

    missing: list[str] = []
    for section, keys in _REQUIRED_CONFIG_KEYS.items():
        section_data = cfg.get(section)
        if not isinstance(section_data, dict):
            missing.append(section)
            continue
        for key in keys:
            if key not in section_data:
                missing.append(f"{section}.{key}")

    if "tickers" not in cfg:
        missing.append("tickers")

    elapsed = (time.perf_counter() - t0) * 1000
    if missing:
        return [
            _record(
                "config_schema",
                CheckStatus.FAIL,
                f"Missing keys: {', '.join(missing)}",
                elapsed,
            )
        ]

    return [
        _record(
            "config_schema",
            CheckStatus.PASS,
            str(config_path.relative_to(ctx.project_root)),
            elapsed,
        )
    ]


def _check_directories(ctx: ValidationContext) -> list[CheckRecord]:
    """Validate data directories and disk space."""
    t0 = time.perf_counter()
    try:
        cfg = _load_config(ctx.project_root)
        paths = cfg.get("paths", {})
        if not isinstance(paths, dict):
            raise ValueError("invalid paths section")
        raw_dir = ctx.project_root / str(paths["raw_dir"])
        processed_dir = ctx.project_root / str(paths["processed_dir"])
    except Exception:
        raw_dir = ctx.project_root / "data" / "raw"
        processed_dir = ctx.project_root / "data" / "processed" / "itch"

    issues: list[str] = []
    for label, directory in (
        ("raw_dir", raw_dir),
        ("processed_dir", processed_dir),
    ):
        if not directory.exists():
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                issues.append(f"Cannot create {label}: {exc}")
                continue

        if not os.access(directory, os.R_OK):
            issues.append(f"{label} not readable")
        if label == "processed_dir" and not os.access(directory, os.W_OK):
            issues.append(f"{label} not writable")

    elapsed = (time.perf_counter() - t0) * 1000
    records: list[CheckRecord] = []
    if issues:
        records.append(
            _record(
                "directories",
                CheckStatus.FAIL,
                "; ".join(issues),
                elapsed,
            )
        )
    else:
        records.append(
            _record(
                "directories",
                CheckStatus.PASS,
                "raw + processed dirs OK",
                elapsed,
            )
        )

    t1 = time.perf_counter()
    try:
        usage = shutil.disk_usage(str(processed_dir))
        free_gb = usage.free / (1024**3)
        elapsed_disk = (time.perf_counter() - t1) * 1000
        if free_gb < ctx.min_disk_gb:
            records.append(
                _record(
                    "disk_space",
                    CheckStatus.WARN,
                    (
                        f"{free_gb:.1f} GB free < {ctx.min_disk_gb} GB "
                        "recommended (ITCH files are ~5 GB each)"
                    ),
                    elapsed_disk,
                )
            )
        else:
            records.append(
                _record(
                    "disk_space",
                    CheckStatus.PASS,
                    f"{free_gb:.1f} GB free",
                    elapsed_disk,
                )
            )
    except Exception:
        elapsed_disk = (time.perf_counter() - t1) * 1000
        records.append(
            _record(
                "disk_space",
                CheckStatus.WARN,
                "Could not determine free disk space",
                elapsed_disk,
            )
        )

    return records


def _check_quality_tools(_: ValidationContext) -> list[CheckRecord]:
    """Validate quality tool availability."""
    t0 = time.perf_counter()
    missing: list[str] = []
    for tool in ("ruff", "mypy", "basedpyright"):
        if shutil.which(tool) is None:
            try:
                importlib.import_module(tool)
            except ImportError:
                missing.append(tool)

    elapsed = (time.perf_counter() - t0) * 1000
    if missing:
        return [
            _record(
                "quality_tools",
                CheckStatus.WARN,
                (
                    f"Not found: {', '.join(missing)} "
                    "(quality gate will skip these stages)"
                ),
                elapsed,
            )
        ]
    return [
        _record(
            "quality_tools",
            CheckStatus.PASS,
            "ruff + mypy + basedpyright available",
            elapsed,
        )
    ]


def run_validation(ctx: ValidationContext) -> ValidationReport:
    """Application use-case for executing validation checks."""
    report = ValidationReport()
    checks = (
        _check_python_version,
        _check_dependencies,
        _check_protocol_integrity,
        _check_pyarrow,
        _check_config,
        _check_directories,
        _check_quality_tools,
    )
    for check in checks:
        report.add_many(check(ctx))
    return report


def main() -> int:
    """CLI adapter entrypoint."""
    parser = argparse.ArgumentParser(
        description="ITCH Pipeline environment validator"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show package versions and per-check timing",
    )
    args = parser.parse_args()

    context = ValidationContext(
        project_root=_PROJECT_ROOT,
        min_disk_gb=_MIN_DISK_GB,
        verbose=args.verbose,
    )
    report = run_validation(context)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, default=str))
    else:
        print(_summary(report, verbose=args.verbose))

    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
