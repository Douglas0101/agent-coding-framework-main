"""Tests for the contract verifier runtime."""

from __future__ import annotations

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from contract_verifier import ContractVerifier, Violation, verify_all_modes


@pytest.fixture
def verifier():
    return ContractVerifier(run_id="test-run-001")


class TestContractVerifierBasic:
    def test_verify_all_modes_pass(self, verifier):
        results = verifier.verify_all_modes()
        for mode, report in results.items():
            assert report.passed, (
                f"Mode {mode} failed: {[v.message for v in report.violations]}"
            )

    def test_verify_single_mode(self, verifier):
        report = verifier.verify_mode("explore")
        assert report.passed
        assert report.mode == "explore"
        assert report.checks_passed == 12
        assert report.checks_failed == 0

    def test_verify_nonexistent_mode(self, verifier):
        report = verifier.verify_mode("nonexistent")
        assert not report.passed
        assert len(report.violations) == 1
        assert report.violations[0].rule_id == "CV-000"

    def test_integrity_hash_present(self, verifier):
        report = verifier.verify_mode("explore")
        assert report.integrity_hash.startswith("sha256:")


class TestContractVerifierViolations:
    def test_missing_section(self, verifier):
        contract = {"agent_mode_contract": {"metadata": {"name": "test"}}}
        violations = verifier._check_required_sections(contract)
        assert any(v.rule_id == "CV-001" for v in violations)

    def test_missing_metadata_field(self, verifier):
        contract = {"agent_mode_contract": {"metadata": {}}}
        violations = verifier._check_metadata(contract)
        assert any("Missing metadata field" in v.message for v in violations)

    def test_invalid_satisficing_mode(self, verifier):
        contract = {"agent_mode_contract": {"satisficing": {"mode": "INVALID"}}}
        violations = verifier._check_satisficing(contract)
        assert any("Invalid satisficing mode" in v.message for v in violations)

    def test_quality_threshold_out_of_range(self, verifier):
        contract = {"agent_mode_contract": {"satisficing": {"quality_threshold": 1.5}}}
        violations = verifier._check_satisficing(contract)
        assert any("out of range" in v.message for v in violations)

    def test_negative_resource(self, verifier):
        contract = {"agent_mode_contract": {"resources": {"max_input_tokens": -100}}}
        violations = verifier._check_resources(contract)
        assert any("must be positive" in v.message for v in violations)

    def test_invalid_retention(self, verifier):
        contract = {
            "agent_mode_contract": {
                "memory": {"operational_context": {"retention": "forever"}}
            }
        }
        violations = verifier._check_memory(contract)
        assert any("Invalid retention" in v.message for v in violations)

    def test_retry_max_exceeds_3(self, verifier):
        contract = {"agent_mode_contract": {"error_policy": {"retry_max": 5}}}
        violations = verifier._check_error_policy(contract)
        assert any("retry_max must be 0-3" in v.message for v in violations)

    def test_tools_overlap(self, verifier):
        contract = {
            "agent_mode_contract": {
                "scope": {
                    "tools_allowlist": ["read", "edit"],
                    "tools_denylist": ["edit", "write"],
                }
            }
        }
        violations = verifier._check_tools_disjoint(contract)
        assert any("both allowlist and denylist" in v.message for v in violations)

    def test_handoff_budget_exceeds_context(self, verifier):
        contract = {
            "agent_mode_contract": {
                "memory": {"handoff_payload_budget": {"max_tokens": 5000}},
                "resources": {"max_context_tokens": 3000},
            }
        }
        violations = verifier._check_budget_conservation(contract)
        assert any("max_tokens" in v.message for v in violations)

    def test_duplicate_skill_names(self, verifier):
        contract = {
            "agent_mode_contract": {
                "skills": [
                    {
                        "name": "test",
                        "description": "a",
                        "source": "internal:test",
                        "trigger": "manual",
                        "budget_share": 0.3,
                    },
                    {
                        "name": "test",
                        "description": "b",
                        "source": "internal:test",
                        "trigger": "manual",
                        "budget_share": 0.3,
                    },
                ]
            }
        }
        violations = verifier._check_skills(contract)
        assert any("Duplicate skill name" in v.message for v in violations)

    def test_skill_budget_exceeds_1(self, verifier):
        contract = {
            "agent_mode_contract": {
                "skills": [
                    {
                        "name": "s1",
                        "description": "a",
                        "source": "internal:test",
                        "trigger": "manual",
                        "budget_share": 0.6,
                    },
                    {
                        "name": "s2",
                        "description": "b",
                        "source": "internal:test",
                        "trigger": "manual",
                        "budget_share": 0.6,
                    },
                ]
            }
        }
        violations = verifier._check_skills(contract)
        assert any("exceeds 1.0" in v.message for v in violations)

    def test_skill_budget_negative(self, verifier):
        contract = {
            "agent_mode_contract": {
                "skills": [
                    {
                        "name": "bad",
                        "description": "a",
                        "source": "internal:test",
                        "trigger": "manual",
                        "budget_share": -0.1,
                    },
                ]
            }
        }
        violations = verifier._check_skills(contract)
        assert any("budget_share out of range" in v.message for v in violations)


class TestVerifyAllModesFunction:
    def test_returns_dict(self):
        results = verify_all_modes(run_id="test-001")
        assert isinstance(results, dict)
        assert "explore" in results
        assert "reviewer" in results
        assert "orchestrator" in results
        assert "autocoder" in results

    def test_all_passed(self):
        results = verify_all_modes(run_id="test-001")
        for mode, report in results.items():
            assert report["passed"], f"{mode} failed"
