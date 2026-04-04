"""Mode contract schema validation and drift detection tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MODES_DIR = REPO_ROOT / ".internal" / "specs" / "modes"
SCHEMA_FILE = REPO_ROOT / ".internal" / "specs" / "core" / "agent-mode-contract.yaml"
ROOT_CONFIG = REPO_ROOT / "opencode.json"
DOT_OPENCODE_CONFIG = REPO_ROOT / ".opencode" / "opencode.json"

REQUIRED_MODES = ("explore", "reviewer", "orchestrator", "autocoder")

REQUIRED_SECTIONS = (
    "metadata",
    "mission",
    "scope",
    "resources",
    "memory",
    "satisficing",
    "handoff",
    "error_policy",
)

VALID_SATISFICING_MODES = {"URGENT", "ECONOMICAL", "BALANCED", "DEEP"}
VALID_RETENTION = {"ephemeral", "session", "persistent"}
VALID_COMPRESSION = {"none", "summary", "summary+refs", "delta"}
VALID_BUDGET_EXCEEDED = {"fail_fast", "degrade_gracefully", "notify_and_continue"}


def _load_mode_contract(name: str) -> dict:
    """Load a mode contract YAML file."""
    path = MODES_DIR / f"{name}.yaml"
    assert path.exists(), f"Mode contract missing: {path}"
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise AssertionError(f"Invalid YAML in {path}: {exc}") from exc


def _load_configs() -> tuple[dict, dict]:
    """Load both opencode config files."""
    root_cfg = json.loads(ROOT_CONFIG.read_text(encoding="utf-8"))
    dot_cfg = json.loads(DOT_OPENCODE_CONFIG.read_text(encoding="utf-8"))
    return root_cfg, dot_cfg


class TestModeContractExistence:
    """Verify all required mode contracts exist."""

    @pytest.mark.parametrize("mode_name", REQUIRED_MODES)
    def test_mode_contract_exists(self, mode_name: str):
        path = MODES_DIR / f"{mode_name}.yaml"
        assert path.exists(), f"Required mode contract missing: {path}"

    def test_schema_file_exists(self):
        assert SCHEMA_FILE.exists(), f"Schema file missing: {SCHEMA_FILE}"


class TestModeContractSchema:
    """Validate mode contracts against the schema specification."""

    @pytest.mark.parametrize("mode_name", REQUIRED_MODES)
    def test_required_sections_present(self, mode_name: str):
        contract = _load_mode_contract(mode_name)
        assert "agent_mode_contract" in contract, f"Missing root key in {mode_name}"
        root = contract["agent_mode_contract"]
        for section in REQUIRED_SECTIONS:
            assert section in root, (
                f"Missing required section '{section}' in {mode_name}"
            )

    @pytest.mark.parametrize("mode_name", REQUIRED_MODES)
    def test_metadata_fields(self, mode_name: str):
        contract = _load_mode_contract(mode_name)
        meta = contract["agent_mode_contract"]["metadata"]
        assert meta["name"] == mode_name
        assert "version" in meta
        assert "parent_contract" in meta
        assert meta["parent_contract"] == "orchestration-contract.yaml"

    @pytest.mark.parametrize("mode_name", REQUIRED_MODES)
    def test_mission_structure(self, mode_name: str):
        contract = _load_mode_contract(mode_name)
        mission = contract["agent_mode_contract"]["mission"]
        assert "description" in mission
        assert "success_criteria" in mission
        assert "failure_conditions" in mission
        assert isinstance(mission["success_criteria"], list)
        assert len(mission["success_criteria"]) > 0

    @pytest.mark.parametrize("mode_name", REQUIRED_MODES)
    def test_scope_structure(self, mode_name: str):
        contract = _load_mode_contract(mode_name)
        scope = contract["agent_mode_contract"]["scope"]
        assert "input_schema" in scope
        assert "output_schema" in scope
        assert "tools_allowlist" in scope
        assert "tools_denylist" in scope

    @pytest.mark.parametrize("mode_name", REQUIRED_MODES)
    def test_tools_disjoint(self, mode_name: str):
        contract = _load_mode_contract(mode_name)
        scope = contract["agent_mode_contract"]["scope"]
        allowlist = set(scope.get("tools_allowlist", []))
        denylist = set(scope.get("tools_denylist", []))
        overlap = allowlist & denylist
        assert not overlap, (
            f"MC-004 violation in {mode_name}: tools in both allowlist and denylist: {overlap}"
        )

    @pytest.mark.parametrize("mode_name", REQUIRED_MODES)
    def test_resources_positive(self, mode_name: str):
        contract = _load_mode_contract(mode_name)
        resources = contract["agent_mode_contract"]["resources"]
        for key, value in resources.items():
            assert isinstance(value, int) and value > 0, (
                f"MC-003 violation in {mode_name}: {key} must be positive integer, got {value}"
            )

    @pytest.mark.parametrize("mode_name", REQUIRED_MODES)
    def test_satisficing_mode_valid(self, mode_name: str):
        contract = _load_mode_contract(mode_name)
        mode = contract["agent_mode_contract"]["satisficing"]["mode"]
        assert mode in VALID_SATISFICING_MODES, (
            f"MC-006 violation in {mode_name}: invalid satisficing mode '{mode}'"
        )

    @pytest.mark.parametrize("mode_name", REQUIRED_MODES)
    def test_quality_threshold_range(self, mode_name: str):
        contract = _load_mode_contract(mode_name)
        threshold = contract["agent_mode_contract"]["satisficing"]["quality_threshold"]
        assert 0.0 <= threshold <= 1.0, (
            f"MC-010 violation in {mode_name}: quality_threshold {threshold} out of [0.0, 1.0]"
        )

    @pytest.mark.parametrize("mode_name", REQUIRED_MODES)
    def test_memory_retention_valid(self, mode_name: str):
        contract = _load_mode_contract(mode_name)
        memory = contract["agent_mode_contract"]["memory"]
        for section in ("operational_context", "session_state", "structural_memory"):
            retention = memory[section]["retention"]
            assert retention in VALID_RETENTION, (
                f"MC-007 violation in {mode_name}: invalid retention '{retention}' in {section}"
            )

    @pytest.mark.parametrize("mode_name", REQUIRED_MODES)
    def test_handoff_compression_valid(self, mode_name: str):
        contract = _load_mode_contract(mode_name)
        compression = contract["agent_mode_contract"]["handoff"]["compression"]
        assert compression in VALID_COMPRESSION, (
            f"Invalid compression mode '{compression}' in {mode_name}"
        )

    @pytest.mark.parametrize("mode_name", REQUIRED_MODES)
    def test_budget_exceeded_policy_valid(self, mode_name: str):
        contract = _load_mode_contract(mode_name)
        policy = contract["agent_mode_contract"]["error_policy"]["on_budget_exceeded"]
        assert policy in VALID_BUDGET_EXCEEDED, (
            f"Invalid on_budget_exceeded policy '{policy}' in {mode_name}"
        )

    @pytest.mark.parametrize("mode_name", REQUIRED_MODES)
    def test_retry_max_bounded(self, mode_name: str):
        contract = _load_mode_contract(mode_name)
        retry = contract["agent_mode_contract"]["error_policy"]["retry_max"]
        assert 0 <= retry <= 3, (
            f"MC-009 violation in {mode_name}: retry_max={retry} must be in [0, 3]"
        )

    @pytest.mark.parametrize("mode_name", REQUIRED_MODES)
    def test_handoff_payload_within_context(self, mode_name: str):
        contract = _load_mode_contract(mode_name)
        resources = contract["agent_mode_contract"]["resources"]
        memory = contract["agent_mode_contract"]["memory"]
        handoff_budget = memory["handoff_payload_budget"]["max_tokens"]
        context_tokens = resources["max_context_tokens"]
        assert handoff_budget <= context_tokens, (
            f"MC-008 violation in {mode_name}: handoff_payload_budget ({handoff_budget}) "
            f"exceeds max_context_tokens ({context_tokens})"
        )


class TestModeContractDrift:
    """Detect drift between config bindings and mode contracts."""

    def test_config_references_existing_contracts(self):
        root_cfg, dot_cfg = _load_configs()
        for cfg_name, cfg in [("root", root_cfg), (".opencode", dot_cfg)]:
            for agent_name, agent_def in cfg.get("agent", {}).items():
                if "mode_contract" not in agent_def:
                    continue
                contract_path = REPO_ROOT / agent_def["mode_contract"]
                assert contract_path.exists(), (
                    f"Config {cfg_name}: agent '{agent_name}' references non-existent "
                    f"mode contract: {agent_def['mode_contract']}"
                )

    def test_config_contract_paths_match(self):
        root_cfg, dot_cfg = _load_configs()
        for agent_name in REQUIRED_MODES:
            root_contract = (
                root_cfg.get("agent", {}).get(agent_name, {}).get("mode_contract")
            )
            dot_contract = (
                dot_cfg.get("agent", {}).get(agent_name, {}).get("mode_contract")
            )
            if root_contract and dot_contract:
                assert root_contract == dot_contract, (
                    f"Drift: agent '{agent_name}' mode_contract path differs: "
                    f"root={root_contract}, .opencode={dot_contract}"
                )

    def test_mission_not_drifted(self):
        """Verify mission descriptions are stable (no accidental changes)."""
        for mode_name in REQUIRED_MODES:
            contract = _load_mode_contract(mode_name)
            mission = contract["agent_mode_contract"]["mission"]["description"]
            assert len(mission) > 10, (
                f"Mission description too short in {mode_name}: possible drift or placeholder"
            )

    def test_budget_not_zero(self):
        """Verify no budget field is accidentally set to zero."""
        for mode_name in REQUIRED_MODES:
            contract = _load_mode_contract(mode_name)
            resources = contract["agent_mode_contract"]["resources"]
            for key, value in resources.items():
                assert value > 0, (
                    f"Budget drift in {mode_name}: {key} is zero or negative"
                )


class TestModeContractHandoffs:
    """Validate handoff target references."""

    def test_handoff_targets_exist(self):
        for mode_name in REQUIRED_MODES:
            contract = _load_mode_contract(mode_name)
            targets = contract["agent_mode_contract"]["handoff"]["allowed_targets"]
            for target in targets:
                assert target in REQUIRED_MODES, (
                    f"Handoff target '{target}' in {mode_name} is not a known mode contract"
                )

    def test_no_self_handoff(self):
        for mode_name in REQUIRED_MODES:
            contract = _load_mode_contract(mode_name)
            targets = contract["agent_mode_contract"]["handoff"]["allowed_targets"]
            assert mode_name not in targets, (
                f"Mode '{mode_name}' lists itself as a handoff target"
            )

    def test_verifier_gate_consistency(self):
        """All modes must require verifier before handoff."""
        for mode_name in REQUIRED_MODES:
            contract = _load_mode_contract(mode_name)
            assert (
                contract["agent_mode_contract"]["handoff"]["verifier_required"] is True
            ), f"Mode '{mode_name}' does not require verifier gate before handoff"


class TestModeContractConstitutionalCompliance:
    """Verify mode contracts comply with constitutional invariants."""

    def test_no_secrets_in_allowlist(self):
        """No mode should allow tools that could expose secrets."""
        for mode_name in REQUIRED_MODES:
            contract = _load_mode_contract(mode_name)
            denylist = contract["agent_mode_contract"]["scope"]["tools_denylist"]
            input_forbidden = contract["agent_mode_contract"]["scope"][
                "input_schema"
            ].get("forbidden_fields", [])
            assert "secrets" in input_forbidden or "credentials" in input_forbidden, (
                f"Mode '{mode_name}' does not forbid secrets/credentials in input"
            )

    def test_evidence_trail_preserved(self):
        """All modes must support evidence trail in output."""
        for mode_name in REQUIRED_MODES:
            contract = _load_mode_contract(mode_name)
            output = contract["agent_mode_contract"]["scope"]["output_schema"]
            required = [f["name"] for f in output.get("required_fields", [])]
            has_evidence = any(
                "evidence" in f.lower() or "finding" in f.lower() for f in required
            )
            assert has_evidence, (
                f"Mode '{mode_name}' output schema lacks evidence/findings field"
            )


EXPECTED_SKILLS = {
    "explore": [
        "impact_analysis",
        "repo_topology_map",
        "dependency_surface",
        "change_impact_deep",
    ],
    "reviewer": [
        "conformance_audit",
        "policy_gate",
        "contract_drift_audit",
        "policy_gate_plus",
        "boundary_leak_detector",
    ],
    "orchestrator": [
        "explicit_planner",
        "budget_allocator",
        "handoff_compressor",
        "memory_curator_v2",
        "spec_architecture",
        "spec_compilation",
    ],
}

VALID_SKILL_SOURCES = {"opencode-builtin", "internal", "domain-pack"}


class TestModeContractSkills:
    """Validate skills integration in mode contracts."""

    @pytest.mark.parametrize("mode_name,expected_skills", EXPECTED_SKILLS.items())
    def test_expected_skills_present(self, mode_name: str, expected_skills: list[str]):
        contract = _load_mode_contract(mode_name)
        skills = contract["agent_mode_contract"].get("skills", [])
        skill_names = [s["name"] for s in skills]
        for expected in expected_skills:
            assert expected in skill_names, (
                f"Mode '{mode_name}' missing expected skill: {expected}"
            )

    def test_autocoder_has_no_skills(self):
        """autocoder is execution-pure; no built-in skills should be added."""
        contract = _load_mode_contract("autocoder")
        skills = contract["agent_mode_contract"].get("skills", [])
        assert len(skills) == 0, (
            f"autocoder should not have skills (execution-pure mode), found: {[s['name'] for s in skills]}"
        )

    @pytest.mark.parametrize("mode_name", REQUIRED_MODES)
    def test_skill_fields_valid(self, mode_name: str):
        contract = _load_mode_contract(mode_name)
        skills = contract["agent_mode_contract"].get("skills", [])
        required_fields = (
            "name",
            "description",
            "source",
            "trigger",
            "input_contract",
            "output_contract",
            "budget_share",
            "verifier_required",
        )
        for skill in skills:
            for field in required_fields:
                assert field in skill, (
                    f"Mode '{mode_name}' skill '{skill.get('name', '?')}' missing field: {field}"
                )

    @pytest.mark.parametrize("mode_name", REQUIRED_MODES)
    def test_skill_budget_share_valid(self, mode_name: str):
        contract = _load_mode_contract(mode_name)
        skills = contract["agent_mode_contract"].get("skills", [])
        for skill in skills:
            share = skill["budget_share"]
            assert 0.0 < share <= 1.0, (
                f"MC-011 violation in {mode_name}: skill '{skill['name']}' "
                f"budget_share={share} out of (0.0, 1.0]"
            )

    @pytest.mark.parametrize("mode_name", REQUIRED_MODES)
    def test_skill_budget_sum_within_limit(self, mode_name: str):
        """MC-013: Sum of skill budget_share must not exceed 1.0."""
        contract = _load_mode_contract(mode_name)
        skills = contract["agent_mode_contract"].get("skills", [])
        total_share = sum(s["budget_share"] for s in skills)
        assert total_share <= 1.0, (
            f"MC-013 violation in {mode_name}: sum of skill budget_share "
            f"({total_share:.2f}) exceeds 1.0"
        )

    @pytest.mark.parametrize("mode_name", REQUIRED_MODES)
    def test_skill_source_valid(self, mode_name: str):
        """MC-012: Skills source must reference known origin."""
        contract = _load_mode_contract(mode_name)
        skills = contract["agent_mode_contract"].get("skills", [])
        for skill in skills:
            source = skill["source"]
            has_valid_prefix = any(
                source.startswith(prefix) for prefix in VALID_SKILL_SOURCES
            )
            assert has_valid_prefix, (
                f"MC-012 violation in {mode_name}: skill '{skill['name']}' "
                f"has invalid source '{source}'. Must start with one of: {VALID_SKILL_SOURCES}"
            )

    def test_skill_verifier_consistency(self):
        """Skills that produce compliance/security output should require verifier."""
        contract = _load_mode_contract("reviewer")
        skills = contract["agent_mode_contract"].get("skills", [])
        for skill in skills:
            if skill["name"] in ("conformance_audit", "policy_gate"):
                assert skill["verifier_required"] is True, (
                    f"Reviewer skill '{skill['name']}' must require verifier gate"
                )

    def test_skill_no_duplicate_names(self):
        """No mode should have duplicate skill names."""
        for mode_name in REQUIRED_MODES:
            contract = _load_mode_contract(mode_name)
            skills = contract["agent_mode_contract"].get("skills", [])
            names = [s["name"] for s in skills]
            assert len(names) == len(set(names)), (
                f"Mode '{mode_name}' has duplicate skill names: {names}"
            )
