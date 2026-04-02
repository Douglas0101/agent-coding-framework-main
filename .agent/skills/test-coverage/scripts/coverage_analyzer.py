#!/usr/bin/env python3
"""Script de automação para análise de cobertura de testes.

Analisa gaps de cobertura, identifica módulos prioritários,
e gera recomendações para melhorar cobertura.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


DEFAULT_OVERALL_TARGET = 85.0
DEFAULT_CRITICAL_TARGET = 65.0
SYSTEM_BLAS_PATH = Path("/lib/x86_64-linux-gnu/libblas.so.3")
SHIM_LIBRARY_NAME = "libcblas.so.3"
DEFAULT_PYTEST_MARK_EXPRESSION = "not stress and not slow"
DEFAULT_CRITICAL_MODULE_PATTERNS = (
    "src/engineering/swarm/planner.py",
    "src/engineering/swarm/scheduler.py",
    "src/engineering/swarm/policy_engine.py",
    "src/engineering/swarm/quality_gate.py",
    "src/engineering/swarm/filters.py",
    "src/engineering/swarm/registry.py",
    "src/engineering/swarm/memory/episodic.py",
    "src/engineering/swarm/memory/procedural.py",
    "src/engineering/swarm/memory/store.py",
)


@dataclass
class ModuleCoverage:
    """Cobertura de um módulo."""

    name: str
    statements: int
    missing: int
    coverage: float
    missing_lines: str

    @property
    def priority(self) -> str:
        """Determina prioridade baseada no módulo."""
        if "security" in self.name:
            return "CRITICAL"
        elif "serving" in self.name or "training" in self.name:
            return "HIGH"
        elif "data" in self.name:
            return "MEDIUM"
        return "LOW"

    @property
    def target(self) -> float:
        """Retorna target de cobertura para o módulo."""
        targets = {
            "CRITICAL": 95.0,
            "HIGH": 90.0,
            "MEDIUM": 85.0,
            "LOW": 80.0,
        }
        return targets[self.priority]

    @property
    def gap(self) -> float:
        """Retorna gap para o target."""
        return max(0, self.target - self.coverage)


def run_coverage() -> tuple[int, str]:
    """Executa pytest com coverage."""
    project_root = Path(__file__).parents[4]
    # Use project venv Python to ensure pytest plugins are available
    venv_python = project_root / ".venv" / "bin" / "python"
    python_exe = str(venv_python) if venv_python.exists() else sys.executable
    cmd = [
        python_exe,
        "-m",
        "pytest",
        "-m",
        DEFAULT_PYTEST_MARK_EXPRESSION,
        "--cov=src",
        "--cov-report=term-missing",
        "--cov-report=json:coverage.json",
        "-n",
        "auto",
        "--dist=loadscope",
        "-q",
        "--benchmark-skip",
    ]

    env = _build_runtime_env(project_root)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        cwd=project_root,
    )

    return result.returncode, result.stdout + result.stderr


def _ensure_blas_shim(project_root: Path) -> Path | None:
    """Provide a local libcblas shim when numpy depends on it."""
    if not SYSTEM_BLAS_PATH.exists():
        return None

    shim_dir = project_root / "artifacts" / "runtime_shims"
    shim_dir.mkdir(parents=True, exist_ok=True)
    shim_path = shim_dir / SHIM_LIBRARY_NAME
    if not shim_path.exists():
        shim_path.symlink_to(SYSTEM_BLAS_PATH)
    return shim_dir


def _build_runtime_env(project_root: Path) -> dict[str, str]:
    """Build deterministic subprocess environment for coverage runs."""
    env = {
        **os.environ,
        "OTEL_ENABLED": "false",
    }

    shim_dir = _ensure_blas_shim(project_root)
    if shim_dir is not None:
        existing = env.get("LD_LIBRARY_PATH", "")
        prefixes = [str(shim_dir), "/lib/x86_64-linux-gnu"]
        if existing:
            prefixes.append(existing)
        env["LD_LIBRARY_PATH"] = ":".join(prefixes)

    return env


def parse_total_line(line: str) -> ModuleCoverage | None:
    """Parse total line."""
    if not line.startswith("TOTAL"):
        return None

    parts = line.split()
    if len(parts) < 4:
        return None

    try:
        return ModuleCoverage(
            name="TOTAL",
            statements=int(parts[1]),
            missing=int(parts[2]),
            coverage=float(parts[3].rstrip("%")),
            missing_lines="",
        )
    except (ValueError, IndexError):
        return None


def parse_module_line(line: str) -> ModuleCoverage | None:
    """Parse module line."""
    parts = line.split()
    if len(parts) < 4 or not parts[0].endswith(".py"):
        return None

    try:
        missing_lines = parts[4] if len(parts) >= 5 else ""
        return ModuleCoverage(
            name=parts[0],
            statements=int(parts[1]),
            missing=int(parts[2]),
            coverage=float(parts[3].rstrip("%")),
            missing_lines=missing_lines,
        )
    except (ValueError, IndexError):
        return None


def parse_coverage_output(output: str) -> list[ModuleCoverage]:
    """Parseia output de cobertura."""
    modules = []
    in_coverage = False

    for line in output.split("\n"):
        if "Name" in line and "Stmts" in line:
            in_coverage = True
            continue

        if not in_coverage:
            continue

        if line.startswith("TOTAL") or line.startswith("-"):
            if line.startswith("TOTAL"):
                total = parse_total_line(line)
                if total:
                    modules.append(total)
            continue

        module = parse_module_line(line)
        if module:
            modules.append(module)

    return modules


def identify_gaps(modules: list[ModuleCoverage]) -> list[ModuleCoverage]:
    """Identifica módulos abaixo do target."""
    gaps = [m for m in modules if m.name != "TOTAL" and m.gap > 0]
    return sorted(gaps, key=lambda x: (-x.gap, x.priority))


def generate_recommendations(
    modules: list[ModuleCoverage],
) -> list[str]:
    """Gera recomendações de melhoria."""
    recommendations = []

    gaps = identify_gaps(modules)

    for module in gaps[:5]:  # Top 5 prioridades
        tests_needed = int(module.missing * (module.gap / 100))
        recommendations.append(
            f"📝 {module.name}: Add ~{tests_needed} test cases "
            f"(current: {module.coverage:.0f}%, target: {module.target:.0f}%)"
        )

        if module.missing_lines:
            lines = module.missing_lines.split(",")[:3]
            recommendations.append(f"   Focus on lines: {', '.join(lines)}")

    return recommendations


def resolve_critical_patterns(patterns: list[str] | None) -> list[str]:
    """Resolve critical module selectors with stable defaults."""
    if patterns:
        resolved = [item.strip() for item in patterns if item.strip()]
        if resolved:
            return resolved
    return list(DEFAULT_CRITICAL_MODULE_PATTERNS)


def select_critical_modules(
    modules: list[ModuleCoverage],
    patterns: list[str],
) -> list[ModuleCoverage]:
    """Select modules considered critical by explicit path patterns."""
    selected: list[ModuleCoverage] = []
    for module in modules:
        if module.name == "TOTAL":
            continue
        normalized_name = module.name.replace("\\", "/")
        if any(
            fnmatch.fnmatch(normalized_name, pattern) for pattern in patterns
        ):
            selected.append(module)
    return selected


def identify_critical_gaps(
    modules: list[ModuleCoverage],
    *,
    target: float,
    patterns: list[str],
) -> list[ModuleCoverage]:
    """Return critical modules below the enforced critical target."""
    selected = select_critical_modules(modules, patterns)
    gaps = [module for module in selected if module.coverage < target]
    return sorted(gaps, key=lambda item: item.coverage)


def format_report(
    modules: list[ModuleCoverage],
    *,
    policy_scope: str,
    overall_target: float,
    critical_target: float,
    critical_patterns: list[str],
) -> str:
    """Formata relatório de cobertura com metadados de política."""
    lines = [
        "=" * 80,
        "TEST COVERAGE ANALYSIS REPORT",
        f"Generated: {datetime.now(UTC).isoformat()}",
        "=" * 80,
        "",
        f"Policy scope: {policy_scope}",
        f"Overall target: {overall_target:.1f}%",
    ]

    if policy_scope == "critical":
        lines.extend(
            [
                f"Critical target: {critical_target:.1f}%",
                f"Critical patterns: {', '.join(critical_patterns)}",
            ]
        )

    lines.append("")

    # Encontra total
    total = next((m for m in modules if m.name == "TOTAL"), None)
    if total:
        if policy_scope == "full":
            status = "✅" if total.coverage >= overall_target else "❌"
        else:
            status = "INFO"
        lines.extend(
            [
                f"OVERALL COVERAGE: {total.coverage:.1f}% {status}",
                f"  Statements: {total.statements}",
                f"  Missing: {total.missing}",
                f"  Target: {overall_target:.1f}%",
                "",
            ]
        )

    critical_modules = select_critical_modules(modules, critical_patterns)
    if policy_scope == "critical":
        lines.extend(
            [
                "CRITICAL MODULES",
                "-" * 80,
            ]
        )
        if not critical_modules:
            lines.append("No critical modules matched configured patterns.")
        else:
            lines.append(f"{'Module':<45} {'Coverage':>10} {'Target':>10}")
            for module in sorted(
                critical_modules,
                key=lambda item: item.coverage,
            ):
                lines.append(
                    f"{module.name[-45:]:<45} "
                    f"{module.coverage:>9.1f}% "
                    f"{critical_target:>9.1f}%"
                )
        lines.append("")

    # Agrupa por prioridade
    for priority in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        priority_modules = [
            m for m in modules if m.name != "TOTAL" and m.priority == priority
        ]

        if not priority_modules:
            continue

        emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}[
            priority
        ]

        lines.extend(
            [
                f"{emoji} {priority} PRIORITY",
                "-" * 80,
                f"{'Module':<45} {'Coverage':>10} {'Target':>10} {'Gap':>10}",
            ]
        )

        for m in sorted(priority_modules, key=lambda x: x.coverage):
            gap_str = f"-{m.gap:.0f}%" if m.gap > 0 else "✓"
            lines.append(
                f"{m.name[-45:]:<45} "
                f"{m.coverage:>9.1f}% "
                f"{m.target:>9.0f}% "
                f"{gap_str:>10}"
            )

        lines.append("")

    # Recomendações
    gaps = identify_gaps(modules)
    if gaps:
        lines.extend(
            [
                "RECOMMENDATIONS",
                "-" * 80,
            ]
        )
        lines.extend(generate_recommendations(modules))

    lines.append("=" * 80)

    return "\n".join(lines)


def handle_coverage_command(
    args: argparse.Namespace,
    project_root: Path,
) -> tuple[int, str]:
    """Handle coverage analysis command."""
    if args.run:
        print("🧪 Running tests with coverage...")
        code, output = run_coverage()
    else:
        print("📊 Analyzing existing coverage...")
        result = subprocess.run(
            ["coverage", "report", "--show-missing"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        code = result.returncode
        output = result.stdout + result.stderr
    return code, output


def handle_report_command(
    modules: list[ModuleCoverage],
    project_root: Path,
    *,
    policy_scope: str,
    overall_target: float,
    critical_target: float,
    critical_patterns: list[str],
) -> None:
    """Handle report generation."""
    report = format_report(
        modules,
        policy_scope=policy_scope,
        overall_target=overall_target,
        critical_target=critical_target,
        critical_patterns=critical_patterns,
    )
    print(report)

    report_path = project_root / "artifacts" / "coverage_report.txt"
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(report)
    print(f"\n📄 Report saved to: {report_path}")


def evaluate_threshold_failures(
    modules: list[ModuleCoverage],
    *,
    policy_scope: str,
    overall_target: float,
    critical_target: float,
    critical_patterns: list[str],
) -> list[str]:
    """Evaluate coverage failures against enforced targets."""
    failures: list[str] = []

    total = next((m for m in modules if m.name == "TOTAL"), None)
    if total is None:
        failures.append("missing TOTAL coverage summary")
    elif policy_scope == "full" and total.coverage < overall_target:
        failures.append(
            "TOTAL coverage "
            f"{total.coverage:.1f}% is below target {overall_target:.1f}%"
        )

    if policy_scope == "full":
        for module in identify_gaps(modules):
            failures.append(
                f"{module.name} {module.coverage:.1f}% < "
                f"{module.target:.0f}% ({module.priority})"
            )
        return failures

    critical_modules = select_critical_modules(modules, critical_patterns)
    if not critical_modules:
        failures.append("critical scope matched no modules")
        return failures

    for module in sorted(critical_modules, key=lambda item: item.coverage):
        if module.coverage < critical_target:
            failures.append(
                f"critical module {module.name} {module.coverage:.1f}% "
                f"< {critical_target:.1f}%"
            )

    return failures


def should_enforce_command_exit(
    *,
    policy_scope: str,
    command_exit: int,
) -> bool:
    """Return whether non-zero coverage command exit should fail gate."""
    if command_exit == 0:
        return False
    return policy_scope == "full"


def main() -> int:
    """Função principal."""
    parser = argparse.ArgumentParser(
        description="Test coverage analysis automation"
    )
    parser.add_argument(
        "--gaps", action="store_true", help="Show only modules below target"
    )
    parser.add_argument(
        "--recommend", action="store_true", help="Show recommendations"
    )
    parser.add_argument(
        "--report", action="store_true", help="Generate full report"
    )
    parser.add_argument("--run", action="store_true", help="Run tests first")
    parser.add_argument(
        "--policy-scope",
        choices=["full", "critical"],
        default="full",
        help="Coverage policy scope: full project or critical modules only",
    )
    parser.add_argument(
        "--overall-target",
        type=float,
        default=DEFAULT_OVERALL_TARGET,
        help="Overall coverage target used in full scope",
    )
    parser.add_argument(
        "--critical-target",
        type=float,
        default=DEFAULT_CRITICAL_TARGET,
        help="Minimum coverage required for modules in critical scope",
    )
    parser.add_argument(
        "--critical-module",
        action="append",
        default=None,
        help=(
            "Critical module pattern (fnmatch). "
            "Repeatable; defaults to swarm runtime core modules"
        ),
    )
    parser.add_argument(
        "--no-enforce",
        action="store_true",
        help="Do not fail when coverage targets are below policy thresholds",
    )

    args = parser.parse_args()
    if not 0 <= args.overall_target <= 100:
        parser.error("--overall-target must be between 0 and 100")
    if not 0 <= args.critical_target <= 100:
        parser.error("--critical-target must be between 0 and 100")

    project_root = Path(__file__).parents[4]
    critical_patterns = resolve_critical_patterns(args.critical_module)

    code, output = handle_coverage_command(args, project_root)
    modules = parse_coverage_output(output)

    if not modules:
        if output.strip():
            print(output.strip())
        print("⚠️  No coverage data found. Run with --run first.")
        return 1

    if args.gaps:
        if args.policy_scope == "critical":
            gaps = identify_critical_gaps(
                modules,
                target=args.critical_target,
                patterns=critical_patterns,
            )
        else:
            gaps = identify_gaps(modules)
        if gaps:
            print("\n🔍 Modules below target coverage:")
            for m in gaps:
                target = (
                    args.critical_target
                    if args.policy_scope == "critical"
                    else m.target
                )
                print(f"  {m.name}: {m.coverage:.1f}% (target: {target}%)")
        else:
            print("✅ All modules meet their coverage targets!")

    elif args.recommend:
        recommendations = generate_recommendations(modules)
        if recommendations:
            print("\n📋 Coverage Improvement Recommendations:")
            for rec in recommendations:
                print(rec)
        else:
            print("✅ No recommendations - coverage is excellent!")

    elif args.report:
        handle_report_command(
            modules,
            project_root,
            policy_scope=args.policy_scope,
            overall_target=args.overall_target,
            critical_target=args.critical_target,
            critical_patterns=critical_patterns,
        )

    else:
        total = next((m for m in modules if m.name == "TOTAL"), None)
        if total:
            status = "✅" if total.coverage >= args.overall_target else "❌"
            print(f"\n{status} Total coverage: {total.coverage:.1f}%")

    threshold_failures: list[str] = []
    if not args.no_enforce:
        threshold_failures = evaluate_threshold_failures(
            modules,
            policy_scope=args.policy_scope,
            overall_target=args.overall_target,
            critical_target=args.critical_target,
            critical_patterns=critical_patterns,
        )
        if threshold_failures:
            print("\n❌ Coverage policy gate failures:")
            for item in threshold_failures[:25]:
                print(f"  - {item}")
            if len(threshold_failures) > 25:
                remaining = len(threshold_failures) - 25
                print(f"  - ... and {remaining} more")

    fail_for_command_exit = should_enforce_command_exit(
        policy_scope=args.policy_scope,
        command_exit=code,
    )
    if code != 0 and not fail_for_command_exit:
        print(
            "⚠️  Coverage command returned non-zero exit, "
            "but policy scope is critical and thresholds passed."
        )

    # When --no-enforce is passed, never fail the command
    if args.no_enforce:
        return 0

    return 0 if not threshold_failures and not fail_for_command_exit else 1


if __name__ == "__main__":
    sys.exit(main())
