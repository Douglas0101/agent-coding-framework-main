#!/usr/bin/env python3
"""Script de automação para benchmarks e profiling de performance.

Executa benchmarks com pytest-benchmark, compara com baseline,
e gera relatórios de performance.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class BenchmarkResult:
    """Resultado de um benchmark."""

    name: str
    mean: float
    stddev: float
    min_time: float
    max_time: float
    rounds: int
    iterations: int

    @property
    def mean_ms(self) -> float:
        """Retorna média em milissegundos."""
        return self.mean * 1000


def run_benchmarks(
    save: bool = False,
    compare: bool = False,
) -> tuple[int, str]:
    """Executa benchmarks com pytest-benchmark."""
    cmd = [
        "pytest",
        "--benchmark-only",
        "--benchmark-json=benchmark_results.json",
        "-v",
    ]

    if save:
        cmd.append("--benchmark-autosave")

    if compare:
        cmd.extend(
            [
                "--benchmark-compare",
                "--benchmark-compare-fail=mean:15%",
            ]
        )

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parents[4],
    )

    return result.returncode, result.stdout + result.stderr


def parse_benchmark_json(json_path: Path) -> list[BenchmarkResult]:
    """Parseia resultados JSON do pytest-benchmark."""
    if not json_path.exists():
        return []

    with open(json_path) as f:
        data = json.load(f)

    results = []
    for bench in data.get("benchmarks", []):
        stats = bench.get("stats", {})
        result = BenchmarkResult(
            name=bench.get("name", "unknown"),
            mean=stats.get("mean", 0),
            stddev=stats.get("stddev", 0),
            min_time=stats.get("min", 0),
            max_time=stats.get("max", 0),
            rounds=stats.get("rounds", 0),
            iterations=stats.get("iterations", 0),
        )
        results.append(result)

    return results


def run_cpu_profile(script: str = "scripts/train.py") -> Path:
    """Executa CPU profiling com cProfile."""
    profile_path = Path(__file__).parents[4] / "artifacts" / "cpu_profile.prof"
    profile_path.parent.mkdir(exist_ok=True)

    cmd = [
        "python",
        "-m",
        "cProfile",
        "-o",
        str(profile_path),
        script,
        "--max-epochs",
        "1",
        "--dry-run",
    ]

    subprocess.run(
        cmd,
        cwd=Path(__file__).parents[4],
        capture_output=True,
    )

    return profile_path


def format_report(results: list[BenchmarkResult]) -> str:
    """Formata relatório de benchmarks."""
    lines = [
        "=" * 70,
        "PERFORMANCE BENCHMARK REPORT",
        f"Generated: {datetime.now(UTC).isoformat()}",
        "=" * 70,
        "",
        f"{'Benchmark':<40} {'Mean (ms)':<12} {'StdDev':<12} {'Rounds':<8}",
        "-" * 70,
    ]

    # Ordena por tempo médio (mais lento primeiro)
    sorted_results = sorted(results, key=lambda x: x.mean, reverse=True)

    for r in sorted_results:
        lines.append(
            f"{r.name[:40]:<40} "
            f"{r.mean_ms:>10.3f}  "
            f"{r.stddev * 1000:>10.4f}  "
            f"{r.rounds:>6}"
        )

    lines.extend(
        [
            "",
            "-" * 70,
            "SUMMARY",
            f"  Total benchmarks: {len(results)}",
        ]
    )

    if results:
        slowest = max(results, key=lambda x: x.mean)
        fastest = min(results, key=lambda x: x.mean)
        lines.extend(
            [
                f"  Slowest: {slowest.name} ({slowest.mean_ms:.3f}ms)",
                f"  Fastest: {fastest.name} ({fastest.mean_ms:.3f}ms)",
            ]
        )

    lines.append("=" * 70)

    return "\n".join(lines)


def main() -> int:
    """Função principal."""
    parser = argparse.ArgumentParser(
        description="Performance benchmarking automation"
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare with previous baseline",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save results as new baseline",
    )
    parser.add_argument(
        "--profile-cpu",
        action="store_true",
        help="Run CPU profiling",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate detailed report",
    )

    args = parser.parse_args()

    project_root = Path(__file__).parents[4]

    if args.profile_cpu:
        print("🔬 Running CPU profiling...")
        profile_path = run_cpu_profile()
        print(f"📄 Profile saved to: {profile_path}")
        print("\nTo analyze:")
        print(
            f'  python -c "import pstats; '
            f"p=pstats.Stats('{profile_path}'); "
            f"p.sort_stats('cumulative').print_stats(20)\""
        )
        return 0

    print("⚡ Running benchmarks...")
    code, output = run_benchmarks(save=args.save, compare=args.compare)

    # Parse resultados
    json_path = project_root / "benchmark_results.json"
    results = parse_benchmark_json(json_path)

    if args.report and results:
        report = format_report(results)
        print(report)

        report_path = project_root / "artifacts" / "benchmark_report.txt"
        report_path.parent.mkdir(exist_ok=True)
        report_path.write_text(report)
        print(f"\n📄 Report saved to: {report_path}")
    elif not results:
        print("⚠️  No benchmark results found.")
        print("Make sure you have benchmarks in tests/perf/")
        print(output)

    if code == 0:
        print("\n✅ All benchmarks passed!")
    else:
        print("\n❌ Benchmark failures detected.")

    return code


if __name__ == "__main__":
    sys.exit(main())
