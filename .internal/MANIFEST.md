# .internal/ — Interconnectivity Manifest

## Purpose

Central registry for the operational core of the agent-coding-framework:
scripts, tests, and artifacts — grouped with explicit dependency mapping.

## Directory Map

```
.internal/
├── MANIFEST.md              ← This file: dependency graph documentation
├── _registry.py             ← Programmatic path resolver & integrity checker
├── scripts/
│   ├── security_patterns.py          ← Shared patterns (imported by tests + boundary check)
│   ├── scan_sensitive_patterns.py    ← CI/local scanner (used by pre-commit + GitHub Actions)
│   ├── check-public-boundary.sh      ← Boundary gate (used by public-artifacts-guard CI)
│   └── run-autocode.sh               ← Autocode wrapper (workaround for OpenCode routing bug)
├── tests/
│   ├── test_stable_execution.py              ← Stable execution suite (38 tests, 7 classes)
│   ├── test_public_config_sanitization.py    ← Sanitized config contract tests
│   └── test_public_repo_allowlist.py         ← Allowlist governance tests
└── artifacts/
    └── codex-swarm/
        ├── run-stable-execution/     ← Conformance report + golden traces
        └── run-advanced-analysis/    ← Security analysis reports
```

## Dependency Graph

### Import Dependencies
```
.internal/scripts/security_patterns.py
  ├── imported by → .internal/tests/test_stable_execution.py
  ├── imported by → .internal/tests/test_public_config_sanitization.py
  └── imported by → .internal/scripts/check-public-boundary.sh
```

### CI/CD Pipeline Dependencies
```
.internal/scripts/scan_sensitive_patterns.py
  ├── triggered by → .pre-commit-config.yaml (local pre-commit hook)
  └── triggered by → .github/workflows/public-repo-guard.yml (CI job)

.internal/scripts/check-public-boundary.sh
  └── triggered by → .github/workflows/public-artifacts-guard.yml (CI job)

.internal/tests/test_stable_execution.py
  └── triggered by → .github/workflows/routing-regression.yml (CI job)
```

### Evidence & Artifact Dependencies
```
.internal/tests/test_stable_execution.py
  └── generates evidence → .internal/artifacts/codex-swarm/run-stable-execution/
        ├── golden-traces/config-parity.json
        ├── golden-traces/routing-validation.json
        └── golden-traces/verifier-gate.json

.internal/artifacts/codex-swarm/run-stable-execution/conformance-report.json
  ├── references evidence → scripts/run-autocode.sh
  ├── references evidence → tests/test_stable_execution.py
  └── references evidence → golden-traces/*.json
```

### Cross-Reference Dependencies
```
.internal/scripts/run-autocode.sh
  ├── pre-flight → validates opencode.json ↔ .opencode/opencode.json parity
  └── fallback reference → .internal/tests/test_stable_execution.py (line 75)

.internal/scripts/check-public-boundary.sh
  └── imports → .internal/scripts/security_patterns.py (PROHIBITED_SECRET_PATTERNS, REPO_ROOT)
```

## Execution Pipeline

```
[Pre-commit] scan_sensitive_patterns.py ──┐
                                          ├──→ [CI] public-repo-guard.yml
[Pre-flight] run-autocode.sh ─────────────┤
                                          ├──→ [CI] routing-regression.yml
[Boundary] check-public-boundary.sh ──────┤
                                          ├──→ [CI] public-artifacts-guard.yml
[Tests] test_stable_execution.py ─────────┤
  └── generates ──→ artifacts/codex-swarm/
```

## Path Resolution

All internal paths are now resolved under `.internal/`. Use `.internal/_registry.py`
for programmatic path resolution:

```python
from _internal._registry import resolve_path

script_path = resolve_path("scripts", "security_patterns.py")
test_path = resolve_path("tests", "test_stable_execution.py")
artifact_path = resolve_path("artifacts", "codex-swarm/run-stable-execution")
```

## Maintenance

When adding new scripts, tests, or artifacts:
1. Place files in the appropriate `.internal/` subdirectory
2. Update this manifest with the new dependency edges
3. Update `.internal/_registry.py` if new resolution patterns are needed
4. Run `python -m pytest .internal/tests/ -v` to verify nothing is broken
