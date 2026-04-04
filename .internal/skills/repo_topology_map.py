"""
Skill: repo_topology_map (explore mode)

Maps repository structure, identifies module boundaries, dependency chains,
and produces a structured topology report.
"""

from __future__ import annotations

import json
import os
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INTERNAL_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = INTERNAL_DIR.parent  # .internal's parent is the project root


@dataclass
class ModuleInfo:
    path: str
    module_type: str  # core, runtime, test, config, doc, domain_pack, skill
    file_count: int = 0
    has_init: bool = False
    dependencies: list[str] = field(default_factory=list)


@dataclass
class TopologyReport:
    run_id: str
    timestamp: str
    root: str
    modules: list[ModuleInfo] = field(default_factory=list)
    total_files: int = 0
    total_dirs: int = 0
    dependency_graph: dict[str, list[str]] = field(default_factory=dict)
    integrity_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "root": self.root,
            "total_files": self.total_files,
            "total_dirs": self.total_dirs,
            "modules": [asdict(m) for m in self.modules],
            "dependency_graph": self.dependency_graph,
            "integrity_hash": self.integrity_hash,
        }


MODULE_CLASSIFICATION = {
    ".internal/specs": "core",
    ".internal/runtime": "runtime",
    ".internal/tests": "test",
    ".internal/skills": "skill",
    ".internal/domains": "domain_pack",
    ".internal/adr": "doc",
    ".internal/scripts": "runtime",
    "docs": "doc",
    ".github": "config",
}

CODE_EXTENSIONS = {".py", ".yaml", ".yml", ".json", ".toml", ".cfg"}


class RepoTopologyMapper:
    """Maps repository structure and produces topology reports."""

    def __init__(self, run_id: str | None = None, root: Path | None = None) -> None:
        self.run_id = (
            run_id or f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        )
        self.root = root or PROJECT_ROOT

    def map(self, max_depth: int = 4) -> TopologyReport:
        modules: dict[str, ModuleInfo] = {}
        total_files = 0
        total_dirs = 0
        dependency_graph: dict[str, list[str]] = {}

        ignore_dirs = {
            ".git",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            "node_modules",
            ".venv",
            "venv",
            "downloads",
            ".idea",
        }

        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in ignore_dirs]

            rel_dir = str(Path(dirpath).relative_to(self.root))
            if rel_dir != "." and not self._is_ignored(rel_dir + "/"):
                total_dirs += 1
                if rel_dir not in modules:
                    parent_type = self._classify_module(rel_dir + "/")
                    modules[rel_dir] = ModuleInfo(path=rel_dir, module_type=parent_type)

            for fname in filenames:
                full_path = Path(dirpath) / fname
                rel = str(full_path.relative_to(self.root))
                if self._is_ignored(rel):
                    continue
                if full_path.suffix not in CODE_EXTENSIONS:
                    continue

                total_files += 1
                parent_dir = str(full_path.parent.relative_to(self.root))

                if parent_dir not in modules:
                    parent_type = self._classify_module(parent_dir + "/")
                    modules[parent_dir] = ModuleInfo(
                        path=parent_dir,
                        module_type=parent_type,
                    )
                modules[parent_dir].file_count += 1
                if fname == "__init__.py":
                    modules[parent_dir].has_init = True

                deps = self._extract_dependencies(full_path, rel)
                if deps:
                    dependency_graph[rel] = deps

        for path in self.root.iterdir():
            if path.is_dir() and not self._is_ignored(str(path.relative_to(self.root))):
                total_dirs += 1

        report = TopologyReport(
            run_id=self.run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            root=str(self.root),
            modules=list(modules.values()),
            total_files=total_files,
            total_dirs=total_dirs,
            dependency_graph=dependency_graph,
        )
        report.integrity_hash = self._compute_hash(report)
        return report

    def _classify_module(self, rel_path: str) -> str:
        for prefix, module_type in MODULE_CLASSIFICATION.items():
            if rel_path.startswith(prefix):
                return module_type
        return "other"

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

    def _extract_dependencies(self, file_path: Path, rel_path: str) -> list[str]:
        deps: list[str] = []
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except (PermissionError, UnicodeDecodeError):
            return deps

        if file_path.suffix == ".py":
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("from ") or stripped.startswith("import "):
                    parts = stripped.split()
                    if len(parts) >= 2:
                        mod = parts[1].split(".")[0]
                        if mod and mod not in (
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
                        ):
                            deps.append(mod)

        elif file_path.suffix in (".yaml", ".yml"):
            if "parent_contract:" in content:
                for line in content.splitlines():
                    if "parent_contract:" in line:
                        ref = line.split(":", 1)[1].strip().strip('"').strip("'")
                        if ref:
                            deps.append(ref)

        return deps[:20]

    def _compute_hash(self, report: TopologyReport) -> str:
        content = json.dumps(
            {
                "root": report.root,
                "total_files": report.total_files,
                "total_dirs": report.total_dirs,
                "modules": [asdict(m) for m in report.modules],
            },
            sort_keys=True,
            default=str,
        )
        return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"


def map_topology(run_id: str | None = None, max_depth: int = 4) -> dict[str, Any]:
    mapper = RepoTopologyMapper(run_id=run_id)
    report = mapper.map(max_depth=max_depth)
    return report.to_dict()


if __name__ == "__main__":
    import sys

    run_id = sys.argv[1] if len(sys.argv) > 1 else None
    result = map_topology(run_id=run_id)

    print(f"[OK] Topology map: {result['run_id']}")
    print(f"  Root: {result['root']}")
    print(f"  Total files: {result['total_files']}")
    print(f"  Total dirs: {result['total_dirs']}")
    print(f"  Modules: {len(result['modules'])}")
    print(f"  Dependencies tracked: {len(result['dependency_graph'])}")

    for mod in result["modules"][:10]:
        print(
            f"    {mod['module_type']:15s} {mod['path']:40s} ({mod['file_count']} files)"
        )
