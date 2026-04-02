#!/usr/bin/env python3
"""DBA governance checker for SQL artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


SEVERITY_ORDER = ("critical", "high", "medium", "low", "info")
DEFAULT_REPORT_JSON = Path("artifacts/database/dba_audit_report.json")
DEFAULT_REPORT_TXT = Path("artifacts/database/dba_findings.txt")


@dataclass(slots=True)
class Finding:
    id: str
    severity: str
    message: str
    file: str | None = None
    line: int | None = None


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DBA governance audit")
    parser.add_argument(
        "--report", action="store_true", help="Emit report artifacts"
    )
    parser.add_argument(
        "--profile",
        choices=("ci", "release"),
        default="ci",
        help="Execution profile",
    )
    parser.add_argument(
        "--dialect",
        choices=("auto", "sqlite", "postgres"),
        default="auto",
        help="SQL dialect policy",
    )
    parser.add_argument("--db-url", default=None, help="Optional database URL")
    parser.add_argument(
        "--sql-path",
        action="append",
        default=None,
        help="Path containing SQL files (repeatable)",
    )
    parser.add_argument(
        "--max-critical",
        type=int,
        default=None,
        help="Maximum allowed critical findings",
    )
    parser.add_argument(
        "--max-high",
        type=int,
        default=None,
        help="Maximum allowed high findings",
    )

    args = parser.parse_args(argv)
    for flag, value in (
        ("--max-critical", args.max_critical),
        ("--max-high", args.max_high),
    ):
        if value is not None and value < 0:
            parser.error(f"{flag} must be >= 0")
    return args


def _detect_dialect(
    requested: str, db_url: str | None, sql_files: list[Path]
) -> str:
    if requested != "auto":
        return requested

    if db_url:
        lowered = db_url.lower()
        if lowered.startswith("postgres://") or lowered.startswith(
            "postgresql://"
        ):
            return "postgres"
        if lowered.startswith("sqlite://"):
            return "sqlite"

    clickhouse_pattern = re.compile(r"mergetree|clickhouse", re.IGNORECASE)
    for sql_file in sql_files:
        text = sql_file.read_text(encoding="utf-8", errors="replace")
        if clickhouse_pattern.search(text):
            return "sqlite"
    return "sqlite"


def _collect_sql_files(paths: list[str]) -> list[Path]:
    sql_files: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_file() and path.suffix.lower() == ".sql":
            sql_files.append(path)
            continue
        if path.is_dir():
            sql_files.extend(sorted(path.rglob("*.sql")))
    return sorted(set(sql_files))


def _line_number(text: str, token: str) -> int | None:
    idx = text.lower().find(token)
    if idx < 0:
        return None
    return text[:idx].count("\n") + 1


def _scan_sql_content(sql_file: Path, findings: list[Finding]) -> None:
    text = sql_file.read_text(encoding="utf-8", errors="replace")
    lowered = text.lower()

    if "select *" in lowered:
        findings.append(
            Finding(
                id="DBA010",
                severity="medium",
                message="Avoid SELECT * in governed SQL scripts",
                file=str(sql_file),
                line=_line_number(lowered, "select *"),
            )
        )

    if "drop table" in lowered and "if exists" not in lowered:
        findings.append(
            Finding(
                id="DBA020",
                severity="high",
                message="DROP TABLE without IF EXISTS",
                file=str(sql_file),
                line=_line_number(lowered, "drop table"),
            )
        )

    if "create table" in lowered and "if not exists" not in lowered:
        findings.append(
            Finding(
                id="DBA030",
                severity="low",
                message="CREATE TABLE without IF NOT EXISTS",
                file=str(sql_file),
                line=_line_number(lowered, "create table"),
            )
        )


def _summarize(findings: list[Finding]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for finding in findings:
        counter[finding.severity] += 1
    return {severity: counter.get(severity, 0) for severity in SEVERITY_ORDER}


def _write_text_report(path: Path, findings: list[Finding]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not findings:
        path.write_text("No findings.\n", encoding="utf-8")
        return

    lines = ["DBA GOVERNANCE FINDINGS", ""]
    for finding in findings:
        location = ""
        if finding.file:
            location = finding.file
            if finding.line is not None:
                location += f":{finding.line}"
        lines.append(
            f"[{finding.severity.upper()}] {finding.id} {location} - {finding.message}".strip()
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _breaches(
    summary: dict[str, int], max_critical: int | None, max_high: int | None
) -> list[str]:
    breaches: list[str] = []
    if max_critical is not None and summary["critical"] > max_critical:
        breaches.append(
            f"critical findings {summary['critical']} exceed threshold {max_critical}"
        )
    if max_high is not None and summary["high"] > max_high:
        breaches.append(
            f"high findings {summary['high']} exceed threshold {max_high}"
        )
    return breaches


def run(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    sql_paths = args.sql_path or ["sql"]
    findings: list[Finding] = []
    sql_files = _collect_sql_files(sql_paths)
    if not sql_files:
        findings.append(
            Finding(
                id="DBA001",
                severity="high",
                message="No SQL files discovered in provided paths",
            )
        )

    for sql_file in sql_files:
        _scan_sql_content(sql_file, findings)

    effective_dialect = _detect_dialect(args.dialect, args.db_url, sql_files)

    if (
        args.profile == "release"
        and effective_dialect == "postgres"
        and not args.db_url
    ):
        findings.append(
            Finding(
                id="DBA100",
                severity="critical",
                message="Postgres dialect in release profile requires --db-url",
            )
        )

    summary = _summarize(findings)
    breaches = _breaches(summary, args.max_critical, args.max_high)

    payload: dict[str, Any] = {
        "profile": args.profile,
        "requested_dialect": args.dialect,
        "effective_dialect": effective_dialect,
        "db_url_provided": bool(args.db_url),
        "checked_paths": sql_paths,
        "sql_file_count": len(sql_files),
        "summary": summary,
        "findings": [asdict(item) for item in findings],
        "breaches": breaches,
        "pass": not breaches,
    }

    DEFAULT_REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_REPORT_JSON.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _write_text_report(DEFAULT_REPORT_TXT, findings)

    return 1 if breaches else 0


def main(argv: list[str] | None = None) -> int:
    try:
        return run(argv)
    except Exception as exc:  # pragma: no cover - defensive guard
        error_payload = {
            "pass": False,
            "error": str(exc),
            "summary": dict.fromkeys(SEVERITY_ORDER, 0),
            "findings": [],
            "breaches": ["execution error"],
        }
        DEFAULT_REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_REPORT_JSON.write_text(
            json.dumps(error_payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        DEFAULT_REPORT_TXT.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_REPORT_TXT.write_text(
            f"Execution error: {exc}\n", encoding="utf-8"
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
