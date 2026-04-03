# Required status checks for merge

To make these gates **mandatory** for merge in public branches (`main`/`master`), configure a branch protection rule or ruleset in GitHub and mark the checks below as required:

- `Public Repo Guard (Required)`
- `Routing Regression (Required)`

## What each check enforces

### `Public Repo Guard (Required)`
Produced by `.github/workflows/public-repo-guard.yml`.

1. Forbidden path validation with explicit versioned allowlist exceptions.
2. Secret scanning via Gitleaks.
3. Detection of sensitive operational config patterns (tokens, keys, internal endpoints).

### `Routing Regression (Required)`
Produced by `.github/workflows/routing-regression.yml`.

1. Stable execution regression suite run (`.internal/tests/test_stable_execution.py`).
2. Mandatory presence/parity validation for `opencode.json` and `.opencode/opencode.json`.
3. Publishing of sanitized routing evidence artifacts (JUnit + sanitized logs) for audit trails.
