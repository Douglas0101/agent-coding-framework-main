#!/usr/bin/env python3
"""Script de automação para qualidade de código.

Executa lint/formatação com Ruff e gates avançados para geração segura
de algoritmos (complexidade, injeção, desserialização e criptografia).
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
import tomllib
from collections import Counter
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass
class LintResult:
    """Resultado de uma execução de lint."""

    tool: str
    passed: bool
    error_count: int
    fixed_count: int
    output: str
    metadata: dict[str, object] = field(default_factory=dict)


PROJECT_ROOT = Path(__file__).parents[4]

IGNORED_PATH_PARTS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "artifacts",
    "outputs",
    "outputs_prod",
    ".cache",
    "cache",
}
SENSITIVE_PATH_HINTS = {
    "auth",
    "credential",
    "crypto",
    "key",
    "password",
    "secret",
    "token",
}

SEC_EVAL_NAMES = {"eval", "exec", "builtins.eval", "builtins.exec"}
SEC_OS_COMMAND_NAMES = {"os.system"}
SEC_SHELLABLE_SUBPROCESS_NAMES = {
    "subprocess.call",
    "subprocess.check_call",
    "subprocess.check_output",
    "subprocess.Popen",
    "subprocess.run",
}
SEC_UNSAFE_DESERIALIZATION_NAMES = {
    "pickle.load",
    "pickle.loads",
    "dill.loads",
    "marshal.loads",
}
SEC_INSECURE_HASH_NAMES = {"hashlib.md5", "hashlib.sha1"}
SEC_PSEUDORANDOM_NAMES = {
    "random.choice",
    "random.randint",
    "random.randrange",
    "random.random",
    "random.randbytes",
    "random.uniform",
}

PYPROJECT_FILE = PROJECT_ROOT / "pyproject.toml"
SETUP_FILE = PROJECT_ROOT / "setup.py"
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"
SECURITY_WORKFLOW_FILE = (
    PROJECT_ROOT / ".github" / "workflows" / "security.yml"
)
CI_WORKFLOW_FILE = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
SECURITY_TEST_FILE = PROJECT_ROOT / "tests" / "test_security.py"
SECURITY_PRIMITIVES_FILE = PROJECT_ROOT / "src" / "security" / "primitives.py"
SECURITY_CRYPTO_FILE = PROJECT_ROOT / "src" / "security" / "crypto.py"


@dataclass(slots=True)
class GateFinding:
    """One finding emitted by algorithm/security gate analyzers."""

    rule_id: str
    path: str
    line: int
    message: str


def run_command(
    cmd: Sequence[str], capture: bool = True
) -> tuple[int, str, str]:
    """Executa um comando e retorna código, stdout e stderr."""
    result = subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        cwd=PROJECT_ROOT,  # Raiz do projeto
    )
    return result.returncode, result.stdout, result.stderr


def _summarize_ruff_issues(
    issues: list[dict[str, object]],
) -> dict[str, object]:
    rule_counts = Counter()
    file_counts = Counter()
    for issue in issues:
        code = issue.get("code")
        filename = issue.get("filename")
        if isinstance(code, str):
            rule_counts[code] += 1
        if isinstance(filename, str):
            file_counts[filename] += 1
    return {
        "rule_counts": dict(rule_counts.most_common(10)),
        "file_counts": dict(file_counts.most_common(10)),
    }


def _build_ruff_args(args: argparse.Namespace) -> list[str]:
    ruff_args: list[str] = []
    if args.select:
        ruff_args.extend(["--select", args.select])
    if args.ignore:
        ruff_args.extend(["--ignore", args.ignore])
    if args.extend_select:
        ruff_args.extend(["--extend-select", args.extend_select])
    if args.extend_ignore:
        ruff_args.extend(["--extend-ignore", args.extend_ignore])
    return ruff_args


def _git_changed_files(staged: bool) -> list[str]:
    cmd = ["git", "diff", "--name-only"]
    if staged:
        cmd.append("--cached")
    code, stdout, _stderr = run_command(cmd)
    if code != 0:
        return []
    files = [line.strip() for line in stdout.splitlines() if line.strip()]
    return [f for f in files if f.endswith(".py")]


def _resolve_paths(args: argparse.Namespace) -> list[str]:
    if args.paths:
        return list(args.paths)

    if args.staged:
        return _git_changed_files(staged=True)

    if args.changed:
        staged = _git_changed_files(staged=True)
        unstaged = _git_changed_files(staged=False)
        return sorted(set(staged + unstaged))

    return ["."]


def _to_project_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _is_ignored_path(path: Path) -> bool:
    path_parts = set(path.parts)
    return bool(path_parts & IGNORED_PATH_PARTS)


def _iter_python_files(paths: Sequence[str]) -> list[Path]:
    discovered: list[Path] = []
    seen: set[Path] = set()

    for raw_path in paths:
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = PROJECT_ROOT / candidate
        if not candidate.exists():
            continue

        if candidate.is_file():
            if candidate.suffix != ".py" or _is_ignored_path(candidate):
                continue
            resolved = candidate.resolve()
            if resolved not in seen:
                seen.add(resolved)
                discovered.append(resolved)
            continue

        for py_file in candidate.rglob("*.py"):
            if _is_ignored_path(py_file):
                continue
            resolved = py_file.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            discovered.append(resolved)

    return discovered


def _safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _find_line_number(content: str, needle: str) -> int:
    if not content or not needle:
        return 1
    for idx, line in enumerate(content.splitlines(), start=1):
        if needle in line:
            return idx
    return 1


def _normalize_dependency_name(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def _extract_requirements_packages(requirements_content: str) -> set[str]:
    packages: set[str] = set()
    for raw_line in requirements_content.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        line = line.split(";", 1)[0].strip()
        match = re.match(r"([A-Za-z0-9_.-]+)", line)
        if not match:
            continue
        packages.add(_normalize_dependency_name(match.group(1)))
    return packages


def _requirements_has_package(requirements: set[str], package: str) -> bool:
    return _normalize_dependency_name(package) in requirements


def _python_module_cmd(module: str, *args: str) -> list[str]:
    """Build a command bound to the current interpreter environment."""
    return [sys.executable, "-m", module, *args]


def _workflow_installs_package(workflow_content: str, package: str) -> bool:
    normalized = re.escape(_normalize_dependency_name(package))
    pattern = re.compile(
        rf"pip\s+install[^\n]*\b{normalized}\b", re.IGNORECASE
    )
    return bool(pattern.search(workflow_content))


def _extract_python_requires_from_setup(setup_content: str) -> str | None:
    match = re.search(
        r"python_requires\s*=\s*['\"]([^'\"]+)['\"]",
        setup_content,
    )
    if not match:
        return None
    return match.group(1).strip()


def _extract_min_python_version(specifier: str) -> tuple[int, int] | None:
    match = re.search(r">=\s*(\d+)\.(\d+)", specifier)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _extract_workflow_python_versions(
    workflow_content: str,
) -> list[tuple[str, int]]:
    versions: list[tuple[str, int]] = []
    for idx, line in enumerate(workflow_content.splitlines(), start=1):
        if "python-version" not in line:
            continue
        for version in re.findall(r"(\d+\.\d+)", line):
            versions.append((version, idx))
    return versions


def _file_imports_module(path: Path, module_name: str) -> bool:
    source = _safe_read_text(path)
    if not source:
        return False
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return False

    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(
            alias.name.split(".")[0] == module_name for alias in node.names
        ):
            return True
        if (
            isinstance(node, ast.ImportFrom)
            and (node.module or "").split(".")[0] == module_name
        ):
            return True
    return False


def check_engineering_gate() -> LintResult:
    """Run engineering guardrails for dependency and CI contracts."""
    findings: list[GateFinding] = []

    pyproject_content = _safe_read_text(PYPROJECT_FILE)
    setup_content = _safe_read_text(SETUP_FILE)
    requirements_content = _safe_read_text(REQUIREMENTS_FILE)
    security_workflow_content = _safe_read_text(SECURITY_WORKFLOW_FILE)
    ci_workflow_content = _safe_read_text(CI_WORKFLOW_FILE)

    if not pyproject_content:
        findings.append(
            GateFinding(
                rule_id="ENG900",
                path=str(PYPROJECT_FILE.relative_to(PROJECT_ROOT)),
                line=1,
                message="pyproject.toml ausente; metadados de build nao podem ser validados.",
            )
        )
        return _build_gate_result("engineering-gate", findings)

    try:
        pyproject_data = tomllib.loads(pyproject_content)
    except tomllib.TOMLDecodeError as exc:
        findings.append(
            GateFinding(
                rule_id="ENG901",
                path=str(PYPROJECT_FILE.relative_to(PROJECT_ROOT)),
                line=exc.lineno or 1,
                message="pyproject.toml invalido; corrija antes de rodar gates.",
            )
        )
        return _build_gate_result("engineering-gate", findings)

    project_data = pyproject_data.get("project")
    requires_python: str | None = None
    if not isinstance(project_data, dict):
        findings.append(
            GateFinding(
                rule_id="ENG001",
                path=str(PYPROJECT_FILE.relative_to(PROJECT_ROOT)),
                line=_find_line_number(pyproject_content, "[project]"),
                message="Secao [project] ausente no pyproject.toml.",
            )
        )
    else:
        version_value = project_data.get("version")
        if not isinstance(version_value, str) or not version_value.strip():
            findings.append(
                GateFinding(
                    rule_id="ENG002",
                    path=str(PYPROJECT_FILE.relative_to(PROJECT_ROOT)),
                    line=_find_line_number(pyproject_content, "version ="),
                    message="`project.version` obrigatoria para build/install editavel.",
                )
            )

        requires_python_value = project_data.get("requires-python")
        if not isinstance(requires_python_value, str):
            findings.append(
                GateFinding(
                    rule_id="ENG003",
                    path=str(PYPROJECT_FILE.relative_to(PROJECT_ROOT)),
                    line=_find_line_number(
                        pyproject_content, "requires-python ="
                    ),
                    message="`project.requires-python` deve ser definido e versionado.",
                )
            )
        else:
            requires_python = requires_python_value.strip()

    setup_python_requires = _extract_python_requires_from_setup(setup_content)
    if requires_python and not setup_python_requires:
        findings.append(
            GateFinding(
                rule_id="ENG004",
                path=str(SETUP_FILE.relative_to(PROJECT_ROOT)),
                line=_find_line_number(setup_content, "setup("),
                message="`setup.py` sem python_requires; alinhe com pyproject.",
            )
        )
    elif (
        requires_python
        and setup_python_requires
        and setup_python_requires.replace(" ", "")
        != requires_python.replace(" ", "")
    ):
        findings.append(
            GateFinding(
                rule_id="ENG005",
                path=str(SETUP_FILE.relative_to(PROJECT_ROOT)),
                line=_find_line_number(setup_content, "python_requires="),
                message=(
                    "python_requires em setup.py diverge de project.requires-python "
                    "no pyproject.toml."
                ),
            )
        )

    requirements_packages = _extract_requirements_packages(
        requirements_content
    )
    security_uses_cryptography = any(
        "from cryptography" in _safe_read_text(path)
        for path in (SECURITY_PRIMITIVES_FILE, SECURITY_CRYPTO_FILE)
    )
    if security_uses_cryptography and not _requirements_has_package(
        requirements_packages, "cryptography"
    ):
        findings.append(
            GateFinding(
                rule_id="ENG006",
                path=str(REQUIREMENTS_FILE.relative_to(PROJECT_ROOT)),
                line=1,
                message=(
                    "Modulo de seguranca importa cryptography, mas requirements.txt "
                    "nao declara a dependencia."
                ),
            )
        )

    security_tests_use_torch = _file_imports_module(
        SECURITY_TEST_FILE, "torch"
    )
    if security_tests_use_torch:
        torch_available = _requirements_has_package(
            requirements_packages, "torch"
        ) or _workflow_installs_package(security_workflow_content, "torch")
        if not torch_available:
            findings.append(
                GateFinding(
                    rule_id="ENG007",
                    path=str(SECURITY_WORKFLOW_FILE.relative_to(PROJECT_ROOT)),
                    line=_find_line_number(
                        security_workflow_content, "Install dependencies"
                    ),
                    message=(
                        "tests/test_security.py importa torch, mas o workflow de "
                        "security nao instala torch."
                    ),
                )
            )

    if requires_python:
        minimum = _extract_min_python_version(requires_python)
        if minimum is not None:
            for workflow_path, workflow_content in (
                (SECURITY_WORKFLOW_FILE, security_workflow_content),
                (CI_WORKFLOW_FILE, ci_workflow_content),
            ):
                for version, line in _extract_workflow_python_versions(
                    workflow_content
                ):
                    parsed = _extract_min_python_version(f">={version}")
                    if parsed is None:
                        continue
                    if parsed < minimum:
                        findings.append(
                            GateFinding(
                                rule_id="ENG008",
                                path=str(
                                    workflow_path.relative_to(PROJECT_ROOT)
                                ),
                                line=line,
                                message=(
                                    "Workflow testa Python abaixo do baseline definido "
                                    "em project.requires-python."
                                ),
                            )
                        )

    return _build_gate_result("engineering-gate", findings)


def _is_constant_true(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value is True


def _contains_break(node: ast.AST) -> bool:
    return any(isinstance(child, ast.Break) for child in ast.walk(node))


def _contains_return(node: ast.AST) -> bool:
    """Check if a while loop body contains a return statement (exit path)."""
    return any(isinstance(child, ast.Return) for child in ast.walk(node))


def _has_shell_true_keyword(node: ast.Call) -> bool:
    for keyword in node.keywords:
        if keyword.arg != "shell":
            continue
        if (
            isinstance(keyword.value, ast.Constant)
            and keyword.value.value is True
        ):
            return True
    return False


class AlgorithmSecurityVisitor(ast.NodeVisitor):
    """AST visitor to enforce advanced algorithm and security guardrails."""

    def __init__(self, path: Path, max_loop_depth: int):
        self.path = path
        self.path_str = _to_project_relative(path)
        self.max_loop_depth = max_loop_depth
        self.aliases: dict[str, str] = {}
        self.findings: list[GateFinding] = []
        self.loop_depth = 0
        lowered_path = self.path_str.lower()
        self.is_security_test = "tests/security/" in lowered_path
        self.sensitive_context = any(
            hint in lowered_path for hint in SENSITIVE_PATH_HINTS
        )

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            local_name = alias.asname or alias.name
            self.aliases[local_name] = alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            local_name = alias.asname or alias.name
            qualified = f"{module}.{alias.name}" if module else alias.name
            self.aliases[local_name] = qualified
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self._visit_loop(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._visit_loop(node)

    def visit_While(self, node: ast.While) -> None:
        if _is_constant_true(node.test) and not _contains_break(node) and not _contains_return(node):
            self._add_finding(
                "ALG002",
                node.lineno,
                "`while True` sem break detectado; adicione limite/timeout explicito.",
            )
        self._visit_loop(node)

    def _visit_loop(self, node: ast.For | ast.AsyncFor | ast.While) -> None:
        self.loop_depth += 1
        if self.loop_depth > self.max_loop_depth:
            self._add_finding(
                "ALG001",
                node.lineno,
                (
                    "Profundidade de loop excedeu o limite "
                    f"({self.max_loop_depth}); refatore para reduzir complexidade."
                ),
            )
        self.generic_visit(node)
        self.loop_depth -= 1

    def visit_Call(self, node: ast.Call) -> None:
        call_name = self._resolve_call_name(node.func)
        if not call_name:
            self.generic_visit(node)
            return

        if self._is_dynamic_exec_call(node, call_name):
            self._add_finding(
                "SEC001",
                node.lineno,
                "Uso de eval/exec detectado; prefira parser seguro ou dispatch explicito.",
            )

        if call_name in SEC_OS_COMMAND_NAMES:
            self._add_finding(
                "SEC002",
                node.lineno,
                "Uso de os.system detectado; prefira subprocess com lista de argumentos.",
            )

        if (
            call_name in SEC_SHELLABLE_SUBPROCESS_NAMES
            and _has_shell_true_keyword(node)
        ):
            self._add_finding(
                "SEC003",
                node.lineno,
                "subprocess com shell=True detectado; risco de command injection.",
            )

        if call_name in SEC_UNSAFE_DESERIALIZATION_NAMES and not getattr(self, "is_security_test", False):
            self._add_finding(
                "SEC004",
                node.lineno,
                "Desserializacao insegura detectada; use formato validado (JSON/schema).",
            )

        if call_name == "yaml.load" and not self._uses_safe_yaml_loader(node):
            self._add_finding(
                "SEC005",
                node.lineno,
                "yaml.load sem SafeLoader detectado; use yaml.safe_load.",
            )

        if call_name in SEC_INSECURE_HASH_NAMES:
            self._add_finding(
                "SEC006",
                node.lineno,
                "Hash inseguro (md5/sha1) detectado; use sha256+ ou BLAKE2.",
            )

        if self.sensitive_context and call_name in SEC_PSEUDORANDOM_NAMES:
            self._add_finding(
                "SEC007",
                node.lineno,
                "random.* em contexto sensivel detectado; prefira secrets.SystemRandom.",
            )

        self.generic_visit(node)

    def _is_dynamic_exec_call(self, node: ast.Call, call_name: str) -> bool:
        if isinstance(node.func, ast.Name):
            return node.func.id in {"eval", "exec"}

        if isinstance(node.func, ast.Attribute):
            if (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "builtins"
                and node.func.attr in {"eval", "exec"}
            ):
                return True
            return call_name in {"builtins.eval", "builtins.exec"}

        return call_name in SEC_EVAL_NAMES

    def _uses_safe_yaml_loader(self, node: ast.Call) -> bool:
        for keyword in node.keywords:
            if keyword.arg != "Loader":
                continue
            loader_name = self._resolve_call_name(keyword.value)
            if not loader_name:
                continue
            if loader_name.endswith("SafeLoader") or loader_name.endswith(
                "CSafeLoader"
            ):
                return True
        return False

    def _resolve_call_name(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return self.aliases.get(node.id, node.id)

        if isinstance(node, ast.Attribute):
            parent = self._resolve_call_name(node.value)
            if not parent:
                return node.attr
            return f"{parent}.{node.attr}"

        return None

    def _add_finding(self, rule_id: str, line: int, message: str) -> None:
        self.findings.append(
            GateFinding(
                rule_id=rule_id, path=self.path_str, line=line, message=message
            )
        )


def _scan_algorithm_security_findings(
    paths: Sequence[str],
    max_loop_depth: int,
) -> list[GateFinding]:
    findings: list[GateFinding] = []
    for file_path in _iter_python_files(paths):
        try:
            source = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            source = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        try:
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError as exc:
            findings.append(
                GateFinding(
                    rule_id="ALG900",
                    path=_to_project_relative(file_path),
                    line=exc.lineno or 1,
                    message="Erro de sintaxe impedindo analise do gate de algoritmo.",
                )
            )
            continue

        visitor = AlgorithmSecurityVisitor(
            file_path, max_loop_depth=max_loop_depth
        )
        visitor.visit(tree)
        findings.extend(visitor.findings)

    return findings


def _build_gate_result(tool: str, findings: list[GateFinding]) -> LintResult:
    if not findings:
        return LintResult(
            tool=tool,
            passed=True,
            error_count=0,
            fixed_count=0,
            output="No issues found.",
            metadata={"skipped": False},
        )

    rule_counts = Counter(item.rule_id for item in findings)
    file_counts = Counter(item.path for item in findings)
    output_lines = [
        f"{item.path}:{item.line} [{item.rule_id}] {item.message}"
        for item in findings
    ]

    return LintResult(
        tool=tool,
        passed=False,
        error_count=len(findings),
        fixed_count=0,
        output="\n".join(output_lines),
        metadata={
            "rule_counts": dict(rule_counts.most_common(10)),
            "file_counts": dict(file_counts.most_common(10)),
        },
    )


def check_algorithm_gate(
    paths: Sequence[str],
    max_loop_depth: int,
    findings: list[GateFinding] | None = None,
) -> LintResult:
    """Run advanced algorithm guardrails focused on complexity boundaries."""
    files = _iter_python_files(paths)
    if not files:
        return LintResult(
            tool="algorithm-gate",
            passed=True,
            error_count=0,
            fixed_count=0,
            output="No Python files to check.",
            metadata={"skipped": True},
        )

    finding_pool = findings or _scan_algorithm_security_findings(
        paths, max_loop_depth
    )
    algorithm_findings = [
        item for item in finding_pool if item.rule_id.startswith("ALG")
    ]
    return _build_gate_result("algorithm-gate", algorithm_findings)


def check_security_gate(
    paths: Sequence[str],
    max_loop_depth: int,
    findings: list[GateFinding] | None = None,
) -> LintResult:
    """Run secure-code generation guardrails (injection/crypto/deserialization)."""
    files = _iter_python_files(paths)
    if not files:
        return LintResult(
            tool="security-gate",
            passed=True,
            error_count=0,
            fixed_count=0,
            output="No Python files to check.",
            metadata={"skipped": True},
        )

    finding_pool = findings or _scan_algorithm_security_findings(
        paths, max_loop_depth
    )
    security_findings = [
        item for item in finding_pool if item.rule_id.startswith("SEC")
    ]
    return _build_gate_result("security-gate", security_findings)


def check_mypy(paths: Sequence[str] | None = None) -> LintResult:
    """Run mypy across src, tests, scripts and .agent (CI-aligned)."""
    targets = ["src", "tests", "scripts", ".agent"]
    cmd = _python_module_cmd("mypy", *targets)
    code, stdout, stderr = run_command(cmd)

    output = stdout or stderr
    error_count = sum(1 for line in output.splitlines() if ": error:" in line)
    return LintResult(
        tool="mypy",
        passed=code == 0,
        error_count=error_count,
        fixed_count=0,
        output=output,
    )


def check_ruff(paths: Sequence[str], ruff_args: Sequence[str]) -> LintResult:
    """Executa Ruff check sem modificar arquivos."""
    if not paths:
        return LintResult(
            tool="ruff-check",
            passed=True,
            error_count=0,
            fixed_count=0,
            output="No Python files to check.",
            metadata={"skipped": True},
        )

    cmd = _python_module_cmd(
        "ruff", "check", "--output-format=json", *ruff_args, *paths
    )
    code, stdout, stderr = run_command(cmd)

    try:
        issues = json.loads(stdout) if stdout else []
        error_count = len(issues)
        metadata: dict[str, object]
        metadata = _summarize_ruff_issues(issues)
    except json.JSONDecodeError:
        error_count = stdout.count("\n") if stdout else 0
        metadata = {"parse_error": True}

    return LintResult(
        tool="ruff-check",
        passed=error_count == 0,
        error_count=error_count,
        fixed_count=0,
        output=stdout or stderr,
        metadata=metadata,
    )


def check_format(paths: Sequence[str]) -> LintResult:
    """Verifica formatação com Ruff format."""
    if not paths:
        return LintResult(
            tool="ruff-format",
            passed=True,
            error_count=0,
            fixed_count=0,
            output="No Python files to check.",
            metadata={"skipped": True},
        )

    cmd = _python_module_cmd("ruff", "format", "--check", *paths)
    code, stdout, stderr = run_command(cmd)

    # Conta arquivos que precisam de formatação
    lines = (stdout + stderr).strip().split("\n")
    files_needing_format = [
        line
        for line in lines
        if line.strip() and "would reformat" in line.lower()
    ]

    return LintResult(
        tool="ruff-format",
        passed=len(files_needing_format) == 0,
        error_count=len(files_needing_format),
        fixed_count=0,
        output=stdout or stderr,
    )


def fix_lint(
    paths: Sequence[str], ruff_args: Sequence[str], unsafe: bool
) -> LintResult:
    """Aplica fix automático com Ruff."""
    if not paths:
        return LintResult(
            tool="ruff-fix",
            passed=True,
            error_count=0,
            fixed_count=0,
            output="No Python files to check.",
            metadata={"skipped": True},
        )

    cmd = _python_module_cmd("ruff", "check", "--fix", *ruff_args, *paths)
    if unsafe:
        cmd.insert(4, "--unsafe-fixes")
    code, stdout, stderr = run_command(cmd)

    # Conta fixes aplicados
    output = stdout + stderr
    fixed_count = output.count("Fixed")

    return LintResult(
        tool="ruff-fix",
        passed=code == 0,
        error_count=0,
        fixed_count=fixed_count,
        output=output,
    )


def fix_format(paths: Sequence[str]) -> LintResult:
    """Aplica formatação com Ruff format."""
    if not paths:
        return LintResult(
            tool="ruff-format-fix",
            passed=True,
            error_count=0,
            fixed_count=0,
            output="No Python files to check.",
            metadata={"skipped": True},
        )

    cmd = _python_module_cmd("ruff", "format", *paths)
    _code, stdout, stderr = run_command(cmd)

    output = stdout + stderr
    reformatted = [
        line
        for line in output.strip().split("\n")
        if "reformatted" in line.lower()
    ]

    return LintResult(
        tool="ruff-format-fix",
        passed=True,
        error_count=0,
        fixed_count=len(reformatted),
        output=output,
    )


def _run_checks(
    paths: Sequence[str],
    ruff_args: Sequence[str],
    run_lint: bool,
    run_format: bool,
    parallel: bool,
) -> list[LintResult]:
    """Run read-only checks, optionally in parallel for lower latency."""
    if not parallel:
        results: list[LintResult] = []
        if run_lint:
            results.append(check_ruff(paths, ruff_args))
        if run_format:
            results.append(check_format(paths))
        return results

    task_order: list[str] = []
    futures: dict[Future[LintResult], str] = {}
    with ThreadPoolExecutor(max_workers=2) as executor:
        if run_lint:
            task_order.append("ruff-check")
            futures[executor.submit(check_ruff, paths, ruff_args)] = (
                "ruff-check"
            )
        if run_format:
            task_order.append("ruff-format")
            futures[executor.submit(check_format, paths)] = "ruff-format"

        results_by_tool: dict[str, LintResult] = {}
        for future, tool in futures.items():
            results_by_tool[tool] = future.result()

    return [results_by_tool[tool] for tool in task_order]


def generate_report(results: list[LintResult]) -> str:
    """Gera relatório de qualidade de código."""
    lines = [
        "=" * 60,
        "CODE QUALITY REPORT",
        "=" * 60,
        "",
    ]

    total_errors = 0
    total_fixed = 0

    for result in results:
        status = "✅ PASS" if result.passed else "❌ FAIL"
        lines.append(f"{result.tool}: {status}")
        lines.append(f"  Errors: {result.error_count}")
        lines.append(f"  Fixed: {result.fixed_count}")
        rule_counts = result.metadata.get("rule_counts")
        if isinstance(rule_counts, dict) and rule_counts:
            lines.append("  Top Rules:")
            for code, count in list(rule_counts.items())[:5]:
                lines.append(f"    {code}: {count}")
        file_counts = result.metadata.get("file_counts")
        if isinstance(file_counts, dict) and file_counts:
            lines.append("  Top Files:")
            for filename, count in list(file_counts.items())[:5]:
                lines.append(f"    {filename}: {count}")
        lines.append("")

        total_errors += result.error_count
        total_fixed += result.fixed_count

    lines.extend(
        [
            "-" * 60,
            f"Total Errors: {total_errors}",
            f"Total Fixed: {total_fixed}",
            "=" * 60,
        ]
    )

    return "\n".join(lines)


def main() -> int:
    """Função principal."""
    parser = argparse.ArgumentParser(
        description="Code quality automation script"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check only, don't modify files",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Fix issues automatically",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate detailed report",
    )
    parser.add_argument(
        "--paths",
        nargs="*",
        help="Specific paths or files to check",
    )
    parser.add_argument(
        "--changed",
        action="store_true",
        help="Check only git-changed Python files (staged + unstaged)",
    )
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Check only git-staged Python files",
    )
    parser.add_argument(
        "--select",
        help="Comma-separated rule codes to select",
    )
    parser.add_argument(
        "--ignore",
        help="Comma-separated rule codes to ignore",
    )
    parser.add_argument(
        "--extend-select",
        dest="extend_select",
        help="Comma-separated rule codes to extend select",
    )
    parser.add_argument(
        "--extend-ignore",
        dest="extend_ignore",
        help="Comma-separated rule codes to extend ignore",
    )
    parser.add_argument(
        "--unsafe-fixes",
        action="store_true",
        help="Allow unsafe fixes when used with --fix",
    )
    parser.add_argument(
        "--lint-only",
        action="store_true",
        help="Run only ruff check",
    )
    parser.add_argument(
        "--format-only",
        action="store_true",
        help="Run only ruff format",
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Disable parallel check mode and run tools sequentially",
    )
    parser.add_argument(
        "--algorithm-gate",
        action="store_true",
        help="Run advanced algorithm complexity guardrails",
    )
    parser.add_argument(
        "--security-gate",
        action="store_true",
        help="Run secure-code generation guardrails",
    )
    parser.add_argument(
        "--engineering-gate",
        action="store_true",
        help=(
            "Run engineering guardrails for dependency contracts, "
            "packaging metadata, and CI parity"
        ),
    )
    parser.add_argument(
        "--mypy",
        action="store_true",
        help="Run mypy type-checking over src tests scripts .agent",
    )
    parser.add_argument(
        "--max-loop-depth",
        type=int,
        default=3,
        help="Maximum allowed nested loop depth for algorithm gate",
    )

    args = parser.parse_args()

    if args.max_loop_depth < 1:
        parser.error("--max-loop-depth must be >= 1")

    results: list[LintResult] = []
    paths = _resolve_paths(args)
    ruff_args = _build_ruff_args(args)

    run_lint = not args.format_only
    run_format = not args.lint_only

    if args.fix:
        print("🔧 Applying fixes...")
        if run_lint:
            results.append(fix_lint(paths, ruff_args, args.unsafe_fixes))
        if run_format:
            results.append(fix_format(paths))
    else:
        print("🔍 Checking code quality...")
        results.extend(
            _run_checks(
                paths=paths,
                ruff_args=ruff_args,
                run_lint=run_lint,
                run_format=run_format,
                parallel=not args.sequential,
            )
        )

    if args.mypy:
        print("🔍 Running mypy...")
        results.append(check_mypy())

    if args.algorithm_gate or args.security_gate or args.engineering_gate:
        print("🛡️  Running advanced gates...")
        findings: list[GateFinding] | None = None
        if args.algorithm_gate or args.security_gate:
            findings = _scan_algorithm_security_findings(
                paths, args.max_loop_depth
            )
            if args.algorithm_gate:
                results.append(
                    check_algorithm_gate(
                        paths, args.max_loop_depth, findings=findings
                    )
                )
            if args.security_gate:
                results.append(
                    check_security_gate(
                        paths, args.max_loop_depth, findings=findings
                    )
                )
        if args.engineering_gate:
            results.append(check_engineering_gate())

    if args.report:
        report = generate_report(results)
        print(report)

        # Salva relatório
        report_path = PROJECT_ROOT / "artifacts" / "quality_report.txt"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report)
        print(f"\n📄 Report saved to: {report_path}")

    # Status final
    all_passed = all(r.passed for r in results)

    if all_passed:
        print("\n✅ All quality checks passed!")
        return 0
    else:
        print("\n❌ Some quality checks failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
