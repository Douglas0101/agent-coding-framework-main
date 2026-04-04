"""Hybrid Core Configuration.

Manages feature flags and configuration for the Hybrid Core 1x/2x system.
Supports environment variable based configuration (opencode does not support
custom config fields in opencode.json due to schema validation).

Usage:
    export OPENCODE_HYBRID_CORE=enabled  # enables hybrid core
    export OPENCODE_HYBRID_CORE=disabled # disabled (default)
    export OPENCODE_TARGET_ACCURACY=0.95  # optional target accuracy
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

HYBRID_CORE_ENV_VAR = "OPENCODE_HYBRID_CORE"
TARGET_ACCURACY_ENV_VAR = "OPENCODE_TARGET_ACCURACY"


@dataclass
class HybridCoreConfig:
    """Configuration for Hybrid Core execution."""

    enabled: bool = False
    target_accuracy: float = 0.95

    def is_enabled(self) -> bool:
        """Check if hybrid core is enabled."""
        return self.enabled


def load_hybrid_core_config() -> HybridCoreConfig:
    """Load hybrid core configuration from environment variables.

    Returns:
        HybridCoreConfig with settings from environment.
    """
    env_value = os.environ.get(HYBRID_CORE_ENV_VAR, "disabled").lower()

    enabled = env_value in ("enabled", "true", "1", "yes")

    accuracy_str = os.environ.get(TARGET_ACCURACY_ENV_VAR, "0.95")
    try:
        target_accuracy = float(accuracy_str)
    except ValueError:
        target_accuracy = 0.95

    return HybridCoreConfig(
        enabled=enabled,
        target_accuracy=target_accuracy,
    )


def get_hybrid_core_config() -> HybridCoreConfig:
    """Get cached hybrid core configuration.

    Returns:
        Singleton HybridCoreConfig instance.
    """
    global _config
    if _config is None:
        _config = load_hybrid_core_config()
    return _config


def is_hybrid_core_enabled() -> bool:
    """Check if hybrid core is enabled via environment variable.

    Returns:
        True if OPENCODE_HYBRID_CORE=enabled|true|1|yes
    """
    return get_hybrid_core_config().is_enabled()


def get_target_accuracy() -> float:
    """Get target accuracy from environment variable.

    Returns:
        Target accuracy (default 0.95)
    """
    return get_hybrid_core_config().target_accuracy


def reset_config():
    """Reset cached configuration (useful for testing)."""
    global _config
    _config = None


_config: HybridCoreConfig | None = None
