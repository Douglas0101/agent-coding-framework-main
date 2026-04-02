/**
 * UT-001: Unit tests for output-filter.ts pure functions.
 *
 * Tests validate the same logic used in production.
 * Shared functions are imported from ../lib/shared.ts.
 * Test-specific functions remain duplicated inline.
 */
import { describe, it, expect } from "bun:test"

import {
  type PatternRule,
  normalizeFlags,
  applyRedactions,
  isSensitiveKey,
} from "../lib/shared"

// --- Test-specific functions (not in shared module) ---
function classifyTool(tool: string, args: Record<string, unknown>): string {
  if (tool === "read" || tool === "glob" || tool === "grep") {
    return "file_reading"
  }
  if (tool === "edit" || tool === "write") {
    return "file_modification"
  }
  if (tool === "task") {
    return "subtask_delegation"
  }
  if (tool !== "bash") {
    return "shell_command"
  }
  const command = String(args.command ?? "")
  if (/(^|\s)(pytest|py\.test|python -m pytest|make test)\b/.test(command)) {
    return "test_execution"
  }
  if (/(^|\s)(ruff|mypy|bandit|make lint|make typecheck|make security)\b/.test(command)) {
    return "code_analysis"
  }
  return "shell_command"
}

function parseJsonLike(text: string): unknown | null {
  const candidate = text.trim()
  if (!(candidate.startsWith("{") || candidate.startsWith("["))) {
    return null
  }
  try {
    return JSON.parse(candidate)
  } catch {
    return null
  }
}

// isSensitiveKey is imported from ../lib/shared.ts

function redactJsonValue(
  value: unknown,
  rules: PatternRule[],
  parentKey?: string,
): unknown {
  if (parentKey && isSensitiveKey(parentKey)) {
    return typeof value === "string" ? "[redacted]" : value
  }
  if (typeof value === "string") {
    return applyRedactions(value, rules).text
  }
  if (Array.isArray(value)) {
    return value.map((item) => redactJsonValue(item, rules, parentKey))
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, nested]) => [
        key,
        redactJsonValue(nested, rules, key),
      ]),
    )
  }
  return value
}

type ManifestPhase = {
  status: "pending" | "in_progress" | "complete" | "failed"
  agent: string
}

type SessionManifest = {
  session_id: string
  agent: string
  timestamp: string
  directory: string
  phases: {
    exploration: ManifestPhase
    implementation: ManifestPhase
    review: ManifestPhase
  }
  state_hash: string
  resume_capable: boolean
  total_tokens: number
  total_cost: number
  message_count: number
  last_tool_call: string
  created_at: string
  updated_at: string
}

type PhaseLabel = "exploration" | "implementation" | "review"

function detectPhase(tool: string, args: Record<string, unknown>): PhaseLabel {
  if (["read", "glob", "grep", "examine-algorithm"].includes(tool)) {
    return "exploration"
  }
  if (
    tool === "task" &&
    (args.agent === "reviewer" ||
      String(args.description ?? "").includes("review"))
  ) {
    return "review"
  }
  if (["write", "edit", "bash"].includes(tool)) {
    return "implementation"
  }
  return "implementation"
}

function stableStringify(value: unknown): string {
  function sortJsonValue(v: unknown): unknown {
    if (Array.isArray(v)) return v.map(sortJsonValue)
    if (v && typeof v === "object")
      return Object.fromEntries(
        Object.entries(v)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([k, n]) => [k, sortJsonValue(n)]),
      )
    return v
  }
  return JSON.stringify(sortJsonValue(value))
}

function computeStateHash(
  manifest: Omit<SessionManifest, "state_hash">,
): string {
  const canonical = stableStringify(manifest)
  const hasher = new Bun.CryptoHasher("sha256")
  hasher.update(canonical)
  return `sha256:${hasher.digest("hex")}`
}

function sanitizeFileComponent(value: string): string {
  const sanitized = value.replace(/[^a-zA-Z0-9._-]+/g, "-")
  return sanitized.length > 0 ? sanitized : "unknown-session"
}

function getSessionID(input: unknown): string {
  if (!input || typeof input !== "object") return "unknown-session"
  const record = input as Record<string, unknown>
  const sessionID = record.sessionID ?? record.sessionId ?? record.session_id
  return typeof sessionID === "string" && sessionID.length > 0
    ? sessionID
    : "unknown-session"
}

// --- Test Suite ---

describe("UT-001: output-filter.ts", () => {
  // === Secret Redaction ===

  describe("secret redaction (100% recall)", () => {
    const rules: PatternRule[] = [
      {
        label: "api_key",
        pattern: "(api[_-]?key\\s*[=:]\\s*)([^\\s,;]+)",
        flags: "i",
        replacement: "$1[redacted]",
      },
      {
        label: "bearer",
        pattern: "(authorization\\s*:\\s*bearer\\s+)([^\\s]+)",
        flags: "i",
        replacement: "$1[redacted]",
      },
      {
        label: "secret",
        pattern: "((?:secret|token|password)\\s*[=:]\\s*)([^\\s,;]+)",
        flags: "i",
        replacement: "$1[redacted]",
      },
    ]

    it("redacts api_key patterns", () => {
      const result = applyRedactions("api_key=super-secret-key", rules)
      expect(result.text).toContain("[redacted]")
      expect(result.applied).toContain("api_key")
    })

    it("redacts bearer tokens", () => {
      const result = applyRedactions("authorization: bearer abc123token", rules)
      expect(result.text).toContain("[redacted]")
      expect(result.applied).toContain("bearer")
    })

    it("redacts password patterns", () => {
      const result = applyRedactions("password=hunter2", rules)
      expect(result.text).toContain("[redacted]")
      expect(result.applied).toContain("secret")
    })

    it("redacts token patterns", () => {
      const result = applyRedactions("token=my-token-value", rules)
      expect(result.text).toContain("[redacted]")
      expect(result.applied).toContain("secret")
    })

    it("returns clean text when no secrets present", () => {
      const result = applyRedactions("def hello(): return 'world'", rules)
      expect(result.text).toBe("def hello(): return 'world'")
      expect(result.applied).toHaveLength(0)
    })
  })

  // === Tool Classification ===

  describe("tool classification", () => {
    it("classifies read/glob/grep as file_reading", () => {
      expect(classifyTool("read", {})).toBe("file_reading")
      expect(classifyTool("glob", {})).toBe("file_reading")
      expect(classifyTool("grep", {})).toBe("file_reading")
    })

    it("classifies edit/write as file_modification", () => {
      expect(classifyTool("edit", {})).toBe("file_modification")
      expect(classifyTool("write", {})).toBe("file_modification")
    })

    it("classifies task as subtask_delegation", () => {
      expect(classifyTool("task", {})).toBe("subtask_delegation")
    })

    it("classifies pytest as test_execution", () => {
      expect(classifyTool("bash", { command: "pytest tests/" })).toBe("test_execution")
    })

    it("classifies ruff as code_analysis", () => {
      expect(classifyTool("bash", { command: "ruff check src/" })).toBe("code_analysis")
    })

    it("classifies other bash as shell_command", () => {
      expect(classifyTool("bash", { command: "ls -la" })).toBe("shell_command")
    })
  })

  // === JSON Parsing ===

  describe("JSON parsing", () => {
    it("parses valid JSON objects", () => {
      expect(parseJsonLike('{"a":1}')).toEqual({ a: 1 })
    })

    it("parses valid JSON arrays", () => {
      expect(parseJsonLike("[1,2,3]")).toEqual([1, 2, 3])
    })

    it("returns null for non-JSON text", () => {
      expect(parseJsonLike("hello world")).toBeNull()
    })

    it("returns null for invalid JSON", () => {
      expect(parseJsonLike("{invalid}")).toBeNull()
    })

    it("returns null for empty string", () => {
      expect(parseJsonLike("")).toBeNull()
    })
  })

  // === Sensitive Key Detection ===

  describe("sensitive key detection", () => {
    it("detects api_key as sensitive", () => {
      expect(isSensitiveKey("api_key")).toBe(true)
      expect(isSensitiveKey("apiKey")).toBe(true)
    })

    it("detects authorization as sensitive", () => {
      expect(isSensitiveKey("authorization")).toBe(true)
    })

    it("detects token as sensitive", () => {
      expect(isSensitiveKey("token")).toBe(true)
    })

    it("detects password as sensitive", () => {
      expect(isSensitiveKey("password")).toBe(true)
    })

    it("detects secret as sensitive", () => {
      expect(isSensitiveKey("secret")).toBe(true)
    })

    it("does not flag normal keys", () => {
      expect(isSensitiveKey("name")).toBe(false)
      expect(isSensitiveKey("value")).toBe(false)
      expect(isSensitiveKey("count")).toBe(false)
    })
  })

  // === JSON Value Redaction ===

  describe("JSON value redaction", () => {
    const rules: PatternRule[] = [
      { label: "secret", pattern: "(secret\\s*[=:]\\s*)([^\\s,;]+)", flags: "i", replacement: "$1[redacted]" },
    ]

    it("redacts values under sensitive keys", () => {
      const result = redactJsonValue({ api_key: "super-secret-key" }, rules)
      expect((result as Record<string, unknown>).api_key).toBe("[redacted]")
    })

    it("preserves values under non-sensitive keys", () => {
      const result = redactJsonValue({ name: "hello" }, rules)
      expect((result as Record<string, unknown>).name).toBe("hello")
    })

    it("handles nested objects", () => {
      const result = redactJsonValue({
        config: { secret: "super-secret-value" },
        name: "test",
      }, rules)
      const obj = result as Record<string, unknown>
      expect((obj.config as Record<string, unknown>).secret).toBe("[redacted]")
      expect(obj.name).toBe("test")
    })

    it("handles arrays", () => {
      const result = redactJsonValue([{ token: "super-secret-token" }, { name: "test" }], rules)
      expect((result as Array<Record<string, unknown>>)[0].token).toBe("[redacted]")
      expect((result as Array<Record<string, unknown>>)[1].name).toBe("test")
    })
  })

  // === Phase Detection ===

  describe("phase detection", () => {
    it("maps read/glob/grep to exploration", () => {
      expect(detectPhase("read", {})).toBe("exploration")
      expect(detectPhase("glob", {})).toBe("exploration")
      expect(detectPhase("grep", {})).toBe("exploration")
      expect(detectPhase("examine-algorithm", {})).toBe("exploration")
    })

    it("maps write/edit/bash to implementation", () => {
      expect(detectPhase("write", {})).toBe("implementation")
      expect(detectPhase("edit", {})).toBe("implementation")
      expect(detectPhase("bash", {})).toBe("implementation")
    })

    it("maps task(reviewer) to review", () => {
      expect(detectPhase("task", { agent: "reviewer" })).toBe("review")
    })

    it("maps task(review in description) to review", () => {
      expect(detectPhase("task", { description: "review the changes" })).toBe("review")
    })

    it("maps task(other) to implementation", () => {
      expect(detectPhase("task", { agent: "general" })).toBe("implementation")
    })

    it("maps unknown tool to implementation", () => {
      expect(detectPhase("unknown-tool", {})).toBe("implementation")
    })
  })

  // === State Hash ===

  describe("state hash (SHA-256)", () => {
    const baseManifest = {
      session_id: "ses_test",
      agent: "autocoder",
      timestamp: "2026-01-01T00:00:00.000Z",
      directory: "/tmp",
      phases: {
        exploration: { status: "pending", agent: "explore" },
        implementation: { status: "pending", agent: "general" },
        review: { status: "pending", agent: "reviewer" },
      },
      resume_capable: false,
      total_tokens: 0,
      total_cost: 0,
      message_count: 0,
      last_tool_call: "",
      created_at: "2026-01-01T00:00:00.000Z",
      updated_at: "2026-01-01T00:00:00.000Z",
    }

    it("produces deterministic hash", () => {
      const hash1 = computeStateHash(baseManifest)
      const hash2 = computeStateHash(baseManifest)
      expect(hash1).toBe(hash2)
    })

    it("starts with sha256: prefix", () => {
      const hash = computeStateHash(baseManifest)
      expect(hash).toMatch(/^sha256:[a-f0-9]{64}$/)
    })

    it("changes when manifest changes", () => {
      const hash1 = computeStateHash(baseManifest)
      const hash2 = computeStateHash({ ...baseManifest, last_tool_call: "read" })
      expect(hash1).not.toBe(hash2)
    })

    it("stable stringify produces sorted keys", () => {
      const a = stableStringify({ z: 1, a: 2, m: 3 })
      expect(a).toBe('{"a":2,"m":3,"z":1}')
    })
  })

  // === File Component Sanitization ===

  describe("file component sanitization", () => {
    it("replaces special chars with hyphens", () => {
      expect(sanitizeFileComponent("ses_abc!@#def")).toBe("ses_abc-def")
    })

    it("preserves valid characters", () => {
      expect(sanitizeFileComponent("ses_abc-123.def")).toBe("ses_abc-123.def")
    })

    it("replaces all-special string with hyphens", () => {
      expect(sanitizeFileComponent("!!!")).toBe("-")
    })

    it("returns fallback for empty string input", () => {
      expect(sanitizeFileComponent("")).toBe("unknown-session")
    })
  })

  // === Session ID Extraction ===

  describe("session ID extraction", () => {
    it("extracts sessionID from input", () => {
      expect(getSessionID({ sessionID: "ses_abc" })).toBe("ses_abc")
    })

    it("extracts sessionId (camelCase) fallback", () => {
      expect(getSessionID({ sessionId: "ses_def" })).toBe("ses_def")
    })

    it("extracts session_id (snake_case) fallback", () => {
      expect(getSessionID({ session_id: "ses_ghi" })).toBe("ses_ghi")
    })

    it("returns unknown-session for null input", () => {
      expect(getSessionID(null)).toBe("unknown-session")
    })

    it("returns unknown-session for non-object input", () => {
      expect(getSessionID("string")).toBe("unknown-session")
    })

    it("returns unknown-session for empty sessionID", () => {
      expect(getSessionID({ sessionID: "" })).toBe("unknown-session")
    })
  })
})
