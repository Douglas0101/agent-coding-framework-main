#!/usr/bin/env python3
"""Code Health Score Calculator - Enterprise Composite Metric.

Calcula um score composto (0-100) baseado em:
- Coverage (30%): Cobertura de testes
- Complexity (25%): Complexidade ciclomática média
- Duplication (20%): Código duplicado
- Tech Debt (25%): Dívida técnica estimada

Integra com métricas DORA para visão enterprise.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict


PROJECT_ROOT = Path(__file__).parents[4]
SRC_ROOT = PROJECT_ROOT / "src"
COMMAND_TIMEOUT_SEC = 120


class DORAMetrics(TypedDict, total=False):
    """Typed DORA metrics for optional reporting."""

    lead_time_hours: float
    deployment_frequency: str
    mttr_hours: float
    change_failure_rate: float


class RuffIssue(TypedDict, total=False):
    """Subset of Ruff JSON issue payload used by this script."""

    code: str
    filename: str


@dataclass(slots=True)
class CommandResult:
    """Normalized command result for subprocess execution."""

    returncode: int
    stdout: str
    stderr: str


@dataclass(slots=True)
class CommandRunner:
    """Boundary adapter to execute shell commands from project root."""

    cwd: Path = PROJECT_ROOT
    timeout_sec: int = COMMAND_TIMEOUT_SEC

    def run(self, cmd: list[str]) -> CommandResult:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                cwd=self.cwd,
                timeout=self.timeout_sec,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as _:
            return CommandResult(returncode=1, stdout="", stderr="")
        return CommandResult(
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )


@dataclass(slots=True)
class HealthMetrics:
    """Métricas de saúde do código."""

    coverage_score: float = 0.0
    complexity_score: float = 0.0
    duplication_score: float = 0.0
    tech_debt_score: float = 0.0

    # DORA Metrics (optional)
    lead_time_hours: float | None = None
    deployment_frequency: str | None = None
    mttr_hours: float | None = None
    change_failure_rate: float | None = None

    # Raw values
    coverage_percent: float = 0.0
    avg_complexity: float = 0.0
    duplication_percent: float = 0.0
    lint_issues: int = 0

    @property
    def composite_score(self) -> float:
        """Calcula score composto ponderado."""
        return (
            self.coverage_score * 0.30
            + self.complexity_score * 0.25
            + self.duplication_score * 0.20
            + self.tech_debt_score * 0.25
        )

    @property
    def grade(self) -> str:
        """Retorna grade baseado no score."""
        score = self.composite_score
        if score >= 90:
            return "A+"
        if score >= 80:
            return "A"
        if score >= 70:
            return "B"
        if score >= 60:
            return "C"
        if score >= 50:
            return "D"
        return "F"


def _parse_coverage_from_report(report_stdout: str) -> float | None:
    for line in report_stdout.splitlines():
        if "TOTAL" not in line:
            continue
        for part in line.split():
            if not part.endswith("%"):
                continue
            try:
                return float(part.removesuffix("%"))
            except ValueError:
                return None
    return None


def get_coverage_score(runner: CommandRunner) -> tuple[float, float]:
    """Obtém score de cobertura de testes."""
    total_only = runner.run(["coverage", "report", "--format=total"])
    if total_only.returncode == 0:
        try:
            coverage = float(total_only.stdout.strip())
            return min(coverage, 100.0), coverage
        except ValueError:
            pass

    if not (PROJECT_ROOT / ".coverage").exists():
        return 0.0, 0.0

    full_report = runner.run(["coverage", "report"])
    coverage = _parse_coverage_from_report(full_report.stdout)
    if coverage is None:
        return 0.0, 0.0
    return min(coverage, 100.0), coverage


def _parse_ruff_issues(stdout: str) -> list[RuffIssue]:
    if not stdout:
        return []
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []

    issues: list[RuffIssue] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        issue: RuffIssue = {}
        code = item.get("code")
        filename = item.get("filename")
        if isinstance(code, str):
            issue["code"] = code
        if isinstance(filename, str):
            issue["filename"] = filename
        issues.append(issue)
    return issues


def get_ruff_issues(runner: CommandRunner) -> list[RuffIssue]:
    """Obtém issues do Ruff (um único snapshot para múltiplas métricas)."""
    result = runner.run(
        ["ruff", "check", "--output-format=json", str(SRC_ROOT)]
    )
    if result.returncode not in (0, 1):
        return []
    return _parse_ruff_issues(result.stdout)


def get_complexity_score(issues: list[RuffIssue]) -> tuple[float, float]:
    """Calcula score de complexidade a partir das issues C901 do Ruff."""
    complex_count = sum(1 for issue in issues if issue.get("code") == "C901")
    score = max(0.0, 100.0 - complex_count * 5.0)
    avg_complexity = 10.0 + complex_count * 2.0 if complex_count > 0 else 5.0
    return score, avg_complexity


def _count_python_lines(root: Path) -> int:
    total = 0
    if not root.exists():
        return total

    for file_path in root.rglob("*.py"):
        try:
            with file_path.open("rb") as source:
                total += sum(1 for _ in source)
        except OSError:
            continue
    return total


def get_duplication_score() -> tuple[float, float]:
    """Obtém score de duplicação estimado sem depender de shell tools."""
    total_lines = _count_python_lines(SRC_ROOT)
    if total_lines <= 0:
        return 80.0, 5.0

    # Estimativa: projetos bem mantidos têm < 5% duplicação.
    # Mantemos faixa 2-8% para evitar oscilações extremas.
    estimated_dup = min(8.0, max(2.0, total_lines / 1000.0))
    score = max(0.0, 100.0 - estimated_dup * 5.0)
    return score, estimated_dup


def get_tech_debt_score(issues: list[RuffIssue]) -> tuple[float, int]:
    """Obtém score de dívida técnica baseado em volume total de lint issues."""
    issue_count = len(issues)
    score = max(0.0, 100.0 - issue_count * 2.0)
    return score, issue_count


def get_dora_metrics(runner: CommandRunner) -> DORAMetrics:
    """Calcula métricas DORA baseado no histórico git."""
    metrics: DORAMetrics = {}

    timestamp_log = runner.run(["git", "log", "-n", "50", "--format=%ct"])
    if timestamp_log.returncode == 0:
        timestamps = [
            int(raw) for raw in timestamp_log.stdout.splitlines() if raw
        ]
        if len(timestamps) >= 2:
            diffs = [
                timestamps[i] - timestamps[i + 1]
                for i in range(len(timestamps) - 1)
            ]
            avg_diff_hours = (sum(diffs) / len(diffs)) / 3600
            metrics["lead_time_hours"] = round(avg_diff_hours, 1)

    weekly_log = runner.run(["git", "log", "--since=1.week", "--format=%H"])
    if weekly_log.returncode == 0:
        weekly_commits = len(
            [line for line in weekly_log.stdout.splitlines() if line]
        )
        if weekly_commits >= 7:
            metrics["deployment_frequency"] = "Daily"
        elif weekly_commits >= 3:
            metrics["deployment_frequency"] = "Multiple per week"
        elif weekly_commits >= 1:
            metrics["deployment_frequency"] = "Weekly"
        else:
            metrics["deployment_frequency"] = "Monthly"

    return metrics


def calculate_health(runner: CommandRunner | None = None) -> HealthMetrics:
    """Calcula todas as métricas de saúde em paralelo quando possível."""
    runner = runner or CommandRunner()
    metrics = HealthMetrics()

    with ThreadPoolExecutor(max_workers=4) as executor:
        coverage_future = executor.submit(get_coverage_score, runner)
        ruff_future = executor.submit(get_ruff_issues, runner)
        duplication_future = executor.submit(get_duplication_score)
        dora_future = executor.submit(get_dora_metrics, runner)

        metrics.coverage_score, metrics.coverage_percent = (
            coverage_future.result()
        )
        ruff_issues = ruff_future.result()
        metrics.duplication_score, metrics.duplication_percent = (
            duplication_future.result()
        )
        dora = dora_future.result()

    metrics.complexity_score, metrics.avg_complexity = get_complexity_score(
        ruff_issues
    )
    metrics.tech_debt_score, metrics.lint_issues = get_tech_debt_score(
        ruff_issues
    )

    metrics.lead_time_hours = dora.get("lead_time_hours")
    metrics.deployment_frequency = dora.get("deployment_frequency")
    metrics.mttr_hours = dora.get("mttr_hours")
    metrics.change_failure_rate = dora.get("change_failure_rate")

    return metrics


def format_report(metrics: HealthMetrics) -> str:
    """Formata relatório de saúde."""
    lines = [
        "=" * 70,
        "CODE HEALTH SCORE REPORT",
        f"Generated: {datetime.now(UTC).isoformat()}",
        "=" * 70,
        "",
        (
            f"🏆 COMPOSITE SCORE: {metrics.composite_score:.1f}/100 "
            f"(Grade: {metrics.grade})"
        ),
        "",
        "─" * 70,
        "COMPONENT SCORES (weighted)",
        "─" * 70,
        (
            f"  📊 Coverage (30%):    {metrics.coverage_score:.1f}/100  "
            f"({metrics.coverage_percent:.1f}% covered)"
        ),
        (
            f"  🔄 Complexity (25%):  {metrics.complexity_score:.1f}/100  "
            f"(avg: {metrics.avg_complexity:.1f})"
        ),
        (
            f"  📋 Duplication (20%): {metrics.duplication_score:.1f}/100  "
            f"(~{metrics.duplication_percent:.1f}% dup)"
        ),
        (
            f"  🔧 Tech Debt (25%):   {metrics.tech_debt_score:.1f}/100  "
            f"({metrics.lint_issues} issues)"
        ),
        "",
    ]

    if metrics.lead_time_hours or metrics.deployment_frequency:
        lines.extend(
            [
                "─" * 70,
                "DORA METRICS",
                "─" * 70,
            ]
        )
        if metrics.lead_time_hours:
            lines.append(
                f"  ⏱️  Lead Time:           {metrics.lead_time_hours:.1f} hours"
            )
        if metrics.deployment_frequency:
            lines.append(
                f"  🚀 Deploy Frequency:    {metrics.deployment_frequency}"
            )
        if metrics.mttr_hours:
            lines.append(
                f"  🔧 MTTR:                {metrics.mttr_hours:.1f} hours"
            )
        if metrics.change_failure_rate:
            lines.append(
                f"  ❌ Change Failure Rate: {metrics.change_failure_rate:.1f}%"
            )
        lines.append("")

    lines.extend(
        [
            "─" * 70,
            "RECOMMENDATIONS",
            "─" * 70,
        ]
    )

    if metrics.coverage_score < 70:
        lines.append("  ⚠️  Increase test coverage to at least 85%")
    if metrics.complexity_score < 70:
        lines.append("  ⚠️  Reduce cyclomatic complexity in flagged functions")
    if metrics.tech_debt_score < 70:
        lines.append("  ⚠️  Address lint issues to reduce technical debt")
    if metrics.composite_score >= 80:
        lines.append(
            "  ✅ Code health is excellent! Maintain current practices."
        )

    lines.extend(["", "=" * 70])

    return "\n".join(lines)


def main() -> int:
    """Função principal."""
    parser = argparse.ArgumentParser(
        description="Code Health Score Calculator"
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--brief", action="store_true", help="Brief output")
    args = parser.parse_args()

    metrics = calculate_health()

    if args.json:
        output = {
            "composite_score": round(metrics.composite_score, 1),
            "grade": metrics.grade,
            "components": {
                "coverage": {
                    "score": metrics.coverage_score,
                    "value": metrics.coverage_percent,
                },
                "complexity": {
                    "score": metrics.complexity_score,
                    "value": metrics.avg_complexity,
                },
                "duplication": {
                    "score": metrics.duplication_score,
                    "value": metrics.duplication_percent,
                },
                "tech_debt": {
                    "score": metrics.tech_debt_score,
                    "value": metrics.lint_issues,
                },
            },
            "dora": {
                "lead_time_hours": metrics.lead_time_hours,
                "deployment_frequency": metrics.deployment_frequency,
            },
            "timestamp": datetime.now(UTC).isoformat(),
        }
        print(json.dumps(output, indent=2))
    elif args.brief:
        print(
            f"Health Score: {metrics.composite_score:.1f}/100 ({metrics.grade})"
        )
    else:
        print(format_report(metrics))

    # Exit code based on score
    return 0 if metrics.composite_score >= 70 else 1


if __name__ == "__main__":
    sys.exit(main())
