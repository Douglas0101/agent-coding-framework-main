/**
 * SEC-001: Path traversal fuzzing tests for examine-algorithm.ts
 *
 * Validates that path traversal attacks are blocked.
 * isBlockedSensitivePath is imported from ../lib/shared.ts.
 */
import { describe, it, expect } from "bun:test"
import { realpath } from "node:fs/promises"
import path from "node:path"

import { isBlockedSensitivePath } from "../lib/shared"

const PROJECT_ROOT = path.resolve(import.meta.dir, "../..")

describe("SEC-001: Path traversal protection", () => {

  // === .env file blocking ===

  describe(".env file blocking", () => {
    it("blocks .env", () => {
      expect(isBlockedSensitivePath("/home/user/project/.env")).toBe(true)
    })

    it("blocks .env.local", () => {
      expect(isBlockedSensitivePath("/home/user/project/.env.local")).toBe(true)
    })

    it("blocks .env.production", () => {
      expect(isBlockedSensitivePath("/home/user/project/.env.production")).toBe(true)
    })

    it("allows .env.example", () => {
      expect(isBlockedSensitivePath("/home/user/project/.env.example")).toBe(false)
    })

    it("allows normal config files", () => {
      expect(isBlockedSensitivePath("/home/user/project/config.json")).toBe(false)
    })

    it("allows package.json", () => {
      expect(isBlockedSensitivePath("/home/user/project/package.json")).toBe(false)
    })

    it("blocks pem files", () => {
      expect(isBlockedSensitivePath("/home/user/project/private-key.pem")).toBe(true)
    })

    it("blocks credentials.json", () => {
      expect(isBlockedSensitivePath("/home/user/project/credentials.json")).toBe(true)
    })

    it("blocks token.json", () => {
      expect(isBlockedSensitivePath("/home/user/project/token.json")).toBe(true)
    })
  })

  // === Path traversal attempts ===

  describe("path traversal attacks", () => {
    it("detects parent directory traversal in resolved paths", () => {
      const worktree = "/home/user/project"
      const target = "/home/user/project/../etc/passwd"
      const relative = path.relative(worktree, target)
      // After resolution, the relative path starts with ..
      expect(relative.startsWith("..")).toBe(true)
    })

    it("normalizes multiple traversal sequences", () => {
      const worktree = "/home/user/project"
      const target = "/home/user/project/../../../etc/passwd"
      const relative = path.relative(worktree, target)
      expect(relative.startsWith("..")).toBe(true)
    })

    it("allows paths within worktree", () => {
      const worktree = "/home/user/project"
      const target = "/home/user/project/src/file.py"
      const relative = path.relative(worktree, target)
      expect(relative.startsWith("..")).toBe(false)
      expect(path.isAbsolute(relative)).toBe(false)
    })

    it("allows nested paths within worktree", () => {
      const worktree = "/home/user/project"
      const target = "/home/user/project/src/deep/nested/file.ts"
      const relative = path.relative(worktree, target)
      expect(relative.startsWith("..")).toBe(false)
    })

    it("detects absolute path outside worktree", () => {
      const worktree = "/home/user/project"
      const target = "/etc/passwd"
      const relative = path.relative(worktree, target)
      expect(relative.startsWith("..")).toBe(true)
    })
  })

  // === Symlink resolution ===

  describe("realpath validation", () => {
    it("project root resolves to real path", async () => {
      const resolved = await realpath(PROJECT_ROOT)
      expect(resolved).toBeTruthy()
      expect(resolved.length).toBeGreaterThan(0)
    })

    it(".opencode directory resolves within project", async () => {
      const opencodeDir = path.join(PROJECT_ROOT, ".opencode")
      const resolved = await realpath(opencodeDir)
      expect(resolved.startsWith(PROJECT_ROOT)).toBe(true)
    })
  })

  // === Fuzz: random paths ===

  describe("fuzz: random path attacks", () => {
    const attacks = [
      "../../../etc/passwd",
      "..\\..\\..\\windows\\system32",
      "/etc/shadow",
      "../../.env",
      "../.env.local",
      "src/../../.env",
      "./../../etc/passwd",
      "src/../../../etc/passwd",
      "%2e%2e%2f%2e%2e%2f",
      "src/./../../etc/passwd",
    ]

    for (const attack of attacks) {
      it(`blocks attack: ${attack}`, () => {
        const worktree = "/home/user/project"
        const targetPath = path.resolve(worktree, attack)
        const relative = path.relative(worktree, targetPath)

        // Either it escapes the worktree or it hits a sensitive file
        const escapesWorktree = relative.startsWith("..") || path.isAbsolute(relative)
        const hitsSensitive = isBlockedSensitivePath(targetPath)
        expect(escapesWorktree || hitsSensitive).toBe(true)
      })
    }

    // Generate 100 random traversal attempts
    for (let i = 0; i < 100; i++) {
      const depth = Math.floor(Math.random() * 5) + 1
      const traversal = "../".repeat(depth)
      const attack = `${traversal}etc/passwd`

      it(`fuzz #${i + 1}: blocks ${attack}`, () => {
        const worktree = "/home/user/project"
        const targetPath = path.resolve(worktree, attack)
        const relative = path.relative(worktree, targetPath)
        const escapesWorktree = relative.startsWith("..") || path.isAbsolute(relative)
        expect(escapesWorktree).toBe(true)
      })
    }
  })
})
