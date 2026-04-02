#!/usr/bin/env python3
"""GPU Profiler - Enterprise ML Performance Analysis.

Profiling avançado para treinamento de modelos PyTorch:
- CUDA memory tracking
- Kernel profiling com torch.profiler
- Throughput analysis
- Bottleneck detection
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class GPUMetrics:
    """Métricas de GPU."""

    gpu_available: bool = False
    device_name: str = ""
    total_memory_gb: float = 0.0
    allocated_memory_gb: float = 0.0
    cached_memory_gb: float = 0.0
    utilization_percent: float = 0.0

    # Profiling
    cuda_time_ms: float = 0.0
    cpu_time_ms: float = 0.0
    memory_events: list = field(default_factory=list)

    @property
    def memory_usage_percent(self) -> float:
        """Porcentagem de memória usada."""
        if self.total_memory_gb == 0:
            return 0.0
        return (self.allocated_memory_gb / self.total_memory_gb) * 100


def check_gpu_availability() -> GPUMetrics:
    """Verifica disponibilidade de GPU."""
    metrics = GPUMetrics()

    try:
        import torch

        metrics.gpu_available = torch.cuda.is_available()

        if metrics.gpu_available:
            metrics.device_name = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            metrics.total_memory_gb = props.total_memory / (1024**3)
            metrics.allocated_memory_gb = torch.cuda.memory_allocated(0) / (
                1024**3
            )
            metrics.cached_memory_gb = torch.cuda.memory_reserved(0) / (
                1024**3
            )
    except ImportError:
        pass

    return metrics


def profile_model_forward(model_path: str | None = None) -> dict[str, object]:
    """Profile de forward pass de um modelo."""
    results: dict[str, object] = {
        "status": "skipped",
        "reason": "No model provided or torch unavailable",
    }

    try:
        import torch
        from torch.profiler import ProfilerActivity, profile, record_function

        if not torch.cuda.is_available():
            results["reason"] = "CUDA not available"
            return results

        # Dummy model for demonstration
        model = torch.nn.Sequential(
            torch.nn.Linear(1024, 512),
            torch.nn.ReLU(),
            torch.nn.Linear(512, 256),
            torch.nn.ReLU(),
            torch.nn.Linear(256, 10),
        ).cuda()

        x = torch.randn(32, 1024).cuda()

        # Warmup
        for _ in range(10):
            _ = model(x)

        torch.cuda.synchronize()

        # Profile
        with (
            profile(
                activities=[ProfilerActivity.CPU, ProfilerActivity.CUDA],
                record_shapes=True,
                profile_memory=True,
            ) as prof,
            record_function("model_forward"),
        ):
            for _ in range(100):
                _ = model(x)
            torch.cuda.synchronize()

        # Extract metrics
        events = prof.key_averages()

        cuda_time = sum(e.cuda_time_total for e in events) / 1000  # ms
        cpu_time = sum(e.cpu_time_total for e in events) / 1000  # ms

        success_results: dict[str, object] = {
            "status": "success",
            "iterations": 100,
            "cuda_time_ms": round(cuda_time, 3),
            "cpu_time_ms": round(cpu_time, 3),
            "avg_forward_ms": round(cuda_time / 100, 3),
            "top_operators": [
                {"name": e.key, "cuda_ms": round(e.cuda_time_total / 1000, 3)}
                for e in sorted(
                    events, key=lambda x: x.cuda_time_total, reverse=True
                )[:5]
            ],
        }
        return success_results

    except ImportError as e:
        results["reason"] = f"Import error: {e}"
    except Exception as e:
        results["reason"] = f"Error: {e}"

    return results


def get_memory_snapshot() -> dict[str, object]:
    """Obtém snapshot de memória GPU."""
    try:
        import torch

        if not torch.cuda.is_available():
            return {"available": False}

        snapshot: dict[str, object] = {
            "available": True,
            "device": torch.cuda.get_device_name(0),
            "total_gb": round(
                torch.cuda.get_device_properties(0).total_memory / (1024**3), 2
            ),
            "allocated_gb": round(
                torch.cuda.memory_allocated(0) / (1024**3), 4
            ),
            "cached_gb": round(torch.cuda.memory_reserved(0) / (1024**3), 4),
            "max_allocated_gb": round(
                torch.cuda.max_memory_allocated(0) / (1024**3), 4
            ),
        }
        return snapshot
    except ImportError:
        return {"available": False, "reason": "torch not installed"}


def analyze_training_efficiency() -> dict[str, object]:
    """Analisa eficiência de treinamento."""
    recommendations: list[dict[str, object]] = []

    try:
        import torch

        # Check AMP availability
        if torch.cuda.is_available() and hasattr(torch.cuda, "amp"):
            recommendations.append(
                {
                    "category": "Mixed Precision",
                    "status": "available",
                    "recommendation": (
                        "Use torch.cuda.amp.autocast() for 2-3x speedup"
                    ),
                    "code": (
                        "with torch.cuda.amp.autocast():\n    outputs = model(inputs)"
                    ),
                }
            )

        # Check cudnn
        if torch.backends.cudnn.is_available():
            recommendations.append(
                {
                    "category": "cuDNN",
                    "status": (
                        "enabled"
                        if torch.backends.cudnn.enabled
                        else "disabled"
                    ),
                    "recommendation": (
                        "Enable torch.backends.cudnn.benchmark = True for conv nets"
                    ),
                }
            )

        # Memory optimization
        recommendations.append(
            {
                "category": "Gradient Checkpointing",
                "status": "available",
                "recommendation": "Use torch.utils.checkpoint for memory-heavy models",
                "memory_savings": "Up to 50% reduction",
            }
        )

        # Compile
        if hasattr(torch, "compile"):
            recommendations.append(
                {
                    "category": "torch.compile",
                    "status": "available",
                    "recommendation": (
                        "Use torch.compile(model) for potential 30-50% speedup"
                    ),
                    "code": "model = torch.compile(model)",
                }
            )

    except ImportError:
        recommendations.append(
            {
                "category": "PyTorch",
                "status": "not_installed",
                "recommendation": "Install PyTorch with CUDA support",
            }
        )

    report: dict[str, object] = {
        "recommendations": recommendations,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    return report


def format_report(
    metrics: GPUMetrics, profile_results: dict, efficiency: dict
) -> str:
    """Formata relatório completo."""
    lines = [
        "=" * 70,
        "GPU PROFILER REPORT - Enterprise ML Performance",
        f"Generated: {datetime.now(UTC).isoformat()}",
        "=" * 70,
        "",
    ]

    # GPU Info
    lines.extend(
        [
            "─" * 70,
            "GPU HARDWARE",
            "─" * 70,
        ]
    )

    if metrics.gpu_available:
        lines.extend(
            [
                f"  🎮 Device:          {metrics.device_name}",
                f"  💾 Total Memory:    {metrics.total_memory_gb:.2f} GB",
                (
                    f"  📊 Allocated:       {metrics.allocated_memory_gb:.4f} GB "
                    f"({metrics.memory_usage_percent:.1f}%)"
                ),
                f"  🗂️  Cached:          {metrics.cached_memory_gb:.4f} GB",
            ]
        )
    else:
        lines.append("  ⚠️  GPU: Not available (CPU-only mode)")

    lines.append("")

    # Profiling Results
    if profile_results.get("status") == "success":
        lines.extend(
            [
                "─" * 70,
                "PROFILING RESULTS",
                "─" * 70,
                (
                    f"  ⏱️  CUDA Time:       "
                    f"{profile_results['cuda_time_ms']:.3f} ms (100 iters)"
                ),
                f"  🖥️  CPU Time:        {profile_results['cpu_time_ms']:.3f} ms",
                f"  📈 Avg Forward:     {profile_results['avg_forward_ms']:.3f} ms/iter",
                "",
                "  Top CUDA Operators:",
            ]
        )
        for op in profile_results.get("top_operators", [])[:5]:
            lines.append(f"    - {op['name']}: {op['cuda_ms']:.3f} ms")

    lines.append("")

    # Efficiency Recommendations
    lines.extend(
        [
            "─" * 70,
            "OPTIMIZATION RECOMMENDATIONS",
            "─" * 70,
        ]
    )

    for rec in efficiency.get("recommendations", []):
        status_icon = (
            "✅" if rec["status"] in ("available", "enabled") else "⚠️"
        )
        lines.append(
            f"  {status_icon} {rec['category']}: {rec['recommendation']}"
        )

    lines.extend(["", "=" * 70])

    return "\n".join(lines)


def main() -> int:
    """Função principal."""
    import argparse

    parser = argparse.ArgumentParser(
        description="GPU Profiler - ML Performance Analysis"
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument(
        "--profile", action="store_true", help="Run forward pass profiling"
    )
    parser.add_argument(
        "--memory", action="store_true", help="Memory snapshot only"
    )
    args = parser.parse_args()

    metrics = check_gpu_availability()
    profile_results = profile_model_forward() if args.profile else {}
    efficiency = analyze_training_efficiency()

    if args.json:
        output = {
            "gpu": {
                "available": metrics.gpu_available,
                "device": metrics.device_name,
                "memory_gb": metrics.total_memory_gb,
            },
            "profiling": profile_results,
            "efficiency": efficiency,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        print(json.dumps(output, indent=2))
    elif args.memory:
        print(json.dumps(get_memory_snapshot(), indent=2))
    else:
        print(format_report(metrics, profile_results, efficiency))

    return 0


if __name__ == "__main__":
    sys.exit(main())
