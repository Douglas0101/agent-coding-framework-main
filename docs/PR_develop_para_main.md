# PR — Promote `develop` to `main` after public-boundary and CI hardening

## Summary

This PR promotes `develop` to `main` after completing the governance fixes required to make the branch safe for public release and branch-protected integration.

The promotion includes:
- cleanup of live `.opencode/manifests` artifacts from the public surface;
- reinforcement of public boundary tests for sanitized manifests only;
- extension of critical routing regression coverage to `develop`;
- documentation alignment across README / AGENTS / required status checks.

## Why this PR is needed

`develop` substantially improves the repository by formalizing the project as an **Agent Coding Framework** with stable execution, config parity, routing regression coverage, and public-vs-internal repository governance. The README now documents the framework architecture, public contract surface, and stable execution guarantees. fileciteturn6file0

However, before promotion, the branch had a material contradiction:

- `.opencode/manifests/README.md` states that only **sanitized** manifests under `./sanitized/` should be versioned, and that session data, local machine paths, and transient runtime content must not be tracked. fileciteturn12file0
- `.gitignore` and the public boundary test enforce the same allowlist. fileciteturn10file0 fileciteturn11file0
- but `.opencode/manifests/latest.json` contained live session metadata such as `session_id`, local directory path, timestamps, provider, and model. fileciteturn13file0

There was also a branch policy mismatch:
- Git Flow defines `develop` as the integration branch for the next release. fileciteturn14file0
- but `Routing Regression (Required)` was configured only for `main`/`master`. fileciteturn9file0

This PR closes those gaps before merging to `main`.

## What changed

### Public boundary hardening
- removed tracked live manifests from `.opencode/manifests/`;
- preserved only the public sanitized subset and docs;
- strengthened tests to fail if non-sanitized manifest artifacts are reintroduced.

### CI / branch protection alignment
- updated routing regression coverage so `develop` receives the same critical gate expected of the integration branch;
- aligned status-check documentation with the actual protected-branch strategy.

### Documentation consistency
- cleaned up contradictory statements about test coverage and public artifact policy;
- preserved the existing stable-execution architecture and routing guarantees.

## Validation

Expected validation for this promotion:

```bash
python -m pytest .internal/tests/test_public_boundary.py -v
python -m pytest .internal/tests/test_stable_execution.py -v
```

Additionally, `Routing Regression (Required)` must pass on the merge target path.

## Risk assessment

### Low risk
- documentation alignment;
- status-check documentation updates.

### Medium risk
- CI trigger expansion to `develop` may surface existing latent failures.

### Controlled risk
- removing live manifests may affect any workflow that incorrectly depended on tracked runtime state; this is intentional and aligns the repository with its own public-boundary policy. fileciteturn12file0 fileciteturn10file0

## Merge readiness checklist

- [ ] No tracked live manifest remains under `.opencode/manifests/`
- [ ] Public boundary tests pass
- [ ] Stable execution tests pass
- [ ] Routing regression covers `develop`
- [ ] Documentation no longer contradicts the enforced governance model

## Outcome

After this PR, `main` receives the mature `develop` line with:
- stable execution guardrails preserved;
- public repository hygiene enforced;
- branch protection and CI behavior aligned with the declared Git Flow.
