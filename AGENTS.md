# Native Swarm Rules

- Use MCP only for context that lives outside the repository or changes frequently.
- Check `/mcp` before starting a multi-agent swarm run and stop if a required server is missing.
- Use `docs_researcher` for version-sensitive facts or official external documentation lookups.
- Treat the workflow as artifact-first: worker outputs belong under `artifacts/codex-swarm/<run-id>/`.
- Keep `write_scope` disjoint across parallel workers.
- `verifier` is the mandatory gate before `synthesizer`.
- `synthesizer` is the single final writer for the run package.
- When live session state matters, pass a `--session-snapshot` JSON file to `scripts/codex_swarm_prepare.py` so the run manifest records the effective overrides.
