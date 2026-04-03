# Native Swarm Rules

- Use MCP only for context that lives outside the repository or changes frequently.
- Check `/mcp` before starting a multi-agent swarm run and stop if a required server is missing.
- Use `docs_researcher` for version-sensitive facts or official external documentation lookups.
- Treat the workflow as artifact-first: worker outputs belong under `artifacts/codex-swarm/<run-id>/`.
- Keep `write_scope` disjoint across parallel workers.
- `verifier` is the mandatory gate before `synthesizer`.
- `synthesizer` is the single final writer for the run package.
- When live session state matters, pass a `--session-snapshot` JSON file to `scripts/codex_swarm_prepare.py` so the run manifest records the effective overrides.

## Known Issues

### Routing Bug: `/autocode` command (OpenCode v1.3.13)

**Problem:** The `/autocode` command (defined in `.opencode/commands/autocode.md` with `agent: autocoder` in frontmatter) is NOT routed to the `autocoder` agent at runtime. Instead, it falls back to the `general` agent with `maxSteps: 50` (expected: `autocoder` with `maxSteps: 6`).

**Confirmed:** Bug persists with `--pure` flag (no plugins), confirming it is a runtime routing issue, not a plugin issue. Other commands with `agent:` in frontmatter work correctly (`/ship` → orchestrator, `/review` → reviewer, `/analyze` → explore).

**Workaround:** Use `--agent autocoder` flag explicitly:
```bash
opencode run --agent autocoder --command autocode "your task"
# Or use the wrapper script:
./scripts/run-autocode.sh "your task"
```

**Tracking:** Root cause appears to be silent config merge failure when `.opencode/opencode.json` does not exist. See `.opencode/skills/self-bootstrap-opencode/debug_autocode.log` for DEBUG evidence.
