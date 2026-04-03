# Required status checks for merge

To make this gate **mandatory** for merge in public branches (`main`/`master`), configure a branch protection rule or ruleset in GitHub and mark the check below as required:

- `Public Repo Guard (Required)`

This check is produced by `.github/workflows/public-repo-guard.yml` and enforces:

1. Forbidden path validation with explicit versioned allowlist exceptions.
2. Secret scanning via Gitleaks.
3. Detection of sensitive operational config patterns (tokens, keys, internal endpoints).
