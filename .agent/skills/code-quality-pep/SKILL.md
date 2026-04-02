---
name: code-quality-pep
description: Python code quality enforcement — PEP 8/20/257/484 compliance, 6-layer analysis with RPA Supervisor, auto-fixing, and complexity metrics
---

# Code Quality PEP Engineering — Agent Skill

> **Purpose**: Enforce Python code quality standards across the entire project using a unified 6-layer analysis pyramid backed by 12+ specialized tools, orchestrated by a supervised RPA loop.

---

## 1. Tool Stack

| Tool | Layer | Coverage | Config Source |
|------|-------|----------|---------------|
| **AST analyzers** | Logic + Structure + Syntax | Mutable defaults, bare except, unreachable code | Custom scripts |
| **ruff** | Style + Imports | PEP 8, PEP 585/604 | `pyproject.toml` `[tool.ruff]` |
| **mypy** | Types | PEP 484/526/544/585/604 | `pyproject.toml` `[tool.mypy]` |
| **basedpyright (LSP)** | Types + IDE | Real-time diagnostics and strict type checks | `pyrightconfig.json` |
| **bandit** | Security | OWASP Top 10, CWE | `pyproject.toml` `[tool.bandit]` |
| **radon** | Complexity | PEP 20 (Zen of Python) | CLI flags |
| **vulture** | Dead code | — | CLI flags |
| **pytest-cov** | Coverage | ≥ 60% | `pyproject.toml` `[tool.coverage]` |

**Superseded** (handled by ruff): flake8, pycodestyle, isort, pydocstyle, pylint.

---

## 2. Six-Layer Analysis Pyramid

```
               ┌──────────────┐
         L5    │  Dead Code   │  vulture
               ├──────────────┤
         L4    │  Complexity  │  radon CC ≤ 10, MI ≥ 20
               ├──────────────┤
         L3    │   Security   │  bandit (S rules)
               ├──────────────┤
         L2    │    Types     │  mypy strict + basedpyright
               ├──────────────┤
         L1    │    Style     │  ruff (E/W/F/I/N/UP/B/C4/SIM)
               ├──────────────┤
         L0    │ Logic+Struct │  AST analyzers (RPA-Exx/Wxx)
               └──────────────┘
```

Each layer builds on the one below — fix L0 before L1, L1 before L2, etc.

---

## 3. L0 — AST Deep Analysis (NEW)

| Code | Check | Severity |
|------|-------|----------|
| RPA-E001 | Bare `except:` | error |
| RPA-E002 | `is`/`is not` with literal | error |
| RPA-E003 | Assert on non-empty tuple | error |
| RPA-E004 | Unreachable code after return/raise | error |
| RPA-E005 | Mutable default argument | error |
| RPA-W001 | f-string without placeholders | warning |
| RPA-W002 | Assignment shadows builtin | warning |
| RPA-W003 | `global` in nested scope | warning |
| RPA-W004 | Deeply nested try/except (> 2) | warning |
| RPA-W005 | Missing else return branch | warning |
| RPA-W006 | Parameter shadows builtin | warning |
| RPA-D001 | Star import (`from x import *`) | error |
| RPA-D002 | Inconsistent dict return keys | warning |
| RPA-D003 | Mixed None/concrete returns | warning |
| RPA-D004 | `__all__` exports undefined names | error |
| RPA-E006 | `list.pop(0)` overhead (use deque) | error |
| RPA-S001 | py_compile failure | error |
| RPA-S003 | Mixed tabs/spaces | error |
| RPA-S005 | Invalid escape sequence | warning |
| RPA-W007 | `except Exception` without raise/log | warning |
| RPA-W008 | Redundant container recreation in loop | warning |

---

## 4. RPA Supervisor — Supervised Loop

```
┌──────────────────────────────────────────┐
│      RPA SUPERVISOR (max 3 iterations)    │
├──────────────────────────────────────────┤
│  Phase 1: PRE-FLIGHT                     │
│  Phase 2: DEEP SCAN (L0–L5)             │
│  Phase 3: SUPERVISED FIX                 │
│  Phase 4: VERIFICATION (rescan + pytest) │
│  Phase 5: REPORT (deltas + diffs)        │
│  ↻ Loop until converged or max reached   │
└──────────────────────────────────────────┘
```

---

## 5. Decision Matrix — When to Use What

| Scenario | Command |
|----------|---------|
| Quick pre-commit check | `python audit.py --quick` (L1 + L2 only) |
| Full analysis | `python audit.py` |
| **Supervised scan + fix** | `python rpa_supervisor.py --fix` |
| **Scan only (no fix)** | `python rpa_supervisor.py` |
| Auto-fix everything safe | `python autofix.py` |
| Preview fixes only | `python autofix.py --dry-run` |
| Find complex functions | `python complexity_report.py` |
| CI/CD gate | `python rpa_supervisor.py --json --fix` |

---

## 6. Fix Priority (Triage Order)

1. **🔴 Critical**: Syntax errors (L0 RPA-S), Security (L3 bandit HIGH)
2. **🟠 High**: Logic errors (L0 RPA-E), Type errors (L2 mypy)
3. **🟡 Medium**: Style violations (L1 ruff E/W) — auto-fix with `autofix.py`
4. **🔵 Low**: Complexity (L4 CC > 10) — refactor when touching the file
5. **⚪ Info**: Dead code (L5 vulture), Structure warnings (L0 RPA-W/D)

---

## 7. Script Reference

| Script | Purpose | Key Flags |
|--------|---------|-----------|
| `rpa_supervisor.py` | 5-phase supervised loop | `--fix`, `--max-iterations N`, `--json`, `--skip-tests` |
| `audit.py` | 5-layer quality scan | `--quick`, `--json`, `--strict`, `--layer N` |
| `autofix.py` | Safe auto-fix chain | `--dry-run`, `--format-only` |
| `complexity_report.py` | CC + MI metrics | `--threshold N`, `--json` |

All scripts located in `.agent/skills/code-quality-pep/scripts/`.

### Sub-modules

| Module | Purpose |
|--------|---------|
| `analyzers/ast_logic_analyzer.py` | AST-based logic error detection |
| `analyzers/data_structure_checker.py` | Type/structure consistency checks |
| `analyzers/syntax_validator.py` | Compile + tokenization validation |
| `fixers/logic_fixer.py` | Auto-fix for logic errors |
| `fixers/safe_transforms.py` | Transactional file transform utilities |

---

## 8. Common Workflows

```bash
# Full supervised scan + fix (recommended)
python .agent/skills/code-quality-pep/scripts/rpa_supervisor.py --fix

# Scan-only (no changes)
python .agent/skills/code-quality-pep/scripts/rpa_supervisor.py

# Quick daily check
python .agent/skills/code-quality-pep/scripts/audit.py --quick

# Auto-fix then audit
python .agent/skills/code-quality-pep/scripts/autofix.py
python .agent/skills/code-quality-pep/scripts/audit.py

# Find refactoring targets
python .agent/skills/code-quality-pep/scripts/complexity_report.py
```

---

## 9. PEP Standards Covered

| PEP | Title | Enforced By |
|-----|-------|-------------|
| PEP 8 | Style Guide | ruff E/W/N, line-length=79 |
| PEP 20 | Zen of Python | radon MI ≥ 20, ruff SIM |
| PEP 257 | Docstring Conventions | ruff D (opt-in) |
| PEP 484 | Type Hints | mypy strict |
| PEP 526 | Variable Annotations | mypy |
| PEP 544 | Protocols | mypy |
| PEP 585 | Generic Types | ruff UP |
| PEP 604 | Union `X \| Y` | ruff UP |
