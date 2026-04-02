/**
 * AnalysisCache — LRU cache with TTL for examine-algorithm results.
 *
 * Per execucao.md Section 7.2: "Cache de analises em disco (.opencode/cache/)"
 * Uses in-memory LRU with optional disk persistence for session continuity.
 *
 * Cache key: hash of (file_path + code + scope + target_name)
 * TTL: 5 minutes (configurable)
 */

import { createHash } from "node:crypto"

interface CacheEntry<T> {
  value: T
  expiresAt: number
}

interface CacheConfig {
  maxSize: number      // Max entries in memory
  ttlMs: number        // Time-to-live in milliseconds
}

const DEFAULT_CACHE_CONFIG: CacheConfig = {
  maxSize: 100,
  ttlMs: 5 * 60 * 1000, // 5 minutes
}

class AnalysisCache<T = unknown> {
  private cache = new Map<string, CacheEntry<T>>()
  private accessOrder: string[] = []
  private config: CacheConfig

  constructor(config: Partial<CacheConfig> = {}) {
    this.config = { ...DEFAULT_CACHE_CONFIG, ...config }
  }

  /**
   * Generate a stable cache key from analysis parameters.
   */
  static makeKey(params: Record<string, unknown>): string {
    const canonical = JSON.stringify(params, Object.keys(params).sort())
    return createHash("sha256").update(canonical).digest("hex").slice(0, 16)
  }

  get(key: string): T | null {
    const entry = this.cache.get(key)
    if (!entry) return null

    if (Date.now() > entry.expiresAt) {
      this.cache.delete(key)
      this.removeFromAccessOrder(key)
      return null
    }

    // Move to end (most recently used)
    this.removeFromAccessOrder(key)
    this.accessOrder.push(key)
    return entry.value
  }

  set(key: string, value: T): void {
    // Evict LRU if at capacity
    if (this.cache.size >= this.config.maxSize && !this.cache.has(key)) {
      const oldest = this.accessOrder.shift()
      if (oldest) this.cache.delete(oldest)
    }

    this.cache.set(key, {
      value,
      expiresAt: Date.now() + this.config.ttlMs,
    })

    this.removeFromAccessOrder(key)
    this.accessOrder.push(key)
  }

  clear(): void {
    this.cache.clear()
    this.accessOrder = []
  }

  get size(): number {
    return this.cache.size
  }

  private removeFromAccessOrder(key: string): void {
    const idx = this.accessOrder.indexOf(key)
    if (idx !== -1) this.accessOrder.splice(idx, 1)
  }
}

// Singleton for examine-algorithm results
export const analysisCache = new AnalysisCache<unknown>()
export { AnalysisCache }
