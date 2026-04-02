---
name: backend-reliability
description: FastAPI reliability checks for route contracts, auth guardrails, and OpenAPI drift detection.
---

# Backend Reliability Skill

## Objective

Validate backend API reliability requirements for governance pipelines: import integrity, route-level auth posture, response contracts, and OpenAPI drift.

## Script

```bash
python .agent/skills/backend-reliability/scripts/backend_reliability_check.py --report
```

## Common Usage

```bash
python .agent/skills/backend-reliability/scripts/backend_reliability_check.py \
  --report \
  --app-module src.api.main:app \
  --app-module src.serving.api:app
```

```bash
python .agent/skills/backend-reliability/scripts/backend_reliability_check.py \
  --report \
  --max-critical 0 \
  --max-high 0 \
  --require-auth
```

## Artifacts

- `artifacts/backend/backend_reliability_report.json`
- `artifacts/backend/openapi_snapshot.json`

## Exit Codes

- `0`: no threshold breach
- `1`: threshold breach
- `2`: execution error
