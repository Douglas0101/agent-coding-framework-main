---
description: Full code quality audit — 5-layer PEP analysis, auto-fix, and complexity metrics
---

# Code Quality PEP Audit

// turbo-all

1. Auto-fix safe issues (formatting + imports):
```bash
python .agent/skills/code-quality-pep/scripts/autofix.py
```

2. Run the full 5-layer audit (style → types → security → complexity → dead code):
```bash
python .agent/skills/code-quality-pep/scripts/audit.py
```

**If any layer fails**, investigate individually:

3. Style only (ruff):
```bash
python -m ruff check src/ tests/ scripts/ --show-fixes
```

4. Types only (mypy):
```bash
python -m mypy src/ --ignore-missing-imports --show-error-codes
```

5. Security only (bandit):
```bash
python -m bandit -r src/ -c pyproject.toml
```

6. Complexity report:
```bash
python .agent/skills/code-quality-pep/scripts/complexity_report.py
```

7. Quick check (L1 + L2 only — for fast iteration):
```bash
python .agent/skills/code-quality-pep/scripts/audit.py --quick
```
