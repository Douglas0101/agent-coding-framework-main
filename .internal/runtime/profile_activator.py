"""Profile Activator — Runtime implementation.

Loads and applies the correct execution profile based on scope detection
results. Resolves adapter configurations, injects contract references,
and validates activation consistency.

Spec: .internal/specs/core/execution-profiles.yaml
Adapters: .internal/modes/autocoder/adapters/
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
EXEC_PROFILES_PATH = (
    REPO_ROOT / ".internal" / "specs" / "core" / "execution-profiles.yaml"
)
ADAPTERS_DIR = REPO_ROOT / ".internal" / "modes" / "autocoder" / "adapters"

TIER_TO_ADAPTER = {
    "tier_1_universal": "default-1x.yaml",
    "tier_2_algorithmic": "performance-2x-tier-2.yaml",
    "tier_3_competitive": "performance-2x-tier-3.yaml",
}


@dataclass
class ActiveProfile:
    """Resolved execution profile ready for use by the engine."""

    profile: str
    tier: str
    adapter_config: dict[str, Any] = field(default_factory=dict)
    active_contracts: list[str] = field(default_factory=list)
    quality_threshold: float = 0.80
    early_exit: bool = True
    satisficing: str = "BALANCED"
    output_schema: list[str] = field(default_factory=list)
    required_artifacts: list[str] = field(default_factory=list)
    instructions: str = ""
    activation_violations: list[str] = field(default_factory=list)

    def is_2x(self) -> bool:
        return self.profile == "performance_2x"

    def is_1x(self) -> bool:
        return self.profile == "default_1x"


class ProfileActivator:
    """Loads and validates execution profile activation.

    Takes a scope classification result and produces an ActiveProfile
    with all contracts, instructions, and configuration resolved.
    """

    def __init__(
        self,
        spec_path: Path | None = None,
        adapters_dir: Path | None = None,
    ):
        self._spec_path = spec_path or EXEC_PROFILES_PATH
        self._adapters_dir = adapters_dir or ADAPTERS_DIR
        self._spec = self._load_spec()

    def _load_spec(self) -> dict:
        if not self._spec_path.exists():
            raise FileNotFoundError(
                f"Execution profiles spec not found: {self._spec_path}"
            )
        return yaml.safe_load(self._spec_path.read_text(encoding="utf-8"))

    def activate(self, tier: str, profile: str | None = None) -> ActiveProfile:
        """Activate an execution profile for the given tier.

        Args:
            tier: One of tier_1_universal, tier_2_algorithmic, tier_3_competitive.
            profile: Override profile (default: inferred from tier).

        Returns:
            ActiveProfile with all configuration resolved.

        Raises:
            ValueError: If tier is unknown.
        """
        if tier not in TIER_TO_ADAPTER:
            raise ValueError(
                f"Unknown tier: {tier}. Must be one of {list(TIER_TO_ADAPTER.keys())}"
            )

        adapter_file = TIER_TO_ADAPTER[tier]
        adapter_path = self._adapters_dir / adapter_file

        adapter_config = (
            self._load_adapter(adapter_path) if adapter_path.exists() else {}
        )

        profile_name = profile or adapter_config.get("profile", "default_1x")
        profile_spec = self._spec.get("profiles", {}).get(profile_name, {})

        contracts = self._resolve_contracts(adapter_config)
        output_schema = self._resolve_output_schema(profile_spec, adapter_config)
        required_artifacts = profile_spec.get("requires", [])
        instructions = adapter_config.get("context_injection", {}).get(
            "instructions", ""
        )
        quality_threshold = adapter_config.get(
            "quality_threshold", profile_spec.get("quality_threshold", 0.80)
        )
        early_exit = adapter_config.get(
            "early_exit", profile_spec.get("early_exit", True)
        )
        satisficing = profile_spec.get("satisficing", "BALANCED")

        violations = self._validate_activation(
            tier, profile_name, adapter_config, profile_spec
        )

        return ActiveProfile(
            profile=profile_name,
            tier=tier,
            adapter_config=adapter_config,
            active_contracts=contracts,
            quality_threshold=quality_threshold,
            early_exit=early_exit,
            satisficing=satisficing,
            output_schema=output_schema,
            required_artifacts=required_artifacts,
            instructions=instructions,
            activation_violations=violations,
        )

    def validate_activation(self, active_profile: ActiveProfile) -> list[str]:
        """Validate an already-activated profile for consistency.

        Returns a list of violation strings (empty if valid).
        """
        violations = list(active_profile.activation_violations)

        if active_profile.is_2x() and active_profile.quality_threshold < 0.90:
            violations.append(
                f"2x profile quality_threshold {active_profile.quality_threshold} < 0.90"
            )

        if active_profile.is_1x() and active_profile.quality_threshold > 0.85:
            violations.append(
                f"1x profile quality_threshold {active_profile.quality_threshold} > 0.85"
            )

        if active_profile.is_2x():
            nou_required = {
                "universal_quality_core",
            }
            activates = set(
                self._spec.get("profiles", {})
                .get("performance_2x", {})
                .get("activates", [])
            )
            if not nou_required.issubset(activates):
                violations.append("2x profile does not activate universal_quality_core")

        if not active_profile.active_contracts:
            violations.append("No contracts loaded for profile activation")

        return violations

    def _load_adapter(self, path: Path) -> dict:
        try:
            return yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            return {}

    def _resolve_contracts(self, adapter_config: dict) -> list[str]:
        context = adapter_config.get("context_injection", {})
        return context.get("contracts", [])

    def _resolve_output_schema(
        self, profile_spec: dict, adapter_config: dict
    ) -> list[str]:
        adapter_schema = adapter_config.get("output_schema", {})
        if isinstance(adapter_schema, dict):
            fields = adapter_schema.get("required_fields", [])
            return [f.get("name", "") for f in fields if isinstance(f, dict)]
        if isinstance(adapter_schema, list):
            return adapter_schema
        return profile_spec.get("output_schema", [])

    def _validate_activation(
        self,
        tier: str,
        profile: str,
        adapter_config: dict,
        profile_spec: dict,
    ) -> list[str]:
        violations = []

        adapter_tier = adapter_config.get("tier", "")
        if adapter_tier and adapter_tier != tier:
            violations.append(f"Tier mismatch: scope={tier}, adapter={adapter_tier}")

        adapter_profile = adapter_config.get("profile", "")
        if adapter_profile and adapter_profile != profile:
            violations.append(
                f"Profile mismatch: requested={profile}, adapter={adapter_profile}"
            )

        if profile == "performance_2x":
            activates = profile_spec.get("activates", [])
            if "universal_quality_core" not in activates:
                violations.append(
                    "2x profile missing universal_quality_core activation"
                )
            if "algorithmic_frontier_core" not in activates:
                violations.append(
                    "2x profile missing algorithmic_frontier_core activation"
                )

        return violations

    def get_available_profiles(self) -> dict[str, dict]:
        """Return all available profiles from the spec."""
        return self._spec.get("profiles", {})

    def get_precedence_rules(self) -> list[str]:
        """Return precedence rules for conflict resolution."""
        return self._spec.get("precedence", {}).get("rules", [])

    def get_activation_policy(self) -> dict:
        """Return the activation policy configuration."""
        return self._spec.get("activation_policy", {})
