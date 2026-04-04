"""Regression Harness — Hybrid Core 1x/2x test scenarios.

Runs a comprehensive suite of scenarios to validate scope detection,
profile activation, gate execution, and over/under-engineering prevention.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from .scope_detector import ScopeDetector
    from .profile_activator import ProfileActivator
    from .gate_executor import GateExecutor
    from .output_validator import OutputValidator
except ImportError:  # pragma: no cover - standalone script/test compatibility
    from scope_detector import ScopeDetector
    from profile_activator import ProfileActivator
    from gate_executor import GateExecutor
    from output_validator import OutputValidator

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SPEC_PATH = REPO_ROOT / ".internal" / "specs" / "core" / "scope-detection-engine.yaml"
ALGO_MAP_PATH = (
    REPO_ROOT
    / ".internal"
    / "domains"
    / "ioi-gold-compiler"
    / "algorithm-selection-map.yaml"
)
EXEC_PROFILES_PATH = (
    REPO_ROOT / ".internal" / "specs" / "core" / "execution-profiles.yaml"
)
ADAPTERS_DIR = REPO_ROOT / ".internal" / "modes" / "autocoder" / "adapters"


@dataclass
class Scenario:
    """A single regression test scenario."""

    id: str
    description: str
    task_input: str
    expected_tier: str
    expected_profile: str
    source_code: str = ""
    code_output: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)


@dataclass
class RegressionResult:
    """Result of a single scenario execution."""

    scenario_id: str
    expected_tier: str
    actual_tier: str
    expected_profile: str
    actual_profile: str
    passed: bool
    details: str = ""
    gate_status: str = ""
    validation_valid: bool = True


class RegressionHarness:
    """Runs regression scenarios for Hybrid Core 1x/2x."""

    def __init__(self):
        self.scope_detector = ScopeDetector(
            spec_path=SPEC_PATH, algorithm_map_path=ALGO_MAP_PATH
        )
        self.profile_activator = ProfileActivator(
            spec_path=EXEC_PROFILES_PATH, adapters_dir=ADAPTERS_DIR
        )
        self.gate_executor = GateExecutor()
        self.output_validator = OutputValidator()
        self._scenarios = self._build_scenarios()

    def _build_scenarios(self) -> list[Scenario]:
        return [
            # ── Tier 1: General Engineering ──
            Scenario(
                id="REG-001",
                description="CRUD endpoint — should stay 1x",
                task_input="Create a REST API endpoint for user registration with email validation",
                expected_tier="tier_1_universal",
                expected_profile="default_1x",
                tags=["tier1", "crud"],
            ),
            Scenario(
                id="REG-002",
                description="Refactor naming — should stay 1x",
                task_input="Refactor the authentication module to use consistent naming conventions",
                expected_tier="tier_1_universal",
                expected_profile="default_1x",
                tags=["tier1", "refactor"],
            ),
            Scenario(
                id="REG-003",
                description="Background worker — should stay 1x",
                task_input="Create a background job to send email notifications via SMTP",
                expected_tier="tier_1_universal",
                expected_profile="default_1x",
                tags=["tier1", "worker"],
            ),
            Scenario(
                id="REG-004",
                description="Database migration — should stay 1x",
                task_input="Add a migration to add email_verified boolean column to users table",
                expected_tier="tier_1_universal",
                expected_profile="default_1x",
                tags=["tier1", "migration"],
            ),
            # ── Tier 2: Algorithmic ──
            Scenario(
                id="REG-005",
                description="Range query with large n — should escalate to 2x",
                task_input="Range minimum query with updates, n=200000",
                expected_tier="tier_2_algorithmic",
                expected_profile="performance_2x",
                tags=["tier2", "range_query"],
            ),
            Scenario(
                id="REG-006",
                description="Graph shortest path — should escalate to 2x",
                task_input="Find shortest path in graph with 150000 nodes and non-negative weights",
                expected_tier="tier_2_algorithmic",
                expected_profile="performance_2x",
                tags=["tier2", "graph"],
            ),
            Scenario(
                id="REG-007",
                description="Large queries — should escalate to 2x",
                task_input="Process 200000 queries on an array efficiently",
                expected_tier="tier_2_algorithmic",
                expected_profile="performance_2x",
                tags=["tier2", "queries"],
            ),
            Scenario(
                id="REG-008",
                description="SCC detection — should escalate to 2x",
                task_input="Find strongly connected components in a directed graph",
                expected_tier="tier_2_algorithmic",
                expected_profile="performance_2x",
                tags=["tier2", "graph"],
            ),
            # ── Tier 3: Competitive/Frontier ──
            Scenario(
                id="REG-009",
                description="Link-Cut Tree — should escalate to 2x Tier 3",
                task_input="Dynamic forest with link/cut operations and path maximum query",
                expected_tier="tier_3_competitive",
                expected_profile="performance_2x",
                tags=["tier3", "lct"],
            ),
            Scenario(
                id="REG-010",
                description="Eertree — should escalate to 2x Tier 3",
                task_input="Count distinct palindromic substrings using eertree",
                expected_tier="tier_3_competitive",
                expected_profile="performance_2x",
                tags=["tier3", "eertree"],
            ),
            Scenario(
                id="REG-011",
                description="IOI-grade problem — should escalate to 2x Tier 3",
                task_input="IOI-grade problem: dynamic tree with path queries, n=10^5",
                expected_tier="tier_3_competitive",
                expected_profile="performance_2x",
                tags=["tier3", "ioi"],
            ),
            Scenario(
                id="REG-012",
                description="Suffix Automaton — should escalate to 2x Tier 3",
                task_input="Build a suffix automaton for longest common substring of two strings",
                expected_tier="tier_3_competitive",
                expected_profile="performance_2x",
                tags=["tier3", "suffix"],
            ),
            # ── False Positive Prevention ──
            Scenario(
                id="REG-FP-001",
                description="'Fast' in non-technical context — should NOT escalate",
                task_input="Create a fast API endpoint for health check",
                expected_tier="tier_1_universal",
                expected_profile="default_1x",
                tags=["fp", "non_technical"],
            ),
            Scenario(
                id="REG-FP-002",
                description="Quick pagination — should NOT escalate",
                task_input="Add quick pagination to the user list page",
                expected_tier="tier_1_universal",
                expected_profile="default_1x",
                tags=["fp", "pagination"],
            ),
            Scenario(
                id="REG-FP-003",
                description="CRUD with no constraints — should NOT escalate",
                task_input="Create REST API for user CRUD operations",
                expected_tier="tier_1_universal",
                expected_profile="default_1x",
                tags=["fp", "crud"],
            ),
            # ── Over-Engineering Detection ──
            Scenario(
                id="REG-OE-001",
                description="LCT for CRUD — should flag over-engineering",
                task_input="Create a simple CRUD endpoint for user management",
                expected_tier="tier_1_universal",
                expected_profile="default_1x",
                tags=["over_engineering"],
            ),
            # ── Under-Engineering Detection ──
            Scenario(
                id="REG-UE-001",
                description="O(n²) for n=200000 — should flag under-engineering",
                task_input="Range minimum query with updates, n=200000",
                expected_tier="tier_2_algorithmic",
                expected_profile="performance_2x",
                tags=["under_engineering"],
            ),
        ]

    def run_all(self) -> list[RegressionResult]:
        """Run all regression scenarios."""
        results = []
        for scenario in self._scenarios:
            result = self._run_scenario(scenario)
            results.append(result)
        return results

    def run_by_tag(self, tag: str) -> list[RegressionResult]:
        """Run scenarios matching a specific tag."""
        results = []
        for scenario in self._scenarios:
            if tag in scenario.tags:
                results.append(self._run_scenario(scenario))
        return results

    def run_tier(self, tier: str) -> list[RegressionResult]:
        """Run scenarios for a specific tier."""
        return self.run_by_tag(tier)

    def run_false_positives(self) -> list[RegressionResult]:
        """Run false positive prevention scenarios."""
        return self.run_by_tag("fp")

    def run_over_engineering(self) -> list[RegressionResult]:
        """Run over-engineering detection scenarios."""
        return self.run_by_tag("over_engineering")

    def run_under_engineering(self) -> list[RegressionResult]:
        """Run under-engineering detection scenarios."""
        return self.run_by_tag("under_engineering")

    def _run_scenario(self, scenario: Scenario) -> RegressionResult:
        """Run a single scenario and compare results."""
        scope_result = self.scope_detector.classify(scenario.task_input)
        active_profile = self.profile_activator.activate(scope_result.tier)

        gate_report = self.gate_executor.execute_all(
            code_output=scenario.code_output,
            is_2x=active_profile.is_2x(),
            source_code=scenario.source_code,
        )

        output_validation = self.output_validator.validate(
            output=scenario.code_output,
            profile=active_profile.profile,
            tier=active_profile.tier,
        )

        tier_match = scope_result.tier == scenario.expected_tier
        profile_match = active_profile.profile == scenario.expected_profile
        passed = tier_match and profile_match

        details = []
        if not tier_match:
            details.append(
                f"Tier mismatch: expected={scenario.expected_tier}, actual={scope_result.tier}"
            )
        if not profile_match:
            details.append(
                f"Profile mismatch: expected={scenario.expected_profile}, actual={active_profile.profile}"
            )

        return RegressionResult(
            scenario_id=scenario.id,
            expected_tier=scenario.expected_tier,
            actual_tier=scope_result.tier,
            expected_profile=scenario.expected_profile,
            actual_profile=active_profile.profile,
            passed=passed,
            details="; ".join(details) if details else "OK",
            gate_status=gate_report.overall_status,
            validation_valid=output_validation.valid,
        )

    def get_summary(self, results: list[RegressionResult]) -> dict:
        """Get a summary of regression results."""
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed

        failed_details = [
            {"id": r.scenario_id, "details": r.details} for r in results if not r.passed
        ]

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": round(passed / total, 3) if total > 0 else 0.0,
            "failed_scenarios": failed_details,
        }
