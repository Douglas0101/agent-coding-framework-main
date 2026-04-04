"""Tests for Hybrid Core Configuration."""

from __future__ import annotations

import os
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestHybridCoreConfig:
    """Tests for hybrid core configuration via environment variables."""

    def test_default_disabled(self):
        """Test that hybrid core is disabled by default."""
        os.environ.pop("OPENCODE_HYBRID_CORE", None)
        os.environ.pop("OPENCODE_TARGET_ACCURACY", None)

        # Reset config cache
        import runtime.hybrid_core_config as hcc

        hcc.reset_config()

        config = hcc.load_hybrid_core_config()
        assert config.enabled is False
        assert config.target_accuracy == 0.95

    def test_enabled_via_env(self):
        """Test that hybrid core can be enabled via environment variable."""
        os.environ["OPENCODE_HYBRID_CORE"] = "enabled"

        import runtime.hybrid_core_config as hcc

        hcc.reset_config()

        config = hcc.load_hybrid_core_config()
        assert config.enabled is True

    def test_enabled_via_true(self):
        """Test that hybrid core can be enabled via true."""
        os.environ["OPENCODE_HYBRID_CORE"] = "true"

        import runtime.hybrid_core_config as hcc

        hcc.reset_config()

        config = hcc.load_hybrid_core_config()
        assert config.enabled is True

    def test_enabled_via_1(self):
        """Test that hybrid core can be enabled via 1."""
        os.environ["OPENCODE_HYBRID_CORE"] = "1"

        import runtime.hybrid_core_config as hcc

        hcc.reset_config()

        config = hcc.load_hybrid_core_config()
        assert config.enabled is True

    def test_disabled_via_env(self):
        """Test that hybrid core can be explicitly disabled."""
        os.environ["OPENCODE_HYBRID_CORE"] = "disabled"

        import runtime.hybrid_core_config as hcc

        hcc.reset_config()

        config = hcc.load_hybrid_core_config()
        assert config.enabled is False

    def test_custom_accuracy(self):
        """Test that custom target accuracy can be set."""
        os.environ["OPENCODE_TARGET_ACCURACY"] = "0.85"

        import runtime.hybrid_core_config as hcc

        hcc.reset_config()

        config = hcc.load_hybrid_core_config()
        assert config.target_accuracy == 0.85

    def test_invalid_accuracy_defaults(self):
        """Test that invalid accuracy value defaults to 0.95."""
        os.environ["OPENCODE_TARGET_ACCURACY"] = "invalid"

        import runtime.hybrid_core_config as hcc

        hcc.reset_config()

        config = hcc.load_hybrid_core_config()
        assert config.target_accuracy == 0.95
