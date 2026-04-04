"""Tests for the approval gate runtime."""

from __future__ import annotations

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from approval_gate import ApprovalGate, ChangeClassification, ApprovalDecision


@pytest.fixture
def gate():
    return ApprovalGate(run_id="test-gate-001")


class TestApprovalGateBasic:
    def test_clean_change_low_risk(self, gate):
        classification = gate.classify_change("src/utils.py", "addition", 50)
        assert classification.risk_level == "low"
        assert not classification.requires_approval

    def test_contract_change_critical(self, gate):
        classification = gate.classify_change(
            ".internal/specs/modes/explore.yaml", "modification", 10
        )
        assert classification.risk_level == "critical"
        assert classification.requires_approval
        assert classification.approvers_required == 2

    def test_public_api_change_high(self, gate):
        classification = gate.classify_change("docs/README.md", "modification", 5)
        assert classification.risk_level == "high"
        assert classification.requires_approval

    def test_config_change_high(self, gate):
        classification = gate.classify_change(
            ".pre-commit-config.yaml", "modification", 3
        )
        assert classification.risk_level == "high"
        assert classification.requires_approval

    def test_test_deletion_high(self, gate):
        classification = gate.classify_change("tests/test_main.py", "deletion", 20)
        assert classification.risk_level == "high"
        assert classification.requires_approval

    def test_runtime_change_high(self, gate):
        classification = gate.classify_change(
            ".internal/runtime/contract_verifier.py", "modification", 30
        )
        assert classification.risk_level == "high"
        assert classification.requires_approval

    def test_large_change_medium(self, gate):
        classification = gate.classify_change("src/main.py", "modification", 300)
        assert classification.risk_level == "medium"
        assert classification.requires_approval
        assert classification.approvers_required == 1

    def test_security_finding_critical(self, gate):
        classification = gate.classify_change(
            "src/main.py", "modification", 10, has_security_finding=True
        )
        assert classification.risk_level == "critical"
        assert classification.requires_approval


class TestApprovalGateEvaluate:
    def test_all_low_approved(self, gate):
        changes = [
            {
                "file_path": "src/utils.py",
                "change_type": "addition",
                "lines_changed": 50,
            },
        ]
        decision = gate.evaluate(changes)
        assert decision.approved
        assert decision.overall_risk == "low"

    def test_critical_blocked(self, gate):
        changes = [
            {
                "file_path": ".internal/specs/modes/explore.yaml",
                "change_type": "modification",
                "lines_changed": 10,
            },
        ]
        decision = gate.evaluate(changes)
        assert not decision.approved
        assert decision.overall_risk == "critical"

    def test_policy_failure_blocks(self, gate):
        changes = [
            {
                "file_path": "src/utils.py",
                "change_type": "addition",
                "lines_changed": 10,
            },
        ]
        decision = gate.evaluate(changes, policy_passed=False)
        assert not decision.approved
        assert "Policy check failed" in decision.blocked_reasons[0]

    def test_contract_failure_blocks(self, gate):
        changes = [
            {
                "file_path": "src/utils.py",
                "change_type": "addition",
                "lines_changed": 10,
            },
        ]
        decision = gate.evaluate(changes, contract_verified=False)
        assert not decision.approved
        assert "Contract verification failed" in decision.blocked_reasons[0]

    def test_approval_requirements_populated(self, gate):
        changes = [
            {
                "file_path": ".internal/specs/modes/explore.yaml",
                "change_type": "modification",
                "lines_changed": 10,
            },
        ]
        decision = gate.evaluate(changes)
        assert len(decision.approval_requirements) > 0
        assert any("contract_change" in r for r in decision.approval_requirements)

    def test_to_dict_structure(self, gate):
        changes = [
            {
                "file_path": "src/utils.py",
                "change_type": "addition",
                "lines_changed": 10,
            }
        ]
        decision = gate.evaluate(changes)
        d = decision.to_dict()
        assert "run_id" in d
        assert "approved" in d
        assert "overall_risk" in d
        assert "changes" in d
        assert "integrity_hash" in d


class TestApprovalGateDiffParsing:
    def test_parse_addition(self, gate):
        diff = """diff --git a/src/new.py b/src/new.py
new file mode 100644
--- /dev/null
+++ b/src/new.py
@@ -0,0 +1,5 @@
+line1
+line2
"""
        changes = gate._parse_diff(diff)
        assert len(changes) == 1
        assert changes[0]["file_path"] == "src/new.py"
        assert changes[0]["change_type"] == "addition"

    def test_parse_deletion(self, gate):
        diff = """diff --git a/src/old.py b/src/old.py
deleted file mode 100644
--- a/src/old.py
+++ /dev/null
@@ -1,3 +0,0 @@
-line1
-line2
"""
        changes = gate._parse_diff(diff)
        assert len(changes) == 1
        assert changes[0]["change_type"] == "deletion"

    def test_evaluate_from_git_diff(self, gate):
        diff = """diff --git a/src/utils.py b/src/utils.py
--- a/src/utils.py
+++ b/src/utils.py
@@ -1,3 +1,5 @@
 line1
+line2
+line3
"""
        decision = gate.evaluate_from_git_diff(diff)
        assert isinstance(decision, ApprovalDecision)


class TestChangeClassification:
    def test_change_id_generated(self, gate):
        classification = gate.classify_change("src/main.py", "addition", 10)
        assert classification.change_id.startswith("chg-")
        assert len(classification.change_id) == 16

    def test_risk_factors_populated(self, gate):
        classification = gate.classify_change(
            ".internal/specs/modes/explore.yaml", "modification", 10
        )
        assert "contract_change" in classification.risk_factors

    def test_affected_contracts_populated(self, gate):
        classification = gate.classify_change(
            ".internal/specs/modes/explore.yaml", "modification", 10
        )
        assert len(classification.affected_contracts) > 0


class TestEvaluateChangesFunction:
    def test_returns_dict(self):
        from approval_gate import evaluate_changes

        result = evaluate_changes(
            [
                {
                    "file_path": "src/utils.py",
                    "change_type": "addition",
                    "lines_changed": 10,
                }
            ],
            run_id="test-001",
        )
        assert isinstance(result, dict)
        assert result["approved"]
