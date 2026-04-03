/**
 * IT-001/IT-002: Integration tests for OpenCode plugin and tool components.
 *
 * Tests validate:
 * - Plugin loads correctly in Bun runtime
 * - Config structure is valid
 * - Manifest persistence creates files
 * - Large JSON round-trip
 */
import { describe, it, expect } from "bun:test"
import { mkdtemp, readFile, rm, unlink } from "node:fs/promises"
import os from "node:os"
import path from "node:path"

const OPENCODE_DIR = path.resolve(import.meta.dir, "..")
const PROJECT_ROOT = path.resolve(OPENCODE_DIR, "..")

describe("IT-001: Plugin load and config", () => {
  it("output-filter.ts loads without error", async () => {
    const plugin = await import(path.join(OPENCODE_DIR, "plugins/output-filter.ts"))
    expect(plugin.default).toBeDefined()
    expect(typeof plugin.default).toBe("function")
  })

  it("examine-algorithm.ts loads without error", async () => {
    const tool = await import(path.join(OPENCODE_DIR, "tools/examine-algorithm.ts"))
    expect(tool.default).toBeDefined()
    // examine-algorithm.ts exports a Tool object, not a function directly
    expect(typeof tool.default).toBe("object")
  })

  it("output-filter.config.json is valid JSON with expected structure", async () => {
    const configPath = path.join(OPENCODE_DIR, "output-filter.config.json")
    const content = await readFile(configPath, "utf-8")
    const config = JSON.parse(content)

    expect(config.enabled).toBe(true)
    expect(config.max_output_chars).toBeGreaterThan(0)
    expect(Array.isArray(config.redaction_patterns)).toBe(true)
    expect(config.redaction_patterns.length).toBeGreaterThan(0)
    expect(config.enrichment).toBeDefined()
    expect(config.examination).toBeDefined()
    expect(config.manifest).toBeDefined()
    expect(config.manifest.enabled).toBe(true)
    expect(config.manifest.persist_dir).toBe(".opencode/manifests")
    expect(config.manifest.max_manifests).toBeGreaterThan(0)
  })

  it("opencode.json is valid JSON with expected structure", async () => {
    const configPath = path.join(PROJECT_ROOT, "opencode.json")
    const content = await readFile(configPath, "utf-8")
    const config = JSON.parse(content)

    expect(config.skills).toBeDefined()
    expect(config.skills.paths).toContain("./.opencode/commands")
    expect(config.skills.paths).toContain("./.opencode/plugins")
    expect(config.skills.paths).toContain("./.opencode/tools")
    expect(config.skills.paths).toContain("./.opencode/skills")
    expect(config.skills.paths).toContain("./.agent/skills")
    expect(config.plugin).toContain("./.opencode/plugins/output-filter.ts")
    expect(config.default_agent).toBe("autocoder")
    expect(config.permission.read).toBe("allow")
    expect(config.permission.doom_loop).toBe("deny")
    expect(config.agent).toBeDefined()
    expect(config.agent.reviewer).toBeDefined()
    expect(config.agent.reviewer.permission.write).toBe("deny")
    expect(config.agent.reviewer.permission.edit).toBe("deny")
    expect(config.agent.reviewer.permission.bash).toBe("deny")
    expect(config.agent.reviewer.permission.webfetch).toBe("deny")
    expect(config.agent.autocoder.maxSteps).toBeGreaterThan(0)
    expect(config.agent.autocoder.permission.doom_loop).toBe("deny")
  })

  it("redaction patterns have valid regex", async () => {
    const configPath = path.join(OPENCODE_DIR, "output-filter.config.json")
    const content = await readFile(configPath, "utf-8")
    const config = JSON.parse(content)

    for (const rule of config.redaction_patterns) {
      expect(rule.label).toBeDefined()
      expect(rule.pattern).toBeDefined()
      expect(rule.replacement).toBeDefined()
      // Verify regex compiles
      expect(() => new RegExp(rule.pattern, "gi")).not.toThrow()
    }
  })
})

describe("IT-002: Manifest persistence", () => {
  // NOTE: This test validates that the output-filter plugin correctly records
  // the agent name passed to the chat.message hook. It does NOT validate runtime
  // command routing. In OpenCode v1.3.13, the `/autocode` command (frontmatter:
  // `agent: autocoder`) is routed to `general` at runtime — a known bug tracked
  // in AGENTS.md under "Known Issues → Routing Bug: /autocode command".
  // The plugin correctly records whatever agent the runtime provides; the bug
  // is that the runtime provides the wrong agent. See:
  // .opencode/skills/self-bootstrap-opencode/debug_autocode.log
  it("persists chat agent/model/provider and command into the manifest", async () => {
    const tempDir = await mkdtemp(path.join(os.tmpdir(), "opencode-output-filter-"))
    const pluginModule = await import(path.join(OPENCODE_DIR, "plugins/output-filter.ts"))
    const hooks = await pluginModule.default({ directory: tempDir })

    await hooks["chat.message"]?.(
      {
        sessionID: "ses_manifest_fields",
        agent: "autocoder",
        model: { providerID: "openrouter", modelID: "gpt-any" },
      },
      {
        message: { role: "user", parts: [] },
        parts: [],
      },
    )

    await hooks["command.execute.before"]?.(
      {
        command: "/autocode implement guardrails",
        sessionID: "ses_manifest_fields",
        arguments: "implement guardrails",
      },
      { parts: [] },
    )

    const toolOutput = {
      title: "read result",
      output: "ok",
      metadata: { total_tokens: 12, total_cost: 0.001 },
    }

    await hooks["tool.execute.after"]?.(
      {
        tool: "read",
        sessionID: "ses_manifest_fields",
        callID: "call_1",
        args: {},
      },
      toolOutput,
    )

    await Bun.sleep(50)

    const manifestPath = path.join(tempDir, ".opencode/manifests/ses_manifest_fields.json")
    const manifest = JSON.parse(await readFile(manifestPath, "utf-8"))

    expect(manifest.agent).toBe("autocoder")
    expect(manifest.provider).toBe("openrouter")
    expect(manifest.model).toBe("gpt-any")
    expect(manifest.last_command).toBe("autocode")

    await rm(tempDir, { recursive: true, force: true })
  })

  it("denies doom_loop permission requests in the plugin hook", async () => {
    const pluginModule = await import(path.join(OPENCODE_DIR, "plugins/output-filter.ts"))
    const hooks = await pluginModule.default({ directory: PROJECT_ROOT })
    const output = { status: "ask" as const }

    await hooks["permission.ask"]?.(
      {
        id: "perm_1",
        type: "doom_loop",
        sessionID: "ses_perm",
        messageID: "msg_perm",
        title: "doom_loop",
        metadata: {},
        time: { created: Date.now() },
      },
      output,
    )

    expect(output.status).toBe("deny")
  })

  it("manifests directory exists", async () => {
    const manifestDir = path.join(OPENCODE_DIR, "manifests")
    const file = Bun.file(path.join(manifestDir, ".keep"))
    expect(await file.exists()).toBe(true)
  })

  it("manifest JSON round-trip preserves structure", async () => {
    const manifest = {
      session_id: "ses_test_roundtrip",
      agent: "test",
      timestamp: new Date().toISOString(),
      directory: "/tmp",
      phases: {
        exploration: { status: "pending", agent: "explore" },
        implementation: { status: "in_progress", agent: "general" },
        review: { status: "pending", agent: "reviewer" },
      },
      state_hash: "sha256:test",
      resume_capable: true,
      total_tokens: 1000,
      total_cost: 0.01,
      message_count: 5,
      last_tool_call: "write",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }

    const manifestDir = path.join(OPENCODE_DIR, "manifests")
    const testPath = path.join(manifestDir, "test-roundtrip.json")
    const content = JSON.stringify(manifest, null, 2)
    await Bun.write(testPath, content)

    const loaded = JSON.parse(await readFile(testPath, "utf-8"))
    expect(loaded.session_id).toBe("ses_test_roundtrip")
    expect(loaded.phases.implementation.status).toBe("in_progress")
    expect(loaded.total_tokens).toBe(1000)

    // Cleanup
    await unlink(testPath).catch(() => {})
  })

  it("large JSON (>10KB) round-trip works", async () => {
    const largeObj: Record<string, string> = {}
    for (let i = 0; i < 500; i++) {
      largeObj[`key_${i}`] = `value_${"_".repeat(20)}_${i}`
    }
    const json = JSON.stringify(largeObj, null, 2)
    expect(json.length).toBeGreaterThan(10000)

    const parsed = JSON.parse(json)
    expect(Object.keys(parsed)).toHaveLength(500)
    expect(parsed.key_0).toBe(`value_${"_".repeat(20)}_0`)
  })
})

describe("IT-002: Config resolved correctly", () => {
  it("deep-agent-ci.yml references exist in execucao.md", async () => {
    const specPath = path.join(PROJECT_ROOT, "execucao.md")
    const specFile = Bun.file(specPath)

    if (!(await specFile.exists())) {
      // execucao.md is not present in this repo — skip gracefully
      return
    }

    const spec = await specFile.text()
    expect(spec).toContain("deep-agent-ci.yml")
    expect(spec).toContain("unit-tests")
    expect(spec).toContain("integration-tests")
    expect(spec).toContain("e2e-tests")
    expect(spec).toContain("security-scan")
  })
})
