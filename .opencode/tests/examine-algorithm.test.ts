/**
 * UT-002: Unit tests for examine-algorithm.ts pure functions.
 *
 * Tests validate entity extraction, language detection, path security,
 * complexity estimation, and pattern detection logic.
 * Shared functions are imported from ../lib/shared.ts.
 */
import { describe, it, expect } from "bun:test"

import {
  type CodeEntity,
  type Signal,
  includesAny,
  detectLanguage,
  collectSignals,
  extractPythonEntities,
  isBlockedSensitivePath,
} from "../lib/shared"

// --- Test-specific functions (not in shared module) ---
function findBraceScopeEnd(lines: string[], startIndex: number): number {
  let braceDepth = 0
  let inString = false
  let stringChar = ""
  let lineEnd = startIndex + 1
  for (const char of lines[startIndex]) {
    if (char === '"' || char === "'") {
      if (!inString) { inString = true; stringChar = char }
      else if (char === stringChar) { inString = false }
    } else if (!inString) {
      if (char === "{") braceDepth++
      else if (char === "}") braceDepth--
    }
  }
  if (braceDepth === 0) return startIndex + 1
  for (let i = startIndex + 1; i < lines.length; i++) {
    for (const char of lines[i]) {
      if (char === '"' || char === "'") {
        if (!inString) { inString = true; stringChar = char }
        else if (char === stringChar) { inString = false }
      } else if (!inString) {
        if (char === "{") braceDepth++
        else if (char === "}") braceDepth--
      }
    }
    lineEnd = i + 1
    if (braceDepth === 0) break
  }
  return lineEnd
}

function extractTypeScriptEntities(text: string, kind: "function" | "class"): CodeEntity[] {
  const lines = text.split("\n")
  const result: CodeEntity[] = []
  const patterns =
    kind === "function"
      ? [
          /^\s*(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(/,
          /^\s*(?:export\s+)?const\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[a-zA-Z_$][a-zA-Z0-9_$]*)\s*=>/,
        ]
      : [/^\s*(?:export\s+)?class\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*(?:extends|implements)?/]
  for (let index = 0; index < lines.length; index++) {
    let matchedName: string | null = null
    for (const pattern of patterns) {
      const match = lines[index].match(pattern)
      if (match) { matchedName = match[1]; break }
    }
    if (!matchedName) continue
    const lineEnd = findBraceScopeEnd(lines, index)
    result.push({ name: matchedName, line_start: index + 1, line_end: lineEnd })
  }
  return result
}

function extractRustEntities(text: string, kind: "fn" | "struct" | "impl" | "mod"): CodeEntity[] {
  const lines = text.split("\n")
  const result: CodeEntity[] = []
  const patterns: { regex: RegExp; nameGroup: number }[] =
    kind === "fn"
      ? [{ regex: /^\s*(?:pub\s+)?(?:async\s+)?fn\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[<(]/, nameGroup: 1 }]
      : kind === "struct"
        ? [{ regex: /^\s*(?:pub\s+)?struct\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\(|\{|$)/, nameGroup: 1 }]
        : kind === "impl"
          ? [{ regex: /^\s*(?:pub\s+)?impl(?:<[^>]+>)?\s+(?:[a-zA-Z_][a-zA-Z0-9_]*\s+for\s+)?([a-zA-Z_][a-zA-Z0-9_]*)/, nameGroup: 1 }]
          : [{ regex: /^\s*(?:pub\s+)?mod\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[;{]/, nameGroup: 1 }]
  for (let index = 0; index < lines.length; index++) {
    let matchedName: string | null = null
    for (const { regex, nameGroup } of patterns) {
      const match = lines[index].match(regex)
      if (match) { matchedName = match[nameGroup]; break }
    }
    if (!matchedName) continue
    const lineEnd = findBraceScopeEnd(lines, index)
    result.push({ name: matchedName, line_start: index + 1, line_end: lineEnd })
  }
  return result
}

function estimateComplexity(text: string, signals: Signal[]): { time: string; space: string; confidence: string } {
  const loops = (text.match(/for |while |\.map\(|\.filter\(/g) ?? []).length
  const active = new Set(signals.filter((item) => item.matched).map((item) => item.label))
  if (active.has("ordenacao")) return { time: "O(n log n)", space: "O(1) a O(n)", confidence: "media" }
  if (active.has("programacao_dinamica")) return { time: "O(n) a O(n^2)", space: "O(n)", confidence: "media" }
  if (loops >= 2) return { time: "O(n^2)", space: "O(1) a O(n)", confidence: "media" }
  if (loops === 1 || active.has("hashing")) return { time: "O(n)", space: active.has("hashing") ? "O(n)" : "O(1) a O(n)", confidence: "alta" }
  return { time: "Inconclusivo", space: "Inconclusivo", confidence: "baixa" }
}

// --- Test Suite ---

describe("UT-002: examine-algorithm.ts", () => {

  // === Language Detection ===

  describe("language detection", () => {
    it("detects Python from .py extension", () => {
      expect(detectLanguage("src/model.py", "")).toBe("python")
    })

    it("detects TypeScript from .ts extension", () => {
      expect(detectLanguage("src/route.ts", "")).toBe("typescript")
    })

    it("detects TypeScript from .tsx extension", () => {
      expect(detectLanguage("src/App.tsx", "")).toBe("typescript")
    })

    it("detects Rust from .rs extension", () => {
      expect(detectLanguage("src/lib.rs", "")).toBe("rust")
    })

    it("detects Python from content (def)", () => {
      expect(detectLanguage(null, "def hello():\n    pass")).toBe("python")
    })

    it("detects TypeScript from content (function)", () => {
      expect(detectLanguage(null, "function hello() {\n  return 1\n}")).toBe("typescript")
    })

    it("detects Rust from content (fn)", () => {
      expect(detectLanguage(null, "fn main() {\n    println!(\"hello\");\n}")).toBe("rust")
    })

    it("returns unknown for unrecognizable content", () => {
      expect(detectLanguage(null, "just some text")).toBe("unknown")
    })

    it("extension takes priority over content", () => {
      // .py extension but TS content → python wins
      expect(detectLanguage("file.py", "function hello() {}")).toBe("python")
    })
  })

  // === Signal Collection ===

  describe("signal collection", () => {
    it("detects iteration signals", () => {
      const signals = collectSignals("for item in items: print(item)")
      const iter = signals.find(s => s.label === "iteracao")
      expect(iter?.matched).toBe(true)
    })

    it("detects sorting signals", () => {
      const signals = collectSignals("return sorted(data)")
      const sort = signals.find(s => s.label === "ordenacao")
      expect(sort?.matched).toBe(true)
    })

    it("detects hashing signals", () => {
      const signals = collectSignals("cache = {} dict lookup")
      const hash = signals.find(s => s.label === "hashing")
      expect(hash?.matched).toBe(true)
    })

    it("detects DP signals", () => {
      const signals = collectSignals("memo = {} dp table")
      const dp = signals.find(s => s.label === "programacao_dinamica")
      expect(dp?.matched).toBe(true)
    })

    it("does not match when signal absent", () => {
      const signals = collectSignals("x = 42")
      const all = signals.filter(s => s.matched)
      expect(all).toHaveLength(0)
    })
  })

  // === Python Entity Extraction ===

  describe("Python entity extraction", () => {
    it("extracts top-level functions", () => {
      const code = "def hello():\n    return 1\n\ndef world():\n    return 2"
      const entities = extractPythonEntities(code, "def")
      expect(entities).toHaveLength(2)
      expect(entities[0].name).toBe("hello")
      expect(entities[0].line_start).toBe(1)
      expect(entities[1].name).toBe("world")
    })

    it("extracts classes", () => {
      const code = "class Model:\n    def __init__(self):\n        pass"
      const entities = extractPythonEntities(code, "class")
      expect(entities).toHaveLength(1)
      expect(entities[0].name).toBe("Model")
    })

    it("handles nested functions with indentation", () => {
      const code = "def outer():\n    def inner():\n        return 1\n    return inner"
      const entities = extractPythonEntities(code, "def")
      expect(entities).toHaveLength(2)
      expect(entities[0].name).toBe("outer")
      expect(entities[1].name).toBe("inner")
    })

    it("returns empty for no matches", () => {
      const entities = extractPythonEntities("x = 42", "def")
      expect(entities).toHaveLength(0)
    })
  })

  // === TypeScript Entity Extraction ===

  describe("TypeScript entity extraction", () => {
    it("extracts function declarations", () => {
      const code = "export function hello() {\n  return 1\n}"
      const entities = extractTypeScriptEntities(code, "function")
      expect(entities).toHaveLength(1)
      expect(entities[0].name).toBe("hello")
    })

    it("extracts arrow functions", () => {
      const code = "const add = (a: number, b: number) => {\n  return a + b\n}"
      const entities = extractTypeScriptEntities(code, "function")
      expect(entities).toHaveLength(1)
      expect(entities[0].name).toBe("add")
    })

    it("extracts async functions", () => {
      const code = "export async function fetchData() {\n  const res = await fetch(url)\n  return res.json()\n}"
      const entities = extractTypeScriptEntities(code, "function")
      expect(entities).toHaveLength(1)
      expect(entities[0].name).toBe("fetchData")
    })

    it("extracts classes", () => {
      const code = "export class MyComponent extends React.Component {\n  render() {\n    return null\n  }\n}"
      const entities = extractTypeScriptEntities(code, "class")
      expect(entities).toHaveLength(1)
      expect(entities[0].name).toBe("MyComponent")
    })

    it("detects brace scope correctly", () => {
      const code = "function outer() {\n  if (true) {\n    return 1\n  }\n}\nfunction inner() {\n  return 2\n}"
      const entities = extractTypeScriptEntities(code, "function")
      expect(entities).toHaveLength(2)
      expect(entities[0].name).toBe("outer")
      expect(entities[1].name).toBe("inner")
    })
  })

  // === Rust Entity Extraction ===

  describe("Rust entity extraction", () => {
    it("extracts public functions", () => {
      const code = "pub fn decrypt_aes_gcm(ciphertext: &[u8]) -> Vec<u8> {\n    let key = derive_key();\n    decrypt(ciphertext, &key)\n}"
      const entities = extractRustEntities(code, "fn")
      expect(entities).toHaveLength(1)
      expect(entities[0].name).toBe("decrypt_aes_gcm")
    })

    it("extracts private functions", () => {
      const code = "fn helper() -> u32 {\n    42\n}"
      const entities = extractRustEntities(code, "fn")
      expect(entities).toHaveLength(1)
      expect(entities[0].name).toBe("helper")
    })

    it("extracts structs", () => {
      const code = "pub struct MemoryGuard {\n    data: Vec<u8>,\n}"
      const entities = extractRustEntities(code, "struct")
      expect(entities).toHaveLength(1)
      expect(entities[0].name).toBe("MemoryGuard")
    })

    it("extracts impl blocks", () => {
      const code = "impl Drop for MemoryGuard {\n    fn drop(&mut self) {\n        self.data.fill(0);\n    }\n}"
      const entities = extractRustEntities(code, "impl")
      expect(entities).toHaveLength(1)
      expect(entities[0].name).toBe("MemoryGuard")
    })

    it("extracts mod declarations", () => {
      const code = "#[cfg(test)]\nmod tests {\n    #[test]\n    fn test_roundtrip() {\n        assert!(true);\n    }\n}"
      const entities = extractRustEntities(code, "mod")
      expect(entities).toHaveLength(1)
      expect(entities[0].name).toBe("tests")
    })

    it("detects brace scope for nested blocks", () => {
      const code = "fn outer() {\n    if true {\n        return\n    }\n}\nfn inner() {\n    return\n}"
      const entities = extractRustEntities(code, "fn")
      expect(entities).toHaveLength(2)
    })
  })

  // === Brace Scope End ===

  describe("brace scope detection", () => {
    it("counts braces correctly for simple block", () => {
      const lines = ["function foo() {", "  return 1", "}"]
      expect(findBraceScopeEnd(lines, 0)).toBe(3)
    })

    it("handles nested braces", () => {
      const lines = ["function foo() {", "  if (true) {", "    return 1", "  }", "}"]
      expect(findBraceScopeEnd(lines, 0)).toBe(5)
    })

    it("handles single-line (no brace)", () => {
      const lines = ["const x = 42;"]
      expect(findBraceScopeEnd(lines, 0)).toBe(1)
    })
  })

  // === Complexity Estimation ===

  describe("complexity estimation", () => {
    it("detects sorting complexity", () => {
      const signals = collectSignals("return sorted(items)")
      const result = estimateComplexity("for item in items: compare(item)", signals)
      expect(result.time).toContain("O(n log n)")
    })

    it("detects nested loop complexity", () => {
      const signals = collectSignals("x")
      const result = estimateComplexity("for i in range(n): for j in range(n): pass", signals)
      expect(result.time).toContain("O(n^2)")
    })

    it("detects single loop complexity", () => {
      const signals = collectSignals("x")
      const result = estimateComplexity("for item in items: process(item)", signals)
      expect(result.time).toContain("O(n)")
    })

    it("returns inconclusive for no signals", () => {
      const signals = collectSignals("x = 42")
      const result = estimateComplexity("x = 42", signals)
      expect(result.time).toBe("Inconclusivo")
    })
  })

  // === Path Security ===

  describe("path traversal protection", () => {
    it("blocks .env files (except .env.example)", () => {
      expect(isBlockedSensitivePath("/tmp/.env")).toBe(true)
    })

    it("allows .env.example", () => {
      expect(isBlockedSensitivePath("/tmp/.env.example")).toBe(false)
    })

    it("blocks .env.local", () => {
      expect(isBlockedSensitivePath("/tmp/.env.local")).toBe(true)
    })

    it("blocks credentials.json", () => {
      expect(isBlockedSensitivePath("/tmp/credentials.json")).toBe(true)
    })

    it("blocks pem files", () => {
      expect(isBlockedSensitivePath("/tmp/private.pem")).toBe(true)
    })

    it("does not block normal files", () => {
      expect(isBlockedSensitivePath("/tmp/config.json")).toBe(false)
    })
  })
})
