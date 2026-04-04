"""Gate Executor — Runtime implementation.

Executes universal and specialized validation gates for the Hybrid Core
1x/2x system. Universal gates run on every task; specialized gates run
only when performance_2x profile is active.

Specs:
  - .internal/specs/core/universal-quality-contract.yaml
  - .internal/domains/ioi-gold-compiler/frontier-validation-gates.yaml
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

try:
    from .tool_runner import ToolRunner, ToolResult
    from .over_engineering_detector import OverEngineeringDetector
    from .under_engineering_detector import UnderEngineeringDetector
except ImportError:  # pragma: no cover - standalone script/test compatibility
    from tool_runner import ToolRunner, ToolResult
    from over_engineering_detector import OverEngineeringDetector
    from under_engineering_detector import UnderEngineeringDetector

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
UNIVERSAL_CONTRACT = (
    REPO_ROOT / ".internal" / "specs" / "core" / "universal-quality-contract.yaml"
)
FRONTIER_GATES = (
    REPO_ROOT
    / ".internal"
    / "domains"
    / "ioi-gold-compiler"
    / "frontier-validation-gates.yaml"
)


@dataclass
class GateCheck:
    """Result of a single gate check."""

    check_id: str
    status: str  # pass, fail, warn
    message: str = ""


@dataclass
class GateResult:
    """Result of a single gate (may contain multiple checks)."""

    gate_id: str
    gate_name: str
    status: str  # pass, fail, warn
    checks: list[GateCheck] = field(default_factory=list)
    evidence_ref: str | None = None


@dataclass
class GateReport:
    """Complete gate execution report."""

    universal_gates: list[GateResult] = field(default_factory=list)
    specialized_gates: list[GateResult] = field(default_factory=list)
    overall_status: str = "pass"
    auto_reject: bool = False
    rejection_reasons: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.auto_reject and self.overall_status != "fail"


class GateExecutor:
    """Executes universal and specialized validation gates."""

    def __init__(
        self,
        universal_contract_path: Path | None = None,
        frontier_gates_path: Path | None = None,
        tool_runner: ToolRunner | None = None,
    ):
        self._universal_path = universal_contract_path or UNIVERSAL_CONTRACT
        self._frontier_path = frontier_gates_path or FRONTIER_GATES
        self._universal_contract = self._load_yaml(self._universal_path)
        self._frontier_gates = self._load_yaml(self._frontier_path)
        self._tool_runner = tool_runner or ToolRunner()

    def _load_yaml(self, path: Path) -> dict | None:
        if not path.exists():
            return None
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def execute_all(
        self,
        code_output: dict[str, Any],
        is_2x: bool = False,
        source_code: str = "",
        file_path: str = "",
    ) -> GateReport:
        """Execute all applicable gates.

        Args:
            code_output: The agent's output dictionary.
            is_2x: Whether performance_2x profile is active.
            source_code: Generated source code for analysis.
            file_path: Path to the generated/modified file.

        Returns:
            GateReport with all gate results.
        """
        universal = self._execute_universal_gates(code_output, source_code)
        specialized: list[GateResult] = []
        if is_2x:
            specialized = self._execute_specialized_gates(code_output, source_code)

        all_gates = universal + specialized
        overall = self._compute_overall_status(all_gates)
        auto_reject, reasons = self._check_auto_reject(all_gates, code_output, is_2x)

        return GateReport(
            universal_gates=universal,
            specialized_gates=specialized,
            overall_status=overall,
            auto_reject=auto_reject,
            rejection_reasons=reasons,
        )

    def execute_universal_gates(
        self,
        code_output: dict[str, Any],
        source_code: str = "",
    ) -> list[GateResult]:
        """Execute only universal gates."""
        return self._execute_universal_gates(code_output, source_code)

    def execute_specialized_gates(
        self,
        code_output: dict[str, Any],
        source_code: str = "",
    ) -> list[GateResult]:
        """Execute only specialized (2x) gates."""
        return self._execute_specialized_gates(code_output, source_code)

    # ── Universal Gates ──────────────────────────────────────────

    def _execute_universal_gates(
        self, code_output: dict, source_code: str
    ) -> list[GateResult]:
        return [
            self._gate_typing(code_output, source_code),
            self._gate_null_safety(code_output, source_code),
            self._gate_complexity(code_output, source_code),
            self._gate_security(code_output, source_code),
            self._gate_error_handling(code_output, source_code),
            self._gate_testing(code_output),
            self._gate_over_engineering(code_output, source_code),
            self._gate_under_engineering(code_output, source_code),
        ]

    def _gate_typing(self, code_output: dict, source_code: str) -> GateResult:
        checks = []
        if not source_code:
            return GateResult(
                gate_id="typing",
                gate_name="Explicit Typing",
                status="warn",
                checks=[
                    GateCheck(
                        "typing_001", "warn", "No source code provided for analysis"
                    )
                ],
            )

        mypy_result = self._tool_runner.run_mypy(source_code)

        if mypy_result.status == "warn":
            checks.append(
                GateCheck(
                    "typing_mypy_install",
                    "warn",
                    mypy_result.error_message or "mypy not available",
                )
            )
        elif mypy_result.status == "error":
            checks.append(
                GateCheck(
                    "typing_mypy_error",
                    "warn",
                    mypy_result.error_message or "mypy execution failed",
                )
            )
        elif mypy_result.checks:
            for tc in mypy_result.checks:
                status = "fail" if tc.severity == "error" else "warn"
                checks.append(
                    GateCheck(
                        f"typing_mypy_{tc.check_id}",
                        status,
                        f"{tc.message}" + (f" (line {tc.line})" if tc.line else ""),
                    )
                )
        else:
            checks.append(GateCheck("typing_ok", "pass", "Type checking passed"))

        lang = self._detect_language(source_code)
        if lang in ("python",):
            if re.search(r"def\s+\w+\s*\([^)]*\)\s*:", source_code):
                funcs_without_return = re.findall(
                    r"def\s+(\w+)\s*\([^)]*\)\s*:\s*\n(?!\s*\"\"\")",
                    source_code,
                )
                for func in funcs_without_return:
                    checks.append(
                        GateCheck(
                            f"typing_{func}",
                            "warn",
                            f"Function '{func}' missing return type annotation",
                        )
                    )

            if re.search(r":\s*Any\b", source_code):
                checks.append(
                    GateCheck("typing_any", "warn", "Use of 'Any' type detected")
                )

        if not any(c.status == "fail" for c in checks):
            status = "pass"
        else:
            status = "fail"
        return GateResult(
            gate_id="typing", gate_name="Explicit Typing", status=status, checks=checks
        )

    def _gate_null_safety(self, code_output: dict, source_code: str) -> GateResult:
        checks = []
        if not source_code:
            return GateResult(
                gate_id="null_safety",
                gate_name="Null Safety",
                status="warn",
                checks=[GateCheck("null_001", "warn", "No source code provided")],
            )

        if re.search(r"if\s+\w+\s+is\s+None", source_code):
            checks.append(GateCheck("null_check", "pass", "Explicit None checks found"))
        elif re.search(r"if\s+not\s+\w+\s*:", source_code):
            checks.append(GateCheck("null_check", "pass", "Falsy checks found"))

        if re.search(r"\.get\s*\(", source_code):
            checks.append(
                GateCheck("null_safe_access", "pass", "Safe dict access with .get()")
            )

        if not checks:
            checks.append(
                GateCheck(
                    "null_warn", "warn", "No explicit null safety patterns detected"
                )
            )

        status = "pass"
        return GateResult(
            gate_id="null_safety", gate_name="Null Safety", status=status, checks=checks
        )

    def _gate_complexity(self, code_output: dict, source_code: str) -> GateResult:
        checks = []
        if not source_code:
            return GateResult(
                gate_id="complexity",
                gate_name="Complexity Guard",
                status="warn",
                checks=[GateCheck("cx_001", "warn", "No source code provided")],
            )

        nesting_depth = 0
        max_depth = 0
        for line in source_code.split("\n"):
            stripped = line.lstrip()
            if stripped.startswith(
                ("if ", "for ", "while ", "elif ", "except ", "with ")
            ):
                indent = len(line) - len(stripped)
                depth = indent // 4
                if depth > max_depth:
                    max_depth = depth

        if max_depth > 4:
            checks.append(
                GateCheck(
                    "cx_depth",
                    "fail",
                    f"Max nesting depth {max_depth} exceeds threshold (4)",
                )
            )
        elif max_depth > 3:
            checks.append(
                GateCheck(
                    "cx_depth",
                    "warn",
                    f"Nesting depth {max_depth} approaching threshold",
                )
            )
        else:
            checks.append(
                GateCheck("cx_depth", "pass", f"Nesting depth {max_depth} acceptable")
            )

        func_lines = re.findall(r"def\s+\w+.*?(?=\ndef\s|\Z)", source_code, re.DOTALL)
        for func in func_lines:
            lines = func.strip().split("\n")
            if len(lines) > 50:
                func_name = re.search(r"def\s+(\w+)", func)
                name = func_name.group(1) if func_name else "unknown"
                checks.append(
                    GateCheck(
                        f"cx_length_{name}",
                        "warn",
                        f"Function '{name}' has {len(lines)} lines",
                    )
                )

        if not any(c.status == "fail" for c in checks):
            status = "pass"
        else:
            status = "fail"

        return GateResult(
            gate_id="complexity",
            gate_name="Complexity Guard",
            status=status,
            checks=checks,
        )

    def _gate_security(self, code_output: dict, source_code: str) -> GateResult:
        checks = []
        if not source_code:
            return GateResult(
                gate_id="security",
                gate_name="Security Scan",
                status="warn",
                checks=[GateCheck("sec_001", "warn", "No source code provided")],
            )

        bandit_result = self._tool_runner.run_bandit(source_code)

        if bandit_result.status == "warn":
            checks.append(
                GateCheck(
                    "security_bandit_install",
                    "warn",
                    bandit_result.error_message or "bandit not available",
                )
            )
        elif bandit_result.status == "error":
            checks.append(
                GateCheck(
                    "security_bandit_error",
                    "warn",
                    bandit_result.error_message or "bandit execution failed",
                )
            )
        elif bandit_result.checks:
            for tc in bandit_result.checks:
                status = "fail" if tc.severity in ("high", "medium") else "warn"
                checks.append(
                    GateCheck(
                        f"security_bandit_{tc.check_id}",
                        status,
                        f"{tc.message}" + (f" (line {tc.line})" if tc.line else ""),
                    )
                )

        security_patterns = [
            (
                r"(?:password|secret|api_key|token)\s*=\s*['\"][^'\"]+['\"]",
                "sec_hardcoded_secret",
                "Hardcoded secret detected",
            ),
            (r"eval\s*\(", "sec_eval", "Use of eval() detected"),
            (r"exec\s*\(", "sec_exec", "Use of exec() detected"),
            (r"os\.system\s*\(", "sec_os_system", "Use of os.system() detected"),
            (
                r"subprocess\..*shell\s*=\s*True",
                "sec_shell_true",
                "subprocess with shell=True detected",
            ),
            (
                r"pickle\.loads?\s*\(",
                "sec_pickle",
                "Use of pickle detected (deserialization risk)",
            ),
        ]

        for pattern, check_id, message in security_patterns:
            if re.search(pattern, source_code):
                checks.append(GateCheck(check_id, "fail", message))

        if re.search(r"sqlite3\.connect|psycopg2|mysql\.connector", source_code):
            if re.search(
                r"f['\"].*SELECT|f['\"].*INSERT|f['\"].*UPDATE|f['\"].*DELETE",
                source_code,
            ):
                checks.append(
                    GateCheck(
                        "sec_sql_injection",
                        "fail",
                        "Potential SQL injection with f-string",
                    )
                )

        if not any(c.status == "fail" for c in checks):
            status = "pass"
        else:
            status = "fail"
        return GateResult(
            gate_id="security", gate_name="Security Scan", status=status, checks=checks
        )

    def _gate_error_handling(self, code_output: dict, source_code: str) -> GateResult:
        checks = []
        if not source_code:
            return GateResult(
                gate_id="error_handling",
                gate_name="Error Handling",
                status="warn",
                checks=[GateCheck("err_001", "warn", "No source code provided")],
            )

        if re.search(r"except\s*:", source_code):
            checks.append(
                GateCheck("err_bare_except", "fail", "Bare except clause detected")
            )
        elif re.search(r"except\s+Exception\s*:", source_code):
            checks.append(
                GateCheck(
                    "err_generic",
                    "warn",
                    "Generic Exception catch — consider specific types",
                )
            )

        if re.search(r"raise\s+", source_code) or re.search(r"except\s+", source_code):
            checks.append(
                GateCheck("err_strategy", "pass", "Error handling strategy present")
            )

        if not checks:
            checks.append(
                GateCheck("err_ok", "pass", "No error handling issues detected")
            )

        status = "fail" if any(c.status == "fail" for c in checks) else "pass"
        return GateResult(
            gate_id="error_handling",
            gate_name="Error Handling",
            status=status,
            checks=checks,
        )

    def _gate_testing(self, code_output: dict) -> GateResult:
        checks = []
        tests = code_output.get("tests", [])
        if not tests:
            checks.append(
                GateCheck("test_missing", "warn", "No tests proposed or executed")
            )
        else:
            checks.append(
                GateCheck(
                    "test_present", "pass", f"{len(tests)} test(s) proposed or executed"
                )
            )

        status = "warn" if any(c.status == "warn" for c in checks) else "pass"
        return GateResult(
            gate_id="testing", gate_name="Testing", status=status, checks=checks
        )

    # ── Specialized Gates (2x only) ──────────────────────────────

    def _execute_specialized_gates(
        self, code_output: dict, source_code: str
    ) -> list[GateResult]:
        return [
            self._gate_algorithmic_validation(code_output),
            self._gate_constraint_satisfaction(code_output),
            self._gate_correctness_invariants(code_output, source_code),
            self._gate_stress_test(code_output),
            self._gate_memory_layout(code_output),
        ]

    def _gate_algorithmic_validation(self, code_output: dict) -> GateResult:
        checks = []

        rationale = code_output.get("algorithm_selection_rationale", "")
        if not rationale or (
            isinstance(rationale, str) and len(rationale.strip()) < 10
        ):
            checks.append(
                GateCheck(
                    "algo_rationale",
                    "fail",
                    "No algorithm selection rationale provided",
                )
            )
        else:
            checks.append(
                GateCheck(
                    "algo_rationale", "pass", "Algorithm selection rationale present"
                )
            )

        cert = code_output.get("complexity_certificate")
        if cert:
            if isinstance(cert, dict):
                has_time = any(k in cert for k in ("time", "time_complexity"))
                has_space = any(k in cert for k in ("space", "space_complexity"))
                if has_time and has_space:
                    checks.append(
                        GateCheck(
                            "algo_complexity", "pass", "Complexity certificate complete"
                        )
                    )
                else:
                    checks.append(
                        GateCheck(
                            "algo_complexity",
                            "warn",
                            "Complexity certificate incomplete",
                        )
                    )
            elif isinstance(cert, str) and len(cert) > 10:
                checks.append(
                    GateCheck(
                        "algo_complexity", "pass", "Complexity certificate present"
                    )
                )
        else:
            checks.append(
                GateCheck(
                    "algo_complexity", "fail", "No complexity certificate provided"
                )
            )

        status = "fail" if any(c.status == "fail" for c in checks) else "pass"
        return GateResult(
            gate_id="algorithmic_validation",
            gate_name="Algorithmic Validation",
            status=status,
            checks=checks,
        )

    def _gate_constraint_satisfaction(self, code_output: dict) -> GateResult:
        checks = []

        constraints = code_output.get("constraints_found", {})
        if constraints:
            max_n = constraints.get("n", 0)
            if max_n >= 100000:
                cert = code_output.get("complexity_certificate", {})
                if isinstance(cert, dict):
                    time_str = str(cert.get("time", cert.get("time_complexity", "")))
                    normalized = time_str.lower().replace(" ", "")
                    if any(
                        token in normalized for token in ("o(n²)", "o(n^2)", "o(n*n)")
                    ):
                        checks.append(
                            GateCheck(
                                "constraint_n",
                                "fail",
                                f"O(n²) infeasible for n={max_n}",
                            )
                        )
                    elif (
                        "o(n" in normalized
                        or "o(log" in normalized
                        or "o(1)" in normalized
                    ):
                        checks.append(
                            GateCheck(
                                "constraint_n",
                                "pass",
                                f"Algorithm compatible with n={max_n}",
                            )
                        )
                    else:
                        checks.append(
                            GateCheck(
                                "constraint_n",
                                "warn",
                                f"Complexity unclear for n={max_n}",
                            )
                        )
                else:
                    checks.append(
                        GateCheck(
                            "constraint_n",
                            "warn",
                            "Cannot verify complexity for large n",
                        )
                    )

        overflow_check = False
        if isinstance(code_output.get("edge_case_analysis"), dict):
            overflow_check = code_output["edge_case_analysis"].get("overflow", False)
        if not overflow_check:
            checks.append(
                GateCheck(
                    "constraint_overflow",
                    "warn",
                    "Overflow risk not explicitly addressed",
                )
            )
        else:
            checks.append(
                GateCheck("constraint_overflow", "pass", "Overflow risk addressed")
            )

        status = "fail" if any(c.status == "fail" for c in checks) else "pass"
        return GateResult(
            gate_id="constraint_satisfaction",
            gate_name="Constraint Satisfaction",
            status=status,
            checks=checks,
        )

    def _gate_correctness_invariants(
        self, code_output: dict, source_code: str
    ) -> GateResult:
        checks = []

        if (
            isinstance(code_output.get("edge_case_analysis"), dict)
            and code_output["edge_case_analysis"]
        ):
            checks.append(
                GateCheck("inv_edge_cases", "pass", "Edge case analysis present")
            )
        else:
            checks.append(
                GateCheck(
                    "inv_edge_cases", "warn", "Edge case analysis missing or empty"
                )
            )

        if source_code:
            has_invariant_comment = bool(
                re.search(r"#\s*(invariant|invariante)", source_code, re.I)
            )
            has_docstring_invariant = bool(
                re.search(r"(invariant|precondition|postcondition)", source_code, re.I)
            )
            if has_invariant_comment or has_docstring_invariant:
                checks.append(
                    GateCheck("inv_documented", "pass", "Invariants documented in code")
                )
            else:
                checks.append(
                    GateCheck(
                        "inv_documented",
                        "warn",
                        "No explicit invariant documentation in code",
                    )
                )

        status = "fail" if any(c.status == "fail" for c in checks) else "pass"
        return GateResult(
            gate_id="correctness_invariants",
            gate_name="Correctness Invariant Verification",
            status=status,
            checks=checks,
        )

    def _gate_stress_test(self, code_output: dict) -> GateResult:
        checks = []

        stress_plan = code_output.get("stress_test_plan", "")
        if not stress_plan or (
            isinstance(stress_plan, str) and len(stress_plan.strip()) < 10
        ):
            checks.append(
                GateCheck("stress_plan", "fail", "No stress test plan provided")
            )
        else:
            checks.append(GateCheck("stress_plan", "pass", "Stress test plan present"))

            if "brute" in stress_plan.lower() or "reference" in stress_plan.lower():
                checks.append(
                    GateCheck(
                        "stress_brute",
                        "pass",
                        "Brute-force comparison mentioned in plan",
                    )
                )
            else:
                checks.append(
                    GateCheck(
                        "stress_brute", "warn", "Brute-force comparison not mentioned"
                    )
                )

        status = "fail" if any(c.status == "fail" for c in checks) else "pass"
        return GateResult(
            gate_id="stress_test",
            gate_name="Stress Test Pass",
            status=status,
            checks=checks,
        )

    def _gate_memory_layout(self, code_output: dict) -> GateResult:
        checks = []

        memory_est = code_output.get("memory_bound_estimate", "")
        if not memory_est or (
            isinstance(memory_est, str) and len(memory_est.strip()) < 10
        ):
            checks.append(
                GateCheck(
                    "memory_estimate", "fail", "No memory bound estimate provided"
                )
            )
        else:
            checks.append(
                GateCheck("memory_estimate", "pass", "Memory bound estimate present")
            )

        if isinstance(memory_est, str) and any(
            kw in memory_est.lower() for kw in ("cache", "allocation", "peak", "memory")
        ):
            checks.append(
                GateCheck("memory_detail", "pass", "Memory analysis includes detail")
            )
        else:
            checks.append(
                GateCheck("memory_detail", "warn", "Memory analysis lacks detail")
            )

        status = "fail" if any(c.status == "fail" for c in checks) else "pass"
        return GateResult(
            gate_id="memory_layout",
            gate_name="Memory Layout Audit",
            status=status,
            checks=checks,
        )

    # ── Aggregation ──────────────────────────────────────────────

    def _compute_overall_status(self, gates: list[GateResult]) -> str:
        if any(g.status == "fail" for g in gates):
            return "fail"
        if any(g.status == "warn" for g in gates):
            return "warn"
        return "pass"

    def _check_auto_reject(
        self,
        gates: list[GateResult],
        code_output: dict,
        is_2x: bool,
    ) -> tuple[bool, list[str]]:
        reasons = []

        for gate in gates:
            if gate.status == "fail":
                fail_checks = [c for c in gate.checks if c.status == "fail"]
                for check in fail_checks:
                    reasons.append(f"[{gate.gate_id}] {check.message}")

        if is_2x:
            required_2x = {
                "algorithm_selection_rationale",
                "complexity_certificate",
                "stress_test_plan",
                "memory_bound_estimate",
            }
            missing = required_2x - set(code_output.keys())
            if missing:
                reasons.append(f"Missing required 2x fields: {', '.join(missing)}")

        auto_reject = len(reasons) > 0
        return auto_reject, reasons

    def _detect_language(self, source_code: str) -> str:
        if source_code.startswith("#") or re.search(r"def\s+\w+", source_code):
            return "python"
        if re.search(r"function\s+\w+|const\s+\w+\s*=", source_code):
            return "javascript"
        if re.search(r"func\s+\w+", source_code):
            return "go"
        if re.search(r"fn\s+\w+|let\s+mut", source_code):
            return "rust"
        if re.search(r"(public|private|class)\s+\w+", source_code):
            return "java"
        return "unknown"

    def _gate_over_engineering(self, code_output: dict, source_code: str) -> GateResult:
        """Detect over-engineering in code."""
        detector = OverEngineeringDetector()

        tier = code_output.get("scope_classification", "tier_1_universal")
        if not tier:
            tier = "tier_1_universal"

        constraints = code_output.get("constraints_found", {})
        task_context = code_output.get("summary", "")

        checks = detector.detect(
            source_code=source_code,
            tier=tier,
            task_context=task_context if isinstance(task_context, str) else "",
            constraints=constraints if isinstance(constraints, dict) else {},
        )

        status = "fail" if any(c.status == "fail" for c in checks) else "pass"
        return GateResult(
            gate_id="over_engineering",
            gate_name="Over-Engineering Detection",
            status=status,
            checks=checks,
        )

    def _gate_under_engineering(
        self, code_output: dict, source_code: str
    ) -> GateResult:
        """Detect under-engineering in code."""
        detector = UnderEngineeringDetector()

        tier = code_output.get("scope_classification", "tier_1_universal")
        if not tier:
            tier = "tier_1_universal"

        constraints = code_output.get("constraints_found", {})

        checks = detector.detect(
            source_code=source_code,
            constraints=constraints if isinstance(constraints, dict) else {},
            tier=tier,
        )

        status = "fail" if any(c.status == "fail" for c in checks) else "pass"
        return GateResult(
            gate_id="under_engineering",
            gate_name="Under-Engineering Detection",
            status=status,
            checks=checks,
        )
