---
name: dba-governance
description: Database governance checks for SQL quality, dialect safety, and migration readiness in swarm pipelines.
---

# DBA Governance Skill

## Objective

Run deterministic DBA checks over SQL artifacts and environment settings to produce auditable findings for CI and release-gate workflows.

## Script

```bash
python .agent/skills/dba-governance/scripts/dba_audit.py --report
```

## Common Usage

```bash
python .agent/skills/dba-governance/scripts/dba_audit.py \
  --report \
  --profile ci \
  --dialect auto \
  --sql-path sql
```

```bash
python .agent/skills/dba-governance/scripts/dba_audit.py \
  --report \
  --profile release \
  --dialect postgres \
  --db-url postgresql://user:pass@host:5432/db \
  --max-critical 0 \
  --max-high 0
```

## Artifacts

- `artifacts/database/dba_audit_report.json`
- `artifacts/database/dba_findings.txt`

## Exit Codes

- `0`: no threshold breach
- `1`: threshold breach
- `2`: execution error
