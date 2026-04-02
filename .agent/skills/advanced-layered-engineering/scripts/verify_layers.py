#!/usr/bin/env python3
"""
Unified layer verification script for Advanced Layered Engineering.

Validates code and configuration across all 6 layers:
- L1: PEP Foundation (Ruff)
- L2: Type System (MyPy)
- L3: Hardware Profiling
- L4: Memory Architecture (Pre-flight)
- L5: Parallel Processing
- L6: Deep Optimization

Usage:
    python verify_layers.py --all
    python verify_layers.py --layer 1
    python verify_layers.py --preflight
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class LayerResult:
    """Result of a layer verification."""

    layer: int
    name: str
    passed: bool
    message: str
    score: int = 100


def run_layer_1() -> LayerResult:
    """Layer 1: PEP Foundation - Ruff lint check."""
    try:
        result = subprocess.run(
            ["ruff", "check", "src/", "--select", "E,W,F,I,N"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        passed = result.returncode == 0
        if passed:
            message = "✅ Zero lint errors"
        else:
            lines = result.stdout.strip().split("\n")
            error_count = len([line for line in lines if line.strip()])
            message = f"❌ {error_count} lint issues found"
        return LayerResult(
            1, "PEP Foundation", passed, message, 100 if passed else 60
        )
    except FileNotFoundError:
        return LayerResult(
            1, "PEP Foundation", False, "⚠️ Ruff not installed", 0
        )
    except subprocess.TimeoutExpired:
        return LayerResult(1, "PEP Foundation", False, "⚠️ Timeout", 0)


def run_layer_2() -> LayerResult:
    """Layer 2: Type System - MyPy strict check."""
    try:
        result = subprocess.run(
            ["mypy", "src/", "--strict", "--ignore-missing-imports"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        passed = result.returncode == 0
        if passed:
            message = "✅ No type errors"
        else:
            lines = result.stdout.strip().split("\n")
            error_count = len([line for line in lines if "error:" in line])
            message = f"❌ {error_count} type errors found"
        return LayerResult(
            2, "Type System", passed, message, 100 if passed else 50
        )
    except FileNotFoundError:
        return LayerResult(2, "Type System", False, "⚠️ MyPy not installed", 0)
    except subprocess.TimeoutExpired:
        return LayerResult(2, "Type System", False, "⚠️ Timeout", 0)


def run_layer_3() -> LayerResult:
    """Layer 3: Hardware Profiling - Detect and report."""
    try:
        # Import hardware intelligence
        sys.path.insert(0, ".")
        from src.config.hardware_intel import HardwareIntelligence

        hw = HardwareIntelligence()
        snapshot = hw.snapshot()

        details = []
        if snapshot.gpu_available:
            details.append(f"GPU: {snapshot.gpu_name}")
            if snapshot.gpu_vram_total_gb:
                details.append(f"VRAM: {snapshot.gpu_vram_total_gb:.1f}GB")
            score = 100
        else:
            details.append(f"CPU: {snapshot.cpu_cores} cores")
            details.append(f"RAM: {snapshot.ram_total_gb:.1f}GB")
            score = 70

        message = "✅ " + " | ".join(details)
        return LayerResult(3, "Hardware Profiling", True, message, score)

    except ImportError as e:
        return LayerResult(
            3, "Hardware Profiling", False, f"⚠️ Import error: {e}", 0
        )
    except Exception as e:
        return LayerResult(3, "Hardware Profiling", False, f"❌ Error: {e}", 0)


def run_layer_4(batch_size: int = 32, epochs: int = 10) -> LayerResult:
    """Layer 4: Memory Architecture - Pre-flight validation."""
    try:
        sys.path.insert(0, ".")
        from src.config.hardware_intel import run_preflight_checks

        result = run_preflight_checks(
            batch_size=batch_size,
            epochs=epochs,
            dataset_size=10000,
            strict=False,
            verbose=False,
        )

        if result.can_proceed:
            message = f"✅ Pre-flight OK (Score: {result.score}/100)"
        else:
            errors = ", ".join(result.errors[:2])
            message = f"❌ Pre-flight failed: {errors}"

        return LayerResult(
            4, "Memory Architecture", result.can_proceed, message, result.score
        )

    except ImportError as e:
        return LayerResult(
            4, "Memory Architecture", False, f"⚠️ Import error: {e}", 0
        )
    except Exception as e:
        return LayerResult(
            4, "Memory Architecture", False, f"❌ Error: {e}", 0
        )


def run_layer_5() -> LayerResult:
    """Layer 5: Parallel Processing - Validate DataLoader config."""
    try:
        sys.path.insert(0, ".")
        from src.config.hardware import get_dataloader_kwargs, get_profile

        profile = get_profile("auto")
        kwargs = get_dataloader_kwargs(profile)

        checks = []
        score = 100

        # Check num_workers
        if kwargs.get("num_workers", 0) > 0:
            checks.append(f"workers={kwargs['num_workers']}")
        else:
            checks.append("workers=0 (single-threaded)")
            score -= 20

        # Check pin_memory
        if kwargs.get("pin_memory", False):
            checks.append("pin_memory=True")
        else:
            if profile.device == "cuda":
                score -= 15
            checks.append("pin_memory=False")

        # Check prefetch
        if "prefetch_factor" in kwargs:
            checks.append(f"prefetch={kwargs['prefetch_factor']}")

        message = "✅ " + " | ".join(checks)
        return LayerResult(5, "Parallel Processing", True, message, score)

    except Exception as e:
        return LayerResult(
            5, "Parallel Processing", False, f"❌ Error: {e}", 0
        )


def run_layer_6() -> LayerResult:
    """Layer 6: Deep Optimization - Check torch.compile availability."""
    try:
        import torch

        checks = []
        score = 100

        # Check torch version
        version = torch.__version__
        major_version = int(version.split(".")[0])
        if major_version >= 2:
            checks.append(f"PyTorch {version} (compile supported)")
        else:
            checks.append(f"PyTorch {version} (compile NOT supported)")
            score -= 30

        # Check CUDA availability
        if torch.cuda.is_available():
            checks.append("CUDA available")
            # Check compute capability for Tensor Cores
            props = torch.cuda.get_device_properties(0)
            if props.major >= 7:
                checks.append("Tensor Cores (AMP optimal)")
            else:
                checks.append("No Tensor Cores")
                score -= 10
        else:
            checks.append("CPU-only")
            score -= 20

        message = "✅ " + " | ".join(checks)
        return LayerResult(6, "Deep Optimization", True, message, score)

    except Exception as e:
        return LayerResult(6, "Deep Optimization", False, f"❌ Error: {e}", 0)


# Registry of layer functions
LAYER_FUNCTIONS: dict[int, Callable[[], LayerResult]] = {
    1: run_layer_1,
    2: run_layer_2,
    3: run_layer_3,
    4: run_layer_4,
    5: run_layer_5,
    6: run_layer_6,
}


def print_results(results: list[LayerResult]) -> int:
    """Print results and return exit code."""
    print("\n" + "=" * 60)
    print("🔬 ADVANCED LAYERED ENGINEERING - VERIFICATION REPORT")
    print("=" * 60 + "\n")

    total_score = 0
    all_passed = True

    for r in results:
        print(f"  L{r.layer}: {r.name}")
        print(f"      {r.message}")
        print(f"      Score: {r.score}/100")
        print()
        total_score += r.score
        if not r.passed:
            all_passed = False

    avg_score = total_score // len(results) if results else 0
    print("-" * 60)
    print(f"  📊 Overall Score: {avg_score}/100")
    print(f"  📋 Status: {'READY' if all_passed else 'NEEDS ATTENTION'}")
    print("=" * 60 + "\n")

    return 0 if all_passed else 1


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify code across 6 engineering layers"
    )
    parser.add_argument("--all", action="store_true", help="Run all layers")
    parser.add_argument(
        "--layer",
        type=int,
        choices=[1, 2, 3, 4, 5, 6],
        help="Run specific layer",
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Run pre-flight check (Layer 4)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=32, help="Batch size for pre-flight"
    )
    parser.add_argument(
        "--epochs", type=int, default=10, help="Epochs for pre-flight"
    )

    args = parser.parse_args()

    results: list[LayerResult] = []

    if args.preflight:
        results.append(run_layer_4(args.batch_size, args.epochs))
    elif args.layer:
        if args.layer == 4:
            results.append(run_layer_4(args.batch_size, args.epochs))
        else:
            results.append(LAYER_FUNCTIONS[args.layer]())
    elif args.all:
        for layer_num in sorted(LAYER_FUNCTIONS.keys()):
            if layer_num == 4:
                results.append(run_layer_4(args.batch_size, args.epochs))
            else:
                results.append(LAYER_FUNCTIONS[layer_num]())
    else:
        parser.print_help()
        return 0

    return print_results(results)


if __name__ == "__main__":
    sys.exit(main())
