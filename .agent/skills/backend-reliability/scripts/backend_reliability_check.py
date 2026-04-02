#!/usr/bin/env python3
"""Backend reliability checks for FastAPI services."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute


SEVERITY_ORDER = ("critical", "high", "medium", "low", "info")
DEFAULT_REPORT_JSON = Path("artifacts/backend/backend_reliability_report.json")
DEFAULT_SNAPSHOT_JSON = Path("artifacts/backend/openapi_snapshot.json")
DEFAULT_BASELINE_JSON = Path("artifacts/backend/openapi_baseline.json")


@dataclass(slots=True)
class Finding:
    id: str
    severity: str
    message: str
    module: str | None = None
    route: str | None = None


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backend reliability checks")
    parser.add_argument(
        "--report", action="store_true", help="Emit report artifacts"
    )
    parser.add_argument(
        "--app-module",
        action="append",
        default=None,
        help="FastAPI app module in module:attr format (repeatable)",
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
    parser.add_argument(
        "--require-auth",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Require auth dependencies on non-health routes",
    )
    parser.add_argument(
        "--baseline-snapshot",
        default=str(DEFAULT_BASELINE_JSON),
        help="Optional baseline OpenAPI snapshot for drift detection",
    )

    args = parser.parse_args(argv)
    for flag, value in (
        ("--max-critical", args.max_critical),
        ("--max-high", args.max_high),
    ):
        if value is not None and value < 0:
            parser.error(f"{flag} must be >= 0")

    modules = args.app_module or ["src.api.main:app", "src.serving.api:app"]
    for module in modules:
        if ":" not in module:
            parser.error("--app-module must use module:attr format")
        module_name, attr_name = module.split(":", 1)
        if not module_name.strip() or not attr_name.strip():
            parser.error("--app-module must use module:attr format")
    args.app_module = modules
    return args


def _is_health_route(route: APIRoute) -> bool:
    return route.path.rstrip("/") in {"/health", "/healthz", "/live", "/ready"}


def _has_auth_dependency(route: APIRoute) -> bool:
    for dependency in route.dependant.dependencies:
        call = getattr(dependency, "call", None)
        name = getattr(call, "__name__", "").lower()
        qualname = getattr(call, "__qualname__", "").lower()
        if any(token in name for token in ("auth", "api_key", "security")):
            return True
        if any(token in qualname for token in ("auth", "api_key", "security")):
            return True
    return False


def _summarize(findings: list[Finding]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for finding in findings:
        counter[finding.severity] += 1
    return {severity: counter.get(severity, 0) for severity in SEVERITY_ORDER}


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

    findings: list[Finding] = []
    snapshot_payload: dict[str, Any] = {"modules": {}}

    for app_module in args.app_module:
        module_name, attr_name = app_module.split(":", 1)
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:
            findings.append(
                Finding(
                    id="BACKEND100",
                    severity="critical",
                    message=f"Failed to import module '{module_name}': {exc}",
                    module=app_module,
                )
            )
            continue

        app = getattr(module, attr_name, None)
        if not isinstance(app, FastAPI):
            findings.append(
                Finding(
                    id="BACKEND110",
                    severity="critical",
                    message=f"Attribute '{attr_name}' is not a FastAPI app",
                    module=app_module,
                )
            )
            continue

        app_snapshot = app.openapi()
        snapshot_payload["modules"][app_module] = {
            "openapi": app_snapshot,
            "route_count": len(app.routes),
        }

        for route in app.routes:
            if not isinstance(route, APIRoute):
                continue

            if (
                args.require_auth
                and not _is_health_route(route)
                and not _has_auth_dependency(route)
            ):
                findings.append(
                    Finding(
                        id="BACKEND200",
                        severity="high",
                        message="Route does not declare auth dependency",
                        module=app_module,
                        route=route.path,
                    )
                )

            if not _is_health_route(route) and route.response_model is None:
                findings.append(
                    Finding(
                        id="BACKEND210",
                        severity="low",
                        message="Route is missing response_model contract",
                        module=app_module,
                        route=route.path,
                    )
                )

    baseline_path = Path(args.baseline_snapshot)
    if baseline_path.exists():
        baseline_payload = json.loads(
            baseline_path.read_text(encoding="utf-8")
        )
        if baseline_payload != snapshot_payload:
            findings.append(
                Finding(
                    id="BACKEND300",
                    severity="high",
                    message="OpenAPI snapshot drift detected against baseline",
                )
            )

    summary = _summarize(findings)
    breaches = _breaches(summary, args.max_critical, args.max_high)

    DEFAULT_SNAPSHOT_JSON.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_SNAPSHOT_JSON.write_text(
        json.dumps(snapshot_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    report_payload = {
        "require_auth": args.require_auth,
        "modules": args.app_module,
        "summary": summary,
        "findings": [asdict(item) for item in findings],
        "breaches": breaches,
        "baseline_snapshot": str(baseline_path),
        "openapi_snapshot": str(DEFAULT_SNAPSHOT_JSON),
        "pass": not breaches,
    }
    DEFAULT_REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_REPORT_JSON.write_text(
        json.dumps(report_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return 1 if breaches else 0


def main(argv: list[str] | None = None) -> int:
    try:
        return run(argv)
    except Exception as exc:  # pragma: no cover - defensive guard
        payload = {
            "pass": False,
            "error": str(exc),
            "summary": dict.fromkeys(SEVERITY_ORDER, 0),
            "findings": [],
            "breaches": ["execution error"],
        }
        DEFAULT_REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_REPORT_JSON.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        DEFAULT_SNAPSHOT_JSON.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_SNAPSHOT_JSON.write_text("{}\n", encoding="utf-8")
        return 2


if __name__ == "__main__":
    sys.exit(main())
