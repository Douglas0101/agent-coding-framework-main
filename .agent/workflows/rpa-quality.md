---
description: Run the RPA Supervisor — supervised code quality scan, fix, and verify loop
---

# RPA Quality Supervisor

// turbo-all

1. Run the RPA Supervisor in **scan-only** mode (detect issues without fixing):
```bash
python .agent/skills/code-quality-pep/scripts/rpa_supervisor.py
```

Alternative (swarm orchestrator, goal-driven):
```bash
python scripts/rpa_swarm.py --goal ci-stabilize --profile ci --fail-fast
```

2. Run with **auto-fix** enabled (scan → fix → verify → report, up to 3 iterations):
```bash
python .agent/skills/code-quality-pep/scripts/rpa_supervisor.py --fix
```

**If fixes introduce test failures**, investigate:

3. Run with fix but skip tests (useful for fast iteration):
```bash
python .agent/skills/code-quality-pep/scripts/rpa_supervisor.py --fix --skip-tests
```

4. Full JSON output for CI/CD:
```bash
python .agent/skills/code-quality-pep/scripts/rpa_supervisor.py --fix --json
```

5. Run the existing 5-layer audit to confirm compatibility:
```bash
python .agent/skills/code-quality-pep/scripts/audit.py
```

6. Run complexity report to find refactoring targets:
```bash
python .agent/skills/code-quality-pep/scripts/complexity_report.py
```
