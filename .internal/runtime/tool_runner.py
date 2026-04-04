"""Tool Runner — Native execution of external linting/type checking/security tools.

Provides native integration with mypy, ruff, bandit, tsc, eslint, and other
static analysis tools. Executes tools via subprocess and parses results into
standardized GateCheck format.

Spec: .internal/specs/core/linting-tools.yaml
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LINTING_TOOLS_CONFIG = REPO_ROOT / ".internal" / "specs" / "core" / "linting-tools.yaml"


@dataclass
class ToolCheck:
    """Single issue detected by a tool."""

    tool: str
    check_id: str
    severity: str  # error, warning, info
    message: str
    line: int | None = None
    column: int | None = None
    file: str | None = None


@dataclass
class ToolResult:
    """Result of tool execution."""

    tool_name: str
    status: str  # pass, fail, warn, error
    checks: list[ToolCheck] = field(default_factory=list)
    execution_time_ms: float = 0.0
    raw_output: str = ""
    error_message: str | None = None

    @property
    def passed(self) -> bool:
        return self.status == "pass"


@dataclass
class ToolConfig:
    """Configuration for a single tool."""

    command: str
    args: list[str]
    timeout_sec: int
    parse_format: str  # json, text
    fail_on: list[str]


class ToolRunner:
    """Native tool executor for static analysis tools.

    Executes mypy, ruff, bandit, tsc, eslint and other tools natively
    via subprocess, parsing results into standardized ToolResult format.
    """

    def __init__(self, config_path: Path | None = None):
        self._config_path = config_path or LINTING_TOOLS_CONFIG
        self._config = self._load_config()
        self._temp_dir = None

    def _load_config(self) -> dict:
        if not self._config_path.exists():
            return {"tools": {}, "fallback_behavior": {}}
        return yaml.safe_load(self._config_path.read_text(encoding="utf-8"))

    def _ensure_temp_dir(self) -> Path:
        if self._temp_dir is None:
            self._temp_dir = tempfile.mkdtemp(prefix="hybrid_core_")
        return Path(self._temp_dir)

    def cleanup(self) -> None:
        """Clean up temporary files."""
        import shutil as sh

        if self._temp_dir and Path(self._temp_dir).exists():
            try:
                sh.rmtree(self._temp_dir)
            except Exception:
                pass
            self._temp_dir = None

    def _is_tool_available(self, tool_command: str) -> bool:
        """Check if a tool is available in PATH."""
        cmd = tool_command.split()[0]
        if cmd.startswith("npx"):
            result = subprocess.run(
                [
                    "npx",
                    "--yes",
                    tool_command.split()[1]
                    if len(tool_command.split()) > 1
                    else "--version",
                ],
                capture_output=True,
                timeout=10,
            )
            return result.returncode == 0
        return shutil.which(cmd) is not None

    def _create_temp_file(self, code: str, extension: str = ".py") -> Path:
        """Create a temporary file with the given code."""
        temp_dir = self._ensure_temp_dir()
        temp_file = temp_dir / f"temp_check{extension}"
        temp_file.write_text(code, encoding="utf-8")
        return temp_file

    def _run_command(
        self,
        command: str,
        args: list[str],
        timeout: int,
        cwd: Path | None = None,
    ) -> tuple[int, str, str]:
        """Run a command and return (returncode, stdout, stderr)."""
        cmd = [command] + args
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=timeout,
                cwd=str(cwd) if cwd else None,
                text=True,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"Command timed out after {timeout}s"
        except FileNotFoundError:
            return -2, "", f"Command not found: {command}"
        except Exception as e:
            return -3, "", str(e)

    def run_mypy(
        self,
        source_code: str,
        file_name: str = "check.py",
    ) -> ToolResult:
        """Execute mypy type checker on source code."""
        tool_config = (
            self._config.get("tools", {}).get("python", {}).get("type_checker", {})
        )

        if not tool_config:
            return ToolResult(
                tool_name="mypy",
                status="error",
                error_message="mypy not configured",
            )

        temp_file = self._create_temp_file(source_code, ".py")
        start_time = datetime.now()

        command = tool_config.get("command", "mypy")
        args = [
            arg.replace("{file}", str(temp_file)) for arg in tool_config.get("args", [])
        ]
        timeout = tool_config.get("timeout_sec", 30)

        returncode, stdout, stderr = self._run_command(command, args, timeout)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        if returncode == -2:
            return ToolResult(
                tool_name="mypy",
                status="warn",
                error_message="mypy not installed. Install with: pip install mypy",
                execution_time_ms=execution_time,
            )

        if returncode == -1:
            return ToolResult(
                tool_name="mypy",
                status="error",
                error_message=f"mypy execution timed out after {timeout}s",
                execution_time_ms=execution_time,
            )

        checks = self._parse_mypy_output(stdout + stderr, returncode)
        status = self._determine_status(checks, returncode, tool_config)

        return ToolResult(
            tool_name="mypy",
            status=status,
            checks=checks,
            execution_time_ms=execution_time,
            raw_output=stdout + stderr,
        )

    def run_ruff(
        self,
        source_code: str,
        file_name: str = "check.py",
    ) -> ToolResult:
        """Execute ruff linter on source code."""
        tool_config = self._config.get("tools", {}).get("python", {}).get("linter", {})

        if not tool_config:
            return ToolResult(
                tool_name="ruff",
                status="error",
                error_message="ruff not configured",
            )

        temp_file = self._create_temp_file(source_code, ".py")
        start_time = datetime.now()

        command = tool_config.get("command", "ruff")
        args = [
            arg.replace("{file}", str(temp_file)) for arg in tool_config.get("args", [])
        ]
        timeout = tool_config.get("timeout_sec", 15)

        returncode, stdout, stderr = self._run_command(command, args, timeout)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        if returncode == -2:
            return ToolResult(
                tool_name="ruff",
                status="warn",
                error_message="ruff not installed. Install with: pip install ruff",
                execution_time_ms=execution_time,
            )

        if returncode == -1:
            return ToolResult(
                tool_name="ruff",
                status="error",
                error_message=f"ruff execution timed out after {timeout}s",
                execution_time_ms=execution_time,
            )

        checks = self._parse_ruff_output(stdout, returncode)
        status = self._determine_status(checks, returncode, tool_config)

        return ToolResult(
            tool_name="ruff",
            status=status,
            checks=checks,
            execution_time_ms=execution_time,
            raw_output=stdout,
        )

    def run_bandit(
        self,
        source_code: str,
        file_name: str = "check.py",
    ) -> ToolResult:
        """Execute bandit security scanner on source code."""
        tool_config = (
            self._config.get("tools", {}).get("python", {}).get("security", {})
        )

        if not tool_config:
            return ToolResult(
                tool_name="bandit",
                status="error",
                error_message="bandit not configured",
            )

        temp_file = self._create_temp_file(source_code, ".py")
        start_time = datetime.now()

        command = tool_config.get("command", "bandit")
        args = [
            arg.replace("{file}", str(temp_file)) for arg in tool_config.get("args", [])
        ]
        timeout = tool_config.get("timeout_sec", 20)

        returncode, stdout, stderr = self._run_command(command, args, timeout)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        if returncode == -2:
            return ToolResult(
                tool_name="bandit",
                status="warn",
                error_message="bandit not installed. Install with: pip install bandit",
                execution_time_ms=execution_time,
            )

        if returncode == -1:
            return ToolResult(
                tool_name="bandit",
                status="error",
                error_message=f"bandit execution timed out after {timeout}s",
                execution_time_ms=execution_time,
            )

        checks = self._parse_bandit_output(stdout, returncode)
        status = self._determine_status(checks, returncode, tool_config)

        return ToolResult(
            tool_name="bandit",
            status=status,
            checks=checks,
            execution_time_ms=execution_time,
            raw_output=stdout,
        )

    def run_tsc(
        self,
        source_code: str,
        file_name: str = "check.ts",
    ) -> ToolResult:
        """Execute TypeScript compiler (tsc) on source code."""
        tool_config = (
            self._config.get("tools", {}).get("typescript", {}).get("type_checker", {})
        )

        if not tool_config:
            tool_config = (
                self._config.get("tools", {})
                .get("javascript", {})
                .get("type_checker", {})
            )

        if not tool_config:
            return ToolResult(
                tool_name="tsc",
                status="error",
                error_message="tsc not configured",
            )

        temp_file = self._create_temp_file(source_code, ".ts")
        start_time = datetime.now()

        command = tool_config.get("command", "npx")
        args = [
            arg.replace("{file}", str(temp_file)) for arg in tool_config.get("args", [])
        ]
        timeout = tool_config.get("timeout_sec", 30)

        returncode, stdout, stderr = self._run_command(command, args, timeout)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        if returncode == -2:
            return ToolResult(
                tool_name="tsc",
                status="warn",
                error_message="tsc not installed. Install with: npm install -g typescript",
                execution_time_ms=execution_time,
            )

        if returncode == -1:
            return ToolResult(
                tool_name="tsc",
                status="error",
                error_message=f"tsc execution timed out after {timeout}s",
                execution_time_ms=execution_time,
            )

        checks = self._parse_tsc_output(stdout + stderr, returncode)
        status = self._determine_status(checks, returncode, tool_config)

        return ToolResult(
            tool_name="tsc",
            status=status,
            checks=checks,
            execution_time_ms=execution_time,
            raw_output=stdout + stderr,
        )

    def run_eslint(
        self,
        source_code: str,
        file_name: str = "check.js",
    ) -> ToolResult:
        """Execute ESLint on source code."""
        tool_config = (
            self._config.get("tools", {}).get("javascript", {}).get("linter", {})
        )

        if not tool_config:
            return ToolResult(
                tool_name="eslint",
                status="error",
                error_message="eslint not configured",
            )

        temp_file = self._create_temp_file(source_code, ".js")
        start_time = datetime.now()

        command = tool_config.get("command", "npx")
        args = [
            arg.replace("{file}", str(temp_file)) for arg in tool_config.get("args", [])
        ]
        timeout = tool_config.get("timeout_sec", 20)

        returncode, stdout, stderr = self._run_command(command, args, timeout)

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        if returncode == -2:
            return ToolResult(
                tool_name="eslint",
                status="warn",
                error_message="eslint not installed. Install with: npm install -g eslint",
                execution_time_ms=execution_time,
            )

        if returncode == -1:
            return ToolResult(
                tool_name="eslint",
                status="error",
                error_message=f"eslint execution timed out after {timeout}s",
                execution_time_ms=execution_time,
            )

        checks = self._parse_eslint_output(stdout, returncode)
        status = self._determine_status(checks, returncode, tool_config)

        return ToolResult(
            tool_name="eslint",
            status=status,
            checks=checks,
            execution_time_ms=execution_time,
            raw_output=stdout,
        )

    def _parse_mypy_output(self, output: str, returncode: int) -> list[ToolCheck]:
        """Parse mypy JSON output."""
        checks = []

        try:
            for line in output.strip().split("\n"):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    for item in data:
                        checks.append(
                            ToolCheck(
                                tool="mypy",
                                check_id=item.get("code", "mypy"),
                                severity=item.get("severity", "error"),
                                message=item.get("message", ""),
                                line=item.get("line"),
                                column=item.get("column"),
                                file=item.get("file"),
                            )
                        )
                except json.JSONDecodeError:
                    pass
        except Exception:
            pass

        if not checks and output.strip():
            for line in output.strip().split("\n"):
                match = re.search(r"(.+?):(\d+):(.+?):\s*(.+)", line)
                if match:
                    checks.append(
                        ToolCheck(
                            tool="mypy",
                            check_id="mypy",
                            severity="error",
                            message=match.group(4),
                            line=int(match.group(2)),
                            file=match.group(1),
                        )
                    )

        return checks

    def _parse_ruff_output(self, output: str, returncode: int) -> list[ToolCheck]:
        """Parse ruff JSON output."""
        checks = []

        try:
            data = json.loads(output) if output.strip() else []
            if isinstance(data, list):
                for item in data:
                    checks.append(
                        ToolCheck(
                            tool="ruff",
                            check_id=item.get("code", {}).get("value", "ruff"),
                            severity=item.get("severity", "error"),
                            message=item.get("message", ""),
                            line=item.get("location", {}).get("row"),
                            column=item.get("location", {}).get("column"),
                            file=item.get("filename"),
                        )
                    )
        except (json.JSONDecodeError, TypeError):
            pass

        return checks

    def _parse_bandit_output(self, output: str, returncode: int) -> list[ToolCheck]:
        """Parse bandit JSON output."""
        checks = []

        try:
            data = json.loads(output) if output.strip() else {}
            issues = data.get("results", [])
            for issue in issues:
                severity = issue.get("issue_severity", "LOW")
                if severity not in ["LOW", "MEDIUM", "HIGH"]:
                    severity = "MEDIUM"
                checks.append(
                    ToolCheck(
                        tool="bandit",
                        check_id=issue.get("issue_id", "bandit"),
                        severity=severity.lower(),
                        message=issue.get("issue_text", ""),
                        line=issue.get("line_number"),
                        file=issue.get("filename"),
                    )
                )
        except (json.JSONDecodeError, TypeError):
            pass

        return checks

    def _parse_tsc_output(self, output: str, returncode: int) -> list[ToolCheck]:
        """Parse tsc text output."""
        checks = []

        for line in output.strip().split("\n"):
            match = re.search(r"(.+?)\((\d+),\d+\):\s*(.+)", line)
            if match:
                severity = "error" if "error" in line.lower() else "warning"
                checks.append(
                    ToolCheck(
                        tool="tsc",
                        check_id="tsc",
                        severity=severity,
                        message=match.group(3),
                        line=int(match.group(2)),
                        file=match.group(1),
                    )
                )

        return checks

    def _parse_eslint_output(self, output: str, returncode: int) -> list[ToolCheck]:
        """Parse eslint JSON output."""
        checks = []

        try:
            data = json.loads(output) if output.strip() else []
            if isinstance(data, list):
                for item in data:
                    checks.append(
                        ToolCheck(
                            tool="eslint",
                            check_id=item.get("ruleId", "eslint"),
                            severity=item.get("severity", 2) > 1
                            and "error"
                            or "warning",
                            message=item.get("message", ""),
                            line=item.get("line"),
                            column=item.get("column"),
                            file=item.get("filePath"),
                        )
                    )
        except (json.JSONDecodeError, TypeError):
            pass

        return checks

    def _determine_status(
        self,
        checks: list[ToolCheck],
        returncode: int,
        tool_config: dict,
    ) -> str:
        """Determine overall status from checks and returncode."""
        fail_on = tool_config.get("fail_on", [])

        severities = {c.severity for c in checks}

        if "error" in fail_on and "error" in severities:
            return "fail"
        if "warning" in fail_on and "warning" in severities:
            return "fail"
        if "note" in fail_on and "note" in severities:
            return "warn"

        if returncode != 0 and returncode != -1:
            return "fail"

        if any(c.severity == "error" for c in checks):
            return "fail"
        if any(c.severity == "warning" for c in checks):
            return "warn"

        return "pass"

    def detect_language(self, source_code: str) -> str:
        """Detect programming language from source code."""
        if re.search(r"def\s+\w+\s*\(", source_code) and not re.search(
            r"func\s+\w+", source_code
        ):
            return "python"
        if re.search(r"function\s+\w+|const\s+\w+\s*=", source_code):
            return "javascript"
        if re.search(r"interface\s+\w+|:\s*(string|number|boolean)\b", source_code):
            return "typescript"
        if re.search(r"func\s+\w+|package\s+\w+", source_code):
            return "go"
        if re.search(r"fn\s+\w+|let\s+mut", source_code):
            return "rust"
        if re.search(r"public\s+class|private\s+class", source_code):
            return "java"
        return "unknown"

    def run_all_tools(
        self,
        source_code: str,
        language: str | None = None,
    ) -> list[ToolResult]:
        """Run all applicable tools for the given source code."""
        if language is None:
            language = self.detect_language(source_code)

        results = []

        if language == "python":
            results.append(self.run_mypy(source_code))
            results.append(self.run_ruff(source_code))
            results.append(self.run_bandit(source_code))
        elif language == "javascript":
            results.append(self.run_eslint(source_code))
        elif language == "typescript":
            results.append(self.run_tsc(source_code))
            results.append(self.run_eslint(source_code))
        elif language == "go":
            pass  # go vet would be added here
        elif language == "rust":
            pass  # cargo clippy would be added here

        return results
