#!/usr/bin/env python3
"""
Hardware Optimization Example for Advanced Layered Engineering.

Demonstrates practical usage of all 6 layers:
- Layer 1-2: Code quality (assumed passing)
- Layer 3: Hardware detection and profile selection
- Layer 4: Pre-flight validation and memory estimation
- Layer 5: Optimal DataLoader configuration
- Layer 6: torch.compile and mixed precision

Usage:
    python hardware_optimization.py
"""

import sys

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset


# Add project root to path
sys.path.insert(0, ".")

from src.config.hardware import (
    get_dataloader_kwargs,
    get_profile,
    optimize_model_for_hardware,
    print_hardware_info,
)
from src.config.hardware_intel import (
    HardwareIntelligence,
    ThermalGuard,
    run_preflight_checks,
)


def create_dummy_model() -> nn.Module:
    """Create a simple CNN for demonstration."""
    return nn.Sequential(
        nn.Conv2d(3, 32, 3, padding=1),
        nn.ReLU(),
        nn.MaxPool2d(2),
        nn.Conv2d(32, 64, 3, padding=1),
        nn.ReLU(),
        nn.MaxPool2d(2),
        nn.Flatten(),
        nn.Linear(64 * 56 * 56, 256),
        nn.ReLU(),
        nn.Linear(256, 14),  # 14 classes for NIH dataset
    )


def create_dummy_data(batch_size: int, num_samples: int = 1000) -> DataLoader:
    """Create dummy data for demonstration."""
    images = torch.randn(num_samples, 3, 224, 224)
    labels = torch.randint(0, 14, (num_samples,))
    dataset = TensorDataset(images, labels)
    return dataset


def main() -> None:
    """Run hardware optimization demonstration."""
    print("\n" + "=" * 70)
    print("🔬 ADVANCED LAYERED ENGINEERING - HARDWARE OPTIMIZATION DEMO")
    print("=" * 70)

    # =========================================================================
    # Layer 3: Hardware Detection
    # =========================================================================
    print("\n📡 LAYER 3: Hardware Detection")
    print("-" * 50)

    hw = HardwareIntelligence()
    hw.print_report()

    # Get optimal profile
    profile = get_profile("auto")
    print_hardware_info(profile)

    # =========================================================================
    # Layer 4: Pre-flight Validation
    # =========================================================================
    print("\n✈️  LAYER 4: Pre-flight Validation")
    print("-" * 50)

    preflight = run_preflight_checks(
        batch_size=profile.batch_size,
        epochs=5,
        dataset_size=10000,
        verbose=True,
    )

    if not preflight.can_proceed:
        print("⚠️  Pre-flight failed! Adjusting configuration...")
        # Use recommended batch size
        if preflight.estimate:
            profile.batch_size = preflight.estimate.recommended_batch_size
            print(f"   Adjusted batch_size to {profile.batch_size}")

    # =========================================================================
    # Layer 5: Parallel Processing Setup
    # =========================================================================
    print("\n⚡ LAYER 5: DataLoader Configuration")
    print("-" * 50)

    dataloader_kwargs = get_dataloader_kwargs(profile)
    print(f"   num_workers: {dataloader_kwargs.get('num_workers', 0)}")
    print(f"   pin_memory: {dataloader_kwargs.get('pin_memory', False)}")
    print(
        f"   prefetch_factor: {dataloader_kwargs.get('prefetch_factor', 'N/A')}"
    )
    print(
        f"   persistent_workers: {dataloader_kwargs.get('persistent_workers', False)}"
    )

    # Create dummy dataset and loader
    dataset = create_dummy_data(profile.batch_size)
    train_loader = DataLoader(
        dataset,
        batch_size=profile.batch_size,
        shuffle=True,
        **dataloader_kwargs,
    )
    print(f"\n   ✅ DataLoader created with {len(train_loader)} batches")

    # =========================================================================
    # Layer 6: Deep Optimization
    # =========================================================================
    print("\n🚀 LAYER 6: Model Optimization")
    print("-" * 50)

    model = create_dummy_model()
    print(
        f"   Original model parameters: {sum(p.numel() for p in model.parameters()):,}"
    )

    # Apply hardware optimizations
    model = optimize_model_for_hardware(model, profile)

    # torch.compile (if available)
    if profile.compile_model and hasattr(torch, "compile"):
        try:
            model = torch.compile(model, mode=profile.compile_mode)
            print(
                f"   ✅ torch.compile() applied (mode={profile.compile_mode})"
            )
        except Exception as e:
            print(f"   ⚠️  torch.compile() failed: {e}")

    # Mixed Precision setup
    if profile.mixed_precision:
        print("   ✅ Mixed Precision (AMP) enabled")
        scaler = torch.cuda.amp.GradScaler()
    else:
        print("   [i] Mixed Precision disabled (CPU mode)")
        scaler = None

    # =========================================================================
    # Demonstration Training Loop
    # =========================================================================
    print("\n🔄 DEMO: Training Loop (1 epoch)")
    print("-" * 50)

    device = profile.get_device()
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)

    # ThermalGuard for CPU
    thermal_guard = None
    if profile.device == "cpu":
        thermal_guard = ThermalGuard(cpu_threads=2, sleep_ms=5)
        print("   🌡️  ThermalGuard activated for CPU")

    model.train()
    total_loss = 0.0
    num_batches = min(5, len(train_loader))  # Demo: only 5 batches

    for i, (images, labels) in enumerate(train_loader):
        if i >= num_batches:
            break

        # Non-blocking transfer (Layer 5)
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)

        optimizer.zero_grad()

        # Mixed precision context (Layer 6)
        if scaler is not None:
            with torch.cuda.amp.autocast(dtype=torch.float16):
                outputs = model(images)
                loss = criterion(outputs, labels)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
        else:
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

        total_loss += loss.item()

        # Thermal throttling (Layer 4)
        if thermal_guard:
            thermal_guard.sleep_between_batches()

        print(f"   Batch {i + 1}/{num_batches}: loss={loss.item():.4f}")

    print(f"\n   ✅ Average loss: {total_loss / num_batches:.4f}")

    # Cleanup
    if thermal_guard:
        thermal_guard.restore_threads()

    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "=" * 70)
    print("📊 OPTIMIZATION SUMMARY")
    print("=" * 70)
    print(f"   Profile: {profile.name}")
    print(f"   Device: {profile.device}")
    print(f"   Batch Size: {profile.batch_size}")
    print(f"   Workers: {profile.num_workers}")
    print(f"   Mixed Precision: {profile.mixed_precision}")
    print(f"   Compiled: {profile.compile_model}")
    print(f"   Pre-flight Score: {preflight.score}/100")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
