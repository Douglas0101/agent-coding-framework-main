# Required status checks for merge

To make these gates **mandatory** for merge, configure a branch protection rule or ruleset in GitHub and mark the checks below as required.

## Branch coverage

| Check | `main`/`master` | `develop` |
|---|---|---|
| `Public Repo Guard (Required)` | Required | Required |
| `Routing Regression (Required)` | Required | Required |

Both checks must pass on `develop` before any PR to `main`/`master` can be merged, ensuring the integration branch is always promotion-ready.

## What each check enforces

### `Public Repo Guard (Required)`
Produced by `.github/workflows/public-repo-guard.yml`.

1. Forbidden path validation with explicit versioned allowlist exceptions.
2. Secret scanning via Gitleaks.
3. Detection of sensitive operational config patterns (tokens, keys, internal endpoints).

### `Routing Regression (Required)`
Produced by `.github/workflows/routing-regression.yml`.

1. Stable execution regression suite run (`.internal/tests/test_stable_execution.py`).
2. Public boundary validation (`.internal/tests/test_public_boundary.py`).
3. Mandatory presence/parity validation for `opencode.json` and `.opencode/opencode.json`.
4. Publishing of sanitized routing evidence artifacts (JUnit + sanitized logs) for audit trails.
