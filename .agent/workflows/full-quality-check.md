---
description: Full quality gate — tests, linting, and type checking in sequence
---

# Full Quality Check

// turbo-all

1. Run auto-fix (safe formatting + imports):
```bash
python .agent/skills/code-quality-pep/scripts/autofix.py
```

2. Run the 5-layer PEP audit:
```bash
python .agent/skills/code-quality-pep/scripts/audit.py
```

3. Run engineering governance gate (deps + packaging + CI parity):
```bash
python .agent/skills/code-quality/scripts/lint_fix.py \
  --check \
  --paths src \
  --algorithm-gate \
  --security-gate \
  --engineering-gate \
  --report
```

4. Run the ITCH pipeline environment validator:
```bash
python .agent/skills/itch-pipeline/scripts/validate_env.py
```

5. Run the ITCH quality gate (pytest → coverage → ruff → mypy):
```bash
bash .agent/skills/itch-pipeline/scripts/quality_gate.sh
```

**If any stage fails**, diagnose with individual commands:

6. Tests only:
```bash
python -m pytest tests/ -v --tb=long
```

7. Lint only:
```bash
python -m ruff check src/ tests/ scripts/ --show-fixes
```

8. Type check only:
```bash
python -m mypy src/ --ignore-missing-imports --show-error-codes
```

9. Complexity check:
```bash
python .agent/skills/code-quality-pep/scripts/complexity_report.py
```
