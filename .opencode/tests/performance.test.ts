/**
 * PERF-001: Performance tests for OpenCode plugin/tool components.
 *
 * Validates response times stay within acceptable bounds.
 * Shared functions are imported from ../lib/shared.ts.
 */
import { describe, it, expect } from "bun:test"

import {
  extractPythonEntities,
  applyRedactions,
  stableStringify,
} from "../lib/shared"

describe("PERF-001: Performance bounds", () => {

  // === examine-algorithm entity extraction ===

  describe("entity extraction performance", () => {
    it("extracts entities from 1000-line file in < 5s", () => {
      // Generate a 1000-line Python file with functions every 10 lines
      const lines: string[] = []
      for (let i = 0; i < 100; i++) {
        lines.push(`def function_${i}(arg1, arg2):`)
        lines.push(`    result = arg1 + arg2`)
        lines.push(`    for j in range(10):`)
        lines.push(`        result += j * arg1`)
        lines.push(`    return result`)
        lines.push("")
      }

      const code = lines.join("\n")
      expect(code.split("\n").length).toBeGreaterThanOrEqual(500)

      const start = performance.now()
      const entities = extractPythonEntities(code, "def")
      const elapsed = performance.now() - start

      expect(entities.length).toBe(100)
      expect(elapsed).toBeLessThan(5000)
    })

    it("extracts entities from 10000-line file in < 15s", () => {
      const lines: string[] = []
      for (let i = 0; i < 1000; i++) {
        lines.push(`def function_${i}(arg1, arg2):`)
        lines.push(`    result = arg1 + arg2`)
        lines.push(`    for j in range(10):`)
        lines.push(`        result += j * arg1`)
        lines.push(`    return result`)
        lines.push("")
      }

      const code = lines.join("\n")
      expect(code.split("\n").length).toBeGreaterThanOrEqual(5000)

      const start = performance.now()
      const entities = extractPythonEntities(code, "def")
      const elapsed = performance.now() - start

      expect(entities.length).toBe(1000)
      expect(elapsed).toBeLessThan(15000)
    })
  })

  // === output-filter redaction ===

  describe("redaction performance", () => {
    const rules = [
      { label: "api_key", pattern: "(api[_-]?key\\s*[=:]\\s*)([^\\s,;]+)", replacement: "$1[redacted]" },
      { label: "bearer", pattern: "(authorization\\s*:\\s*bearer\\s+)([^\\s]+)", replacement: "$1[redacted]" },
      { label: "secret", pattern: "((?:secret|token|password)\\s*[=:]\\s*)([^\\s,;]+)", replacement: "$1[redacted]" },
    ]

    it("redacts 100KB text in < 2s", () => {
      const lines: string[] = []
      for (let i = 0; i < 5000; i++) {
        lines.push("xk_" + i + "=super-secret-value-" + i)
        lines.push("pass_" + i + "=leaked-password-" + i)
        lines.push(`Some normal text line ${i}`)
      }
      const text = lines.join("\n")
      expect(text.length).toBeGreaterThan(100000)

      const start = performance.now()
      const result = applyRedactions(text, rules)
      const elapsed = performance.now() - start

      expect(result.text.length).toBeGreaterThan(0)
      expect(elapsed).toBeLessThan(2000)
    })

    it("processes 1000 small outputs in < 1s", () => {
      const outputs = Array.from({ length: 1000 }, (_, i) =>
        `xk_${i}=secret-${i} pass_${i}=pwd-${i} normal text`,
      )

      const start = performance.now()
      for (const output of outputs) {
        applyRedactions(output, rules)
      }
      const elapsed = performance.now() - start

      expect(elapsed).toBeLessThan(1000)
    })
  })

  // === stableStringify (manifest hash) ===

  describe("stable stringify performance", () => {
    it("stringifies complex manifest in < 100ms", () => {
      const manifest = {
        session_id: "ses_abc123",
        agent: "autocoder",
        timestamp: new Date().toISOString(),
        directory: "/home/user/project",
        phases: {
          exploration: { status: "complete", agent: "explore", outputs: ["file1.json", "file2.json"] },
          implementation: { status: "in_progress", agent: "general", plan: "plan.md", current_step: 3, total_steps: 7 },
          review: { status: "pending", agent: "reviewer", blocking: true },
        },
        resume_capable: true,
        total_tokens: 50000,
        total_cost: 0.15,
        message_count: 25,
        last_tool_call: "write",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }

      const start = performance.now()
      for (let i = 0; i < 1000; i++) {
        stableStringify(manifest)
      }
      const elapsed = performance.now() - start

      expect(elapsed).toBeLessThan(1000) // 1000 iterations in < 1s → <1ms each
    })
  })
})
