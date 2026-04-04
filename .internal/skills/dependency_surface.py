"""
Skill: dependency_surface (explore mode)

Analyzes repository dependency surface: import graphs, coupling metrics,
circular dependencies, external package surface, and change blast radius.
Produces a structured dependency report for impact analysis.
"""

from __future__ import annotations

import json
import re
import hashlib
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INTERNAL_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = INTERNAL_DIR.parent

PYTHON_STDLIB = {
    "os",
    "sys",
    "json",
    "re",
    "hashlib",
    "datetime",
    "pathlib",
    "typing",
    "dataclasses",
    "enum",
    "collections",
    "itertools",
    "functools",
    "abc",
    "io",
    "copy",
    "math",
    "statistics",
    "logging",
    "unittest",
    "argparse",
    "subprocess",
    "shutil",
    "tempfile",
    "textwrap",
    "string",
    "struct",
    "time",
    "traceback",
    "warnings",
    "contextlib",
    "importlib",
    "inspect",
    "dis",
    "ast",
    "token",
    "tokenize",
    "pickle",
    "csv",
    "configparser",
    "tomllib",
    "xml",
    "html",
    "http",
    "urllib",
    "email",
    "socket",
    "ssl",
    "select",
    "threading",
    "multiprocessing",
    "concurrent",
    "asyncio",
    "queue",
    "heapq",
    "bisect",
    "array",
    "weakref",
    "types",
    "pprint",
    "reprlib",
    "numbers",
    "decimal",
    "fractions",
    "random",
    "operator",
    "posixpath",
    "ntpath",
    "genericpath",
    "stat",
    "fileinput",
    "filecmp",
    "linecache",
    "codecs",
    "unicodedata",
    "locale",
    "gettext",
}


@dataclass
class DependencyNode:
    """Single module/package in the dependency graph."""

    name: str
    node_type: str  # internal, external, stdlib
    import_count: int = 0
    imported_by: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    is_circular: bool = False


@dataclass
class CouplingMetrics:
    """Coupling metrics between modules."""

    afferent_coupling: int = 0  # Ca: modules that depend on this
    efferent_coupling: int = 0  # Ce: modules this depends on
    instability: float = 0.0  # I = Ce / (Ca + Ce)


@dataclass
class CircularDependency:
    """Detected circular dependency chain."""

    chain: list[str]
    severity: str  # critical, high, medium


@dataclass
class ExternalDependency:
    """External package dependency."""

    name: str
    imported_by: list[str] = field(default_factory=list)
    import_locations: list[str] = field(default_factory=list)
    risk_level: str = "low"  # critical, high, medium, low


@dataclass
class DependencySurfaceReport:
    run_id: str
    timestamp: str
    total_nodes: int = 0
    internal_deps: int = 0
    external_deps: int = 0
    stdlib_deps: int = 0
    circular_dependencies: list[CircularDependency] = field(default_factory=list)
    coupling: dict[str, CouplingMetrics] = field(default_factory=dict)
    nodes: list[DependencyNode] = field(default_factory=list)
    external_packages: list[ExternalDependency] = field(default_factory=list)
    blast_radius: dict[str, list[str]] = field(default_factory=dict)
    integrity_hash: str = ""

    @property
    def has_critical_issues(self) -> bool:
        return any(d.severity == "critical" for d in self.circular_dependencies)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "total_nodes": self.total_nodes,
            "internal_deps": self.internal_deps,
            "external_deps": self.external_deps,
            "stdlib_deps": self.stdlib_deps,
            "circular_dependencies": [asdict(d) for d in self.circular_dependencies],
            "coupling": {k: asdict(v) for k, v in self.coupling.items()},
            "nodes": [asdict(n) for n in self.nodes],
            "external_packages": [asdict(p) for p in self.external_packages],
            "blast_radius": self.blast_radius,
            "has_critical_issues": self.has_critical_issues,
            "integrity_hash": self.integrity_hash,
        }


class DependencySurfaceAnalyzer:
    """Analyzes dependency surface and produces structured reports."""

    def __init__(self, run_id: str | None = None, root: Path | None = None) -> None:
        self.run_id = (
            run_id or f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        )
        self.root = root or PROJECT_ROOT
        self._nodes: dict[str, DependencyNode] = {}
        self._external: dict[str, ExternalDependency] = {}
        self._circular: list[CircularDependency] = []
        self._coupling: dict[str, CouplingMetrics] = {}
        self._blast_radius: dict[str, list[str]] = {}

    def analyze(self, max_depth: int = 5) -> DependencySurfaceReport:
        self._scan_python_imports()
        self._scan_yaml_references()
        self._detect_circular_dependencies()
        self._compute_coupling_metrics()
        self._compute_blast_radius()
        self._classify_external_risk()

        internal_count = sum(
            1 for n in self._nodes.values() if n.node_type == "internal"
        )
        external_count = len(self._external)
        stdlib_count = sum(1 for n in self._nodes.values() if n.node_type == "stdlib")

        report = DependencySurfaceReport(
            run_id=self.run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_nodes=len(self._nodes) + external_count,
            internal_deps=internal_count,
            external_deps=external_count,
            stdlib_deps=stdlib_count,
            circular_dependencies=self._circular,
            coupling=self._coupling,
            nodes=list(self._nodes.values()),
            external_packages=list(self._external.values()),
            blast_radius=self._blast_radius,
        )
        report.integrity_hash = self._compute_hash(report)
        return report

    def _scan_python_imports(self) -> None:
        for py_file in self.root.rglob("*.py"):
            rel_path = str(py_file.relative_to(self.root))
            if self._is_ignored(rel_path):
                continue

            try:
                content = py_file.read_text(encoding="utf-8", errors="replace")
            except (PermissionError, UnicodeDecodeError):
                continue

            module_name = rel_path.replace("/", ".").replace(".py", "")

            for line in content.splitlines():
                stripped = line.strip()
                if not (stripped.startswith("from ") or stripped.startswith("import ")):
                    continue

                imports = self._parse_import_line(stripped)
                for imp in imports:
                    self._register_import(module_name, imp)

    def _parse_import_line(self, line: str) -> list[str]:
        imports: list[str] = []
        line = line.split("#")[0].strip()

        if line.startswith("from "):
            parts = line.split()
            if len(parts) >= 2:
                module = parts[1]
                imports.append(module.split(".")[0])
        elif line.startswith("import "):
            parts = line.split()
            for part in parts[1:]:
                part = part.rstrip(",")
                if part and part != "as":
                    imports.append(part.split(".")[0])

        return imports

    def _register_import(self, source: str, target: str) -> None:
        if target in PYTHON_STDLIB:
            if target not in self._nodes:
                self._nodes[target] = DependencyNode(name=target, node_type="stdlib")
            self._nodes[target].import_count += 1
            return

        is_internal = self._is_internal_module(target)

        if is_internal:
            if target not in self._nodes:
                self._nodes[target] = DependencyNode(name=target, node_type="internal")
            self._nodes[target].import_count += 1
            if source not in self._nodes[target].imported_by:
                self._nodes[target].imported_by.append(source)

            if source not in self._nodes:
                self._nodes[source] = DependencyNode(name=source, node_type="internal")
            if target not in self._nodes[source].imports:
                self._nodes[source].imports.append(target)
        else:
            if target not in self._external:
                self._external[target] = ExternalDependency(name=target)
            if source not in self._external[target].imported_by:
                self._external[target].imported_by.append(source)

    def _is_internal_module(self, name: str) -> bool:
        internal_paths = [
            self.root / ".internal",
            self.root / "src",
            self.root / "lib",
        ]
        for base in internal_paths:
            if base.exists():
                candidate = base / name
                if candidate.exists() or (base / f"{name}.py").exists():
                    return True
        return False

    def _scan_yaml_references(self) -> None:
        for yaml_file in self.root.rglob("*.yaml"):
            rel_path = str(yaml_file.relative_to(self.root))
            if self._is_ignored(rel_path):
                continue
            try:
                content = yaml_file.read_text(encoding="utf-8", errors="replace")
            except (PermissionError, UnicodeDecodeError):
                continue

            if "parent_contract:" in content:
                for line in content.splitlines():
                    if "parent_contract:" in line:
                        ref = line.split(":", 1)[1].strip().strip('"').strip("'")
                        if ref:
                            if ref not in self._nodes:
                                self._nodes[ref] = DependencyNode(
                                    name=ref, node_type="internal"
                                )
                            self._nodes[ref].import_count += 1

    def _detect_circular_dependencies(self) -> None:
        visited: set[str] = set()
        rec_stack: set[str] = set()
        path: list[str] = []

        def dfs(node: str) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            node_obj = self._nodes.get(node)
            if node_obj:
                for neighbor in node_obj.imports:
                    if neighbor not in self._nodes:
                        continue
                    if neighbor not in visited:
                        dfs(neighbor)
                    elif neighbor in rec_stack:
                        cycle_start = path.index(neighbor)
                        cycle = path[cycle_start:] + [neighbor]
                        severity = self._circular_severity(cycle)
                        self._circular.append(
                            CircularDependency(chain=cycle, severity=severity)
                        )
                        for n in cycle[:-1]:
                            if n in self._nodes:
                                self._nodes[n].is_circular = True

            path.pop()
            rec_stack.discard(node)

        for node in list(self._nodes.keys()):
            if node not in visited:
                dfs(node)

    def _circular_severity(self, cycle: list[str]) -> str:
        length = len(cycle) - 1
        if length == 1:
            return "critical"
        if length == 2:
            return "high"
        if length <= 4:
            return "medium"
        return "low"

    def _compute_coupling_metrics(self) -> None:
        for name, node in self._nodes.items():
            ca = len(node.imported_by)
            ce = len(node.imports)
            total = ca + ce
            instability = ce / total if total > 0 else 0.0
            self._coupling[name] = CouplingMetrics(
                afferent_coupling=ca,
                efferent_coupling=ce,
                instability=round(instability, 3),
            )

    def _compute_blast_radius(self) -> None:
        for name, node in self._nodes.items():
            affected: set[str] = set()
            queue = list(node.imported_by)
            while queue:
                current = queue.pop(0)
                if current not in affected:
                    affected.add(current)
                    if current in self._nodes:
                        queue.extend(self._nodes[current].imported_by)
            self._blast_radius[name] = sorted(affected)

    def _classify_external_risk(self) -> None:
        for name, ext in self._external.items():
            num_dependents = len(ext.imported_by)
            if num_dependents >= 10:
                ext.risk_level = "critical"
            elif num_dependents >= 5:
                ext.risk_level = "high"
            elif num_dependents >= 3:
                ext.risk_level = "medium"
            else:
                ext.risk_level = "low"

    def _is_ignored(self, rel_path: str) -> bool:
        ignored = [
            ".git/",
            "__pycache__/",
            ".pytest_cache/",
            ".mypy_cache/",
            ".ruff_cache/",
            "node_modules/",
            ".venv/",
            "venv/",
            ".internal/artifacts/",
            "downloads/",
        ]
        return any(rel_path.startswith(ign) for ign in ignored)

    def _compute_hash(self, report: DependencySurfaceReport) -> str:
        content = json.dumps(
            {
                "total_nodes": report.total_nodes,
                "internal_deps": report.internal_deps,
                "external_deps": report.external_deps,
                "circular_count": len(report.circular_dependencies),
            },
            sort_keys=True,
            default=str,
        )
        return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"


def analyze_dependency_surface(
    run_id: str | None = None, max_depth: int = 5
) -> dict[str, Any]:
    analyzer = DependencySurfaceAnalyzer(run_id=run_id)
    report = analyzer.analyze(max_depth=max_depth)
    return report.to_dict()


if __name__ == "__main__":
    import sys

    run_id = sys.argv[1] if len(sys.argv) > 1 else None
    result = analyze_dependency_surface(run_id=run_id)

    status = "CRITICAL ISSUES" if result["has_critical_issues"] else "OK"
    print(f"[{status}] Dependency surface: {result['run_id']}")
    print(f"  Total nodes: {result['total_nodes']}")
    print(f"  Internal: {result['internal_deps']}")
    print(f"  External: {result['external_deps']}")
    print(f"  Stdlib: {result['stdlib_deps']}")
    print(f"  Circular dependencies: {len(result['circular_dependencies'])}")

    for cd in result["circular_dependencies"]:
        print(f"    [{cd['severity'].upper()}] {' -> '.join(cd['chain'])}")

    print(f"  External packages:")
    for pkg in sorted(result["external_packages"], key=lambda x: x["name"]):
        print(
            f"    {pkg['name']} ({pkg['risk_level']}) -> {len(pkg['imported_by'])} files"
        )
