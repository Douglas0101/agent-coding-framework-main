"""
Regression tests for stable agent execution.
Covers: loop prevention, retry limits, resume, write_scope isolation,
command routing, handoff validation, and forbidden transitions.
"""

import json
import os
import time
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
OPENCODE_CONFIG = REPO_ROOT / "opencode.json"
OPENCODE_DOT_CONFIG = REPO_ROOT / ".opencode" / "opencode.json"
COMMANDS_DIR = REPO_ROOT / ".opencode" / "commands"
SPECS_DIR = REPO_ROOT / ".opencode" / "specs"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def _load_yaml(path: Path) -> dict:
    """Minimal YAML loader for the spec files (no external dependency)."""
    # For these tests we parse the key/value pairs we need manually
    # to avoid requiring PyYAML at runtime.
    result: dict = {}
    current_key = None
    with open(path, "r") as f:
        for line in f:
            stripped = line.rstrip()
            if not stripped or stripped.startswith("#"):
                continue
            if ":" in stripped and not stripped.startswith(" "):
                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                result[key] = value
                current_key = key
            elif stripped.startswith("  - ") and current_key == "invariants":
                result.setdefault("invariants_list", []).append(
                    stripped.strip("- ").strip('"')
                )
    return result


# ---------------------------------------------------------------------------
# 1. Config integrity tests
# ---------------------------------------------------------------------------


class TestConfigIntegrity(unittest.TestCase):
    """Ensure config files exist and are consistent."""

    def test_opencode_json_exists_in_dot_opencode(self):
        """Root cause fix: .opencode/opencode.json must exist."""
        self.assertTrue(
            OPENCODE_DOT_CONFIG.exists(),
            f"Missing {OPENCODE_DOT_CONFIG} — causes silent routing failure",
        )

    def test_opencode_json_valid(self):
        config = _load_json(OPENCODE_DOT_CONFIG)
        self.assertIn("agent", config)
        self.assertIn("autocoder", config["agent"])

    def test_root_and_dot_opencode_configs_match(self):
        """Both config files must define the same agent map."""
        root = _load_json(OPENCODE_CONFIG)
        dot = _load_json(OPENCODE_DOT_CONFIG)
        root_agents = set(root.get("agent", {}).keys())
        dot_agents = set(dot.get("agent", {}).keys())
        self.assertEqual(
            root_agents,
            dot_agents,
            "Agent sets differ between opencode.json and .opencode/opencode.json",
        )

    def test_autocoder_max_steps_is_six(self):
        config = _load_json(OPENCODE_DOT_CONFIG)
        self.assertEqual(config["agent"]["autocoder"]["maxSteps"], 6)

    def test_doom_loop_denied_globally(self):
        config = _load_json(OPENCODE_DOT_CONFIG)
        self.assertEqual(config["permission"]["doom_loop"], "deny")

    def test_doom_loop_denied_per_agent(self):
        config = _load_json(OPENCODE_DOT_CONFIG)
        for agent_name, agent_cfg in config["agent"].items():
            self.assertEqual(
                agent_cfg["permission"]["doom_loop"],
                "deny",
                f"doom_loop not denied for agent '{agent_name}'",
            )


# ---------------------------------------------------------------------------
# 2. Command routing tests
# ---------------------------------------------------------------------------


class TestCommandRouting(unittest.TestCase):
    """Every command with agent: in frontmatter must map to a defined agent."""

    def _parse_frontmatter_agent(self, path: Path) -> str | None:
        """Extract agent from YAML frontmatter (--- block)."""
        in_fm = False
        for line in path.open():
            line = line.strip()
            if line == "---":
                if in_fm:
                    return None  # end of frontmatter
                in_fm = True
                continue
            if in_fm and line.startswith("agent:"):
                return line.split(":", 1)[1].strip()
        return None

    def setUp(self):
        self.config = _load_json(OPENCODE_DOT_CONFIG)
        self.known_agents = set(self.config["agent"].keys())

    def test_all_commands_have_defined_agent(self):
        for cmd_file in COMMANDS_DIR.glob("*.md"):
            agent = self._parse_frontmatter_agent(cmd_file)
            if agent:
                self.assertIn(
                    agent,
                    self.known_agents,
                    f"Command {cmd_file.name} maps to undefined agent '{agent}'",
                )

    def test_autocode_maps_to_autocoder(self):
        agent = self._parse_frontmatter_agent(COMMANDS_DIR / "autocode.md")
        self.assertEqual(agent, "autocoder")

    def test_ship_maps_to_orchestrator(self):
        agent = self._parse_frontmatter_agent(COMMANDS_DIR / "ship.md")
        self.assertEqual(agent, "orchestrator")

    def test_review_maps_to_reviewer(self):
        agent = self._parse_frontmatter_agent(COMMANDS_DIR / "review.md")
        self.assertEqual(agent, "reviewer")

    def test_analyze_maps_to_explore(self):
        agent = self._parse_frontmatter_agent(COMMANDS_DIR / "analyze.md")
        self.assertEqual(agent, "explore")

    def test_test_scope_maps_to_tester(self):
        agent = self._parse_frontmatter_agent(COMMANDS_DIR / "test-scope.md")
        self.assertEqual(agent, "tester")

    def test_ops_report_maps_to_autocoder(self):
        agent = self._parse_frontmatter_agent(COMMANDS_DIR / "ops-report.md")
        self.assertEqual(agent, "autocoder")


# ---------------------------------------------------------------------------
# 3. Spec existence and structure tests
# ---------------------------------------------------------------------------


class TestSpecStructure(unittest.TestCase):
    """Verify all required specs exist and contain mandatory fields."""

    def test_capability_spec_exists(self):
        path = SPECS_DIR / "capabilities" / "stable-execution.capability.yaml"
        self.assertTrue(path.exists(), f"Missing {path}")

    def test_behavior_spec_exists(self):
        path = SPECS_DIR / "behaviors" / "stable-execution.behavior.yaml"
        self.assertTrue(path.exists(), f"Missing {path}")

    def test_contract_spec_exists(self):
        path = SPECS_DIR / "contracts" / "agent-handoff.contract.yaml"
        self.assertTrue(path.exists(), f"Missing {path}")

    def test_policy_spec_exists(self):
        path = SPECS_DIR / "policies" / "stable-execution.policy.yaml"
        self.assertTrue(path.exists(), f"Missing {path}")

    def test_verification_spec_exists(self):
        path = SPECS_DIR / "verification" / "stable-execution.verification.yaml"
        self.assertTrue(path.exists(), f"Missing {path}")

    def test_release_spec_exists(self):
        path = SPECS_DIR / "release" / "stable-execution.release.yaml"
        self.assertTrue(path.exists(), f"Missing {path}")

    def test_capability_has_required_fields(self):
        path = SPECS_DIR / "capabilities" / "stable-execution.capability.yaml"
        content = path.read_text()
        for field in ("spec_id", "version", "status", "objective", "invariants"):
            self.assertIn(field, content, f"Capability spec missing field: {field}")

    def test_behavior_has_states_and_transitions(self):
        path = SPECS_DIR / "behaviors" / "stable-execution.behavior.yaml"
        content = path.read_text()
        for field in ("states:", "transitions:", "forbidden_transitions:"):
            self.assertIn(field, content, f"Behavior spec missing section: {field}")

    def test_contract_has_handoff_schema(self):
        path = SPECS_DIR / "contracts" / "agent-handoff.contract.yaml"
        content = path.read_text()
        for field in ("handoff_schema:", "required_fields:", "validation_rules:"):
            self.assertIn(field, content, f"Contract spec missing section: {field}")

    def test_policy_has_retry_and_circuit_breaker(self):
        path = SPECS_DIR / "policies" / "stable-execution.policy.yaml"
        content = path.read_text()
        for section in (
            "retry_policy",
            "circuit_breaker_policy",
            "write_scope_policy",
            "routing_policy",
        ):
            self.assertIn(section, content, f"Policy spec missing section: {section}")

    def test_verification_has_acceptance_criteria(self):
        path = SPECS_DIR / "verification" / "stable-execution.verification.yaml"
        content = path.read_text()
        self.assertIn("acceptance_criteria:", content)
        self.assertIn("test_suites:", content)


# ---------------------------------------------------------------------------
# 4. Property tests (invariants)
# ---------------------------------------------------------------------------


class TestInvariants(unittest.TestCase):
    """Property-level invariants derived from specs."""

    def test_no_unbounded_retry_policy(self):
        """Policy must cap retries."""
        path = SPECS_DIR / "policies" / "stable-execution.policy.yaml"
        content = path.read_text()
        self.assertIn("max_attempts", content)
        # Verify value <= 3 (YAML format: - rule: "max_attempts" then value: 3)
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if "max_attempts" in line:
                # Look for value in next few lines
                for j in range(i + 1, min(i + 3, len(lines))):
                    if "value:" in lines[j]:
                        val = int(lines[j].split("value:")[1].strip())
                        self.assertLessEqual(val, 3, "max_attempts must be <= 3")
                        return
        self.fail("max_attempts value not found in policy")

    def test_forbidden_transitions_defined(self):
        """Behavior spec must define forbidden transitions."""
        path = SPECS_DIR / "behaviors" / "stable-execution.behavior.yaml"
        content = path.read_text()
        # YAML uses from:/to: on separate lines, check for the pattern
        # running -> running means from: "running" followed by to: "running"
        self.assertIn('from: "running"', content)
        self.assertIn('to: "running"', content)
        # Check for retrying -> retrying
        self.assertIn('from: "retrying"', content)
        self.assertIn('to: "retrying"', content)
        # Check for running -> synthesized (forbidden)
        self.assertIn('to: "synthesized"', content)
        # Verify forbidden_transitions section exists
        self.assertIn("forbidden_transitions:", content)

    def test_verifier_gate_in_behavior(self):
        """Behavior must prevent synthesized before verified."""
        path = SPECS_DIR / "behaviors" / "stable-execution.behavior.yaml"
        content = path.read_text()
        self.assertIn("Sintese sem validacao previa pelo verifier", content)

    def test_write_scope_disjoint_policy(self):
        """Policy must enforce disjoint write scopes."""
        path = SPECS_DIR / "policies" / "stable-execution.policy.yaml"
        content = path.read_text()
        self.assertIn("disjoint_scopes", content)
        self.assertIn("single_final_writer", content)

    def test_no_silent_fallback_policy(self):
        """Routing policy must forbid silent fallback."""
        path = SPECS_DIR / "policies" / "stable-execution.policy.yaml"
        content = path.read_text()
        self.assertIn("no_silent_fallback", content)
        self.assertIn("fallback_requires_evidence", content)


# ---------------------------------------------------------------------------
# 5. Handoff contract validation tests
# ---------------------------------------------------------------------------


class TestHandoffContract(unittest.TestCase):
    """Validate handoff contract schema completeness."""

    REQUIRED_HANDOFF_FIELDS = [
        "schema_version",
        "artifact_type",
        "producer_agent",
        "consumer_agent",
        "spec_id",
        "spec_version",
        "run_id",
        "timestamp",
        "evidence_refs",
        "risk_level",
        "compatibility_assessment",
        "trace_links",
    ]

    def test_all_required_fields_in_contract(self):
        path = SPECS_DIR / "contracts" / "agent-handoff.contract.yaml"
        content = path.read_text()
        for field in self.REQUIRED_HANDOFF_FIELDS:
            self.assertIn(
                f'"{field}"', content, f"Contract missing required field: {field}"
            )

    def test_validation_rules_present(self):
        path = SPECS_DIR / "contracts" / "agent-handoff.contract.yaml"
        content = path.read_text()
        rules = [
            "no_partial_payload",
            "no_missing_provenance",
            "evidence_refs_resolvable",
            "versioning_required",
            "write_scope_disjoint",
            "verifier_gate",
        ]
        for rule in rules:
            self.assertIn(rule, content, f"Contract missing validation rule: {rule}")


# ---------------------------------------------------------------------------
# 6. AGENTS.md consistency
# ---------------------------------------------------------------------------


class TestAgentsMdConsistency(unittest.TestCase):
    """Ensure AGENTS.md documents known issues and swarm rules."""

    def setUp(self):
        self.content = (REPO_ROOT / "AGENTS.md").read_text()

    def test_documents_routing_bug(self):
        self.assertIn("Routing Bug", self.content)
        self.assertIn("autocode", self.content)

    def test_documents_workaround(self):
        self.assertIn("--agent autocoder", self.content)

    def test_verifier_gate_rule(self):
        self.assertIn("verifier", self.content.lower())
        self.assertIn("synthesizer", self.content.lower())

    def test_write_scope_disjoint_rule(self):
        self.assertIn("write_scope", self.content)


# ---------------------------------------------------------------------------
# 7. Negative tests — forbidden patterns
# ---------------------------------------------------------------------------


class TestNegativePatterns(unittest.TestCase):
    """Ensure forbidden patterns do NOT appear in config."""

    def test_no_doom_loop_allow(self):
        config = _load_json(OPENCODE_DOT_CONFIG)
        # Global
        self.assertNotEqual(config["permission"].get("doom_loop"), "allow")
        # Per-agent
        for name, cfg in config["agent"].items():
            self.assertNotEqual(cfg["permission"].get("doom_loop"), "allow")

    def test_no_infinite_retry_in_policy(self):
        path = SPECS_DIR / "policies" / "stable-execution.policy.yaml"
        content = path.read_text()
        # Must have explicit max, not unbounded
        self.assertIn("max_attempts", content)
        self.assertNotIn("unlimited", content.lower())

    def test_no_silent_fallback_in_config(self):
        config = _load_json(OPENCODE_DOT_CONFIG)
        # No 'fallback_agent' key should exist
        self.assertNotIn("fallback_agent", config)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
