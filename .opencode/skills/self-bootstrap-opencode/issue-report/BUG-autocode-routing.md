# Bug: `agent:` frontmatter field in commands is not respected at runtime for `autocoder` agent

## Environment
- **OpenCode version:** 1.3.13
- **OS:** Linux
- **Runtime:** `opencode run --command`

## Expected Behavior
When a command file (e.g., `.opencode/commands/autocode.md`) declares `agent: autocoder` in its YAML frontmatter, the runtime should route execution to the `autocoder` agent (configured with `maxSteps: 6` in `opencode.json`).

## Actual Behavior
The `/autocode` command is routed to the `general` agent with `maxSteps: 50` instead of `autocoder` with `maxSteps: 6`.

## Reproduction

### Minimal Setup
```
project/
├── opencode.json          # contains: "default_agent": "autocoder", "agent": { "autocoder": { "maxSteps": 6 } }
└── .opencode/
    └── commands/
        └── autocode.md    # frontmatter: agent: autocoder
```

### Commands
```bash
# BUG: Routes to general (maxSteps=50) instead of autocoder (maxSteps=6)
opencode run --command autocode "Diga qual agente voce e." --format json

# WORKS: Routes to autocoder correctly
opencode run --agent autocoder "Diga qual agente voce e." --format json

# WORKS: Other commands with agent: frontmatter route correctly
opencode run --command ship "..."        # → orchestrator (maxSteps=5) ✅
opencode run --command review "..."      # → reviewer (maxSteps=2) ✅
opencode run --command analyze "..."     # → explore (maxSteps=4) ✅
```

### Affected Commands
| Command | Frontmatter `agent:` | Expected Agent | Actual Agent | Status |
|---------|---------------------|----------------|--------------|--------|
| `/autocode` | `autocoder` | autocoder (maxSteps=6) | **general** (maxSteps=50) | ❌ |
| `/ops-report` | `autocoder` | autocoder (maxSteps=6) | **general** (maxSteps=5) | ❌ |
| `/ship` | `orchestrator` | orchestrator (maxSteps=5) | orchestrator (maxSteps=5) | ✅ |
| `/review` | `reviewer` | reviewer (maxSteps=2) | reviewer (maxSteps=2) | ✅ |
| `/analyze` | `explore` | explore (maxSteps=4) | explore (maxSteps=4) | ✅ |

**Pattern:** Only commands with `agent: autocoder` are affected.

### Isolation
- Bug persists with `--pure` flag (no plugins loaded) → **not a plugin issue**
- Bug persists across fresh sessions → **not a stale session issue**
- No global config overrides (`OPENCODE_CONFIG`, `OPENCODE_CONFIG_DIR` are empty)

### DEBUG Logs
```
service=config path=/project/opencode.json loading
service=config loading config from /project/.opencode/opencode.jsonc  ← FILE DOES NOT EXIST
service=config loading config from /project/.opencode/opencode.json   ← FILE DOES NOT EXIST
```
The runtime attempts to load `.opencode/opencode.json` and `.opencode/opencode.jsonc` which don't exist. This may cause a silent config merge failure that drops the `agent:` field from command frontmatter.

### Additional Evidence
Creating an empty `.opencode/opencode.json` (`{}`) causes the runtime to **hang** on `--command autocode`, further suggesting the config merge logic is the root cause.

## Impact
- `/autocode` runs with `maxSteps: 50` (general) instead of `maxSteps: 6` (autocoder) — 8x more steps than intended
- Security/operational guardrails defined for `autocoder` are bypassed
- The `default_agent: "autocoder"` setting in `opencode.json` is ignored when using `--command`

## Workaround
```bash
opencode run --agent autocoder --command autocode "task"
```

## Related Files
- `opencode.json` — project-level config with `default_agent: "autocoder"`
- `.opencode/commands/autocode.md` — command with `agent: autocoder` frontmatter
- `.opencode/commands/ops-report.md` — also affected (same `agent: autocoder`)
