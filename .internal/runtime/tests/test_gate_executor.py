"""Tests for Gate Executor runtime."""

from __future__ import annotations

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gate_executor import GateExecutor, GateResult, GateReport


@pytest.fixture
def executor():
    return GateExecutor()


class TestGateExecutorBasics:
    def test_returns_gate_report(self, executor):
        report = executor.execute_all({}, is_2x=False)
        assert isinstance(report, GateReport)

    def test_universal_gates_executed_1x(self, executor):
        report = executor.execute_all({}, is_2x=False)
        assert len(report.universal_gates) > 0
        assert len(report.specialized_gates) == 0

    def test_specialized_gates_executed_2x(self, executor):
        output = {
            "algorithm_selection_rationale": "Segment tree for range queries",
            "complexity_certificate": {"time": "O(log n)", "space": "O(n)"},
            "stress_test_plan": "Generate random arrays and compare with brute force",
            "memory_bound_estimate": "O(n) for segment tree, ~4MB for n=100000",
            "edge_case_analysis": {"empty": True, "overflow": True},
        }
        report = executor.execute_all(output, is_2x=True)
        assert len(report.specialized_gates) > 0


class TestUniversalGates:
    def test_typing_gate_no_source(self, executor):
        report = executor.execute_universal_gates({})
        typing_gate = next(g for g in report if g.gate_id == "typing")
        assert typing_gate.status == "warn"

    def test_security_clean_code(self, executor):
        source = "def hello(name: str) -> str:\n    return f'Hello {name}'"
        report = executor.execute_universal_gates({}, source)
        sec_gate = next(g for g in report if g.gate_id == "security")
        assert sec_gate.status == "pass"

    def test_security_hardcoded_secret(self, executor):
        source = "password = 'secret123'\ndef login(): pass"
        report = executor.execute_universal_gates({}, source)
        sec_gate = next(g for g in report if g.gate_id == "security")
        assert sec_gate.status == "fail"

    def test_security_eval_detected(self, executor):
        source = "result = eval(user_input)"
        report = executor.execute_universal_gates({}, source)
        sec_gate = next(g for g in report if g.gate_id == "security")
        assert sec_gate.status == "fail"

    def test_complexity_acceptable(self, executor):
        source = "def simple():\n    x = 1\n    return x"
        report = executor.execute_universal_gates({}, source)
        cx_gate = next(g for g in report if g.gate_id == "complexity")
        assert cx_gate.status == "pass"

    def test_complexity_deep_nesting(self, executor):
        source = "\n".join(f"{'    ' * i}if True:" for i in range(1, 7))
        report = executor.execute_universal_gates({}, source)
        cx_gate = next(g for g in report if g.gate_id == "complexity")
        assert cx_gate.status == "fail"

    def test_error_handling_bare_except(self, executor):
        source = "try:\n    pass\nexcept:\n    pass"
        report = executor.execute_universal_gates({}, source)
        err_gate = next(g for g in report if g.gate_id == "error_handling")
        assert err_gate.status == "fail"

    def test_testing_gate_no_tests(self, executor):
        report = executor.execute_universal_gates({})
        test_gate = next(g for g in report if g.gate_id == "testing")
        assert test_gate.status == "warn"

    def test_testing_gate_with_tests(self, executor):
        report = executor.execute_universal_gates({"tests": ["pytest tests/"]})
        test_gate = next(g for g in report if g.gate_id == "testing")
        assert test_gate.status == "pass"


class TestSpecializedGates:
    def test_algorithmic_validation_pass(self, executor):
        output = {
            "algorithm_selection_rationale": "Segment tree for RMQ with updates",
            "complexity_certificate": {"time": "O(log n)", "space": "O(n)"},
        }
        report = executor.execute_specialized_gates(output, "")
        algo_gate = next(g for g in report if g.gate_id == "algorithmic_validation")
        assert algo_gate.status == "pass"

    def test_algorithmic_validation_fail_no_rationale(self, executor):
        output = {}
        report = executor.execute_specialized_gates(output, "")
        algo_gate = next(g for g in report if g.gate_id == "algorithmic_validation")
        assert algo_gate.status == "fail"

    def test_constraint_satisfaction_pass(self, executor):
        output = {
            "constraints_found": {"n": 200000},
            "complexity_certificate": {"time": "O(n log n)", "space": "O(n)"},
            "edge_case_analysis": {"overflow": True},
        }
        report = executor.execute_specialized_gates(output, "")
        constraint_gate = next(
            g for g in report if g.gate_id == "constraint_satisfaction"
        )
        assert constraint_gate.status == "pass"

    def test_constraint_satisfaction_fail_naive(self, executor):
        output = {
            "constraints_found": {"n": 200000},
            "complexity_certificate": {"time": "O(n²)", "space": "O(1)"},
            "edge_case_analysis": {"overflow": True},
        }
        report = executor.execute_specialized_gates(output, "")
        constraint_gate = next(
            g for g in report if g.gate_id == "constraint_satisfaction"
        )
        assert constraint_gate.status == "fail"

    def test_stress_test_pass(self, executor):
        output = {
            "stress_test_plan": "Generate random inputs and compare with brute force reference solution",
        }
        report = executor.execute_specialized_gates(output, "")
        stress_gate = next(g for g in report if g.gate_id == "stress_test")
        assert stress_gate.status == "pass"

    def test_stress_test_fail(self, executor):
        output = {"stress_test_plan": ""}
        report = executor.execute_specialized_gates(output, "")
        stress_gate = next(g for g in report if g.gate_id == "stress_test")
        assert stress_gate.status == "fail"

    def test_memory_layout_pass(self, executor):
        output = {
            "memory_bound_estimate": "Peak memory: O(n) = 4MB for n=100000. Cache-friendly sequential access.",
        }
        report = executor.execute_specialized_gates(output, "")
        mem_gate = next(g for g in report if g.gate_id == "memory_layout")
        assert mem_gate.status == "pass"

    def test_memory_layout_fail(self, executor):
        output = {"memory_bound_estimate": ""}
        report = executor.execute_specialized_gates(output, "")
        mem_gate = next(g for g in report if g.gate_id == "memory_layout")
        assert mem_gate.status == "fail"


class TestGateReport:
    def test_overall_pass(self, executor):
        output = {
            "tests": ["pytest"],
            "algorithm_selection_rationale": "Good rationale with enough text here",
            "complexity_certificate": {"time": "O(n)", "space": "O(n)"},
            "stress_test_plan": "Good stress test plan with enough text here",
            "memory_bound_estimate": "Good memory estimate with enough text here",
            "edge_case_analysis": {"overflow": True},
        }
        source = "def hello(name: str) -> str:\n    return name"
        report = executor.execute_all(output, is_2x=True, source_code=source)
        assert report.overall_status in ("pass", "warn")
        assert report.auto_reject is False

    def test_overall_fail_security(self, executor):
        source = "password = 'secret'\ndef login(): pass"
        report = executor.execute_all({}, is_2x=False, source_code=source)
        assert report.overall_status == "fail"
        assert report.auto_reject is True

    def test_auto_reject_missing_2x_fields(self, executor):
        report = executor.execute_all({}, is_2x=True)
        assert report.auto_reject is True
        assert any("Missing required 2x fields" in r for r in report.rejection_reasons)

    def test_passed_property(self, executor):
        report = GateReport(
            universal_gates=[GateResult("test", "Test", "pass")],
            overall_status="pass",
        )
        assert report.passed is True

    def test_not_passed_on_fail(self, executor):
        report = GateReport(
            universal_gates=[GateResult("test", "Test", "fail")],
            overall_status="fail",
            auto_reject=True,
        )
        assert report.passed is False


class TestEdgeCases:
    def test_empty_output_1x(self, executor):
        report = executor.execute_all({}, is_2x=False)
        assert len(report.universal_gates) > 0

    def test_empty_output_2x(self, executor):
        report = executor.execute_all({}, is_2x=True)
        assert len(report.universal_gates) > 0
        assert len(report.specialized_gates) > 0
        assert report.auto_reject is True
