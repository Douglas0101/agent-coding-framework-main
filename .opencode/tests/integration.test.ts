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
import { readFile, unlink } from "node:fs/promises"
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
    expect(config.skills.paths).toContain(".opencode/skills")
    expect(config.agent).toBeDefined()
    expect(config.agent.reviewer).toBeDefined()
    expect(config.agent.reviewer.permission.write).toBe("deny")
    expect(config.agent.reviewer.permission.edit).toBe("deny")
    expect(config.agent.reviewer.permission.bash).toBe("deny")
    expect(config.agent.reviewer.permission.webfetch).toBe("deny")
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
    const spec = await readFile(
      path.join(PROJECT_ROOT, "execucao.md"),
      "utf-8",
    )
    expect(spec).toContain("deep-agent-ci.yml")
    expect(spec).toContain("unit-tests")
    expect(spec).toContain("integration-tests")
    expect(spec).toContain("e2e-tests")
    expect(spec).toContain("security-scan")
  })
})
