/**
 * heartbeat-monitor.ts
 *
 * Liveness monitoring for DAG node execution.
 * Tracks heartbeat signals and detects unresponsive nodes.
 *
 * This module is pure TypeScript with no external runtime dependencies.
 */

import { AsyncLock } from './async-lock.js';
import { sanitizeRunId, sanitizeSpecId } from './input-sanitizer.js';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type HeartbeatStatus = 'healthy' | 'stale' | 'dead';

export interface HeartbeatEntry {
  node_id: string;
  spec_id: string;
  run_id: string;
  last_heartbeat: string; // ISO 8601
  heartbeat_count: number;
  status: HeartbeatStatus;
  metadata: Record<string, unknown>;
}

export interface HeartbeatConfig {
  interval_ms: number; // Expected heartbeat interval (default: 30000ms = 30s)
  stale_threshold_ms: number; // Time before marking as stale (default: 2x interval)
  dead_threshold_ms: number; // Time before marking as dead (default: 5x interval)
}

export interface HeartbeatResult {
  valid: boolean;
  errors: string[];
  entry?: HeartbeatEntry;
}

export interface StaleNodesResult {
  stale: string[]; // node_ids
  dead: string[]; // node_ids
  healthy_count: number;
}

// ---------------------------------------------------------------------------
// In-memory store with concurrency control
// ---------------------------------------------------------------------------

const heartbeatStore = new Map<string, HeartbeatEntry>();
const heartbeatLock = new AsyncLock();

const DEFAULT_CONFIG: HeartbeatConfig = {
  interval_ms: 30000,
  stale_threshold_ms: 60000,
  dead_threshold_ms: 150000,
};

function heartbeatKey(spec_id: string, run_id: string, node_id: string): string {
  return `${spec_id}::${run_id}::${node_id}`;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Records a heartbeat signal for a node.
 * Thread-safe: uses async lock for concurrent access protection.
 */
export async function recordHeartbeat(
  spec_id: string,
  run_id: string,
  node_id: string,
  metadata: Record<string, unknown> = {},
  config: Partial<HeartbeatConfig> = {},
): Promise<HeartbeatResult> {
  // Input sanitization
  const specIdResult = sanitizeSpecId(spec_id);
  if (!specIdResult.valid) {
    return { valid: false, errors: [`Invalid spec_id: ${specIdResult.errors.join(', ')}`] };
  }

  const runIdResult = sanitizeRunId(run_id);
  if (!runIdResult.valid) {
    return { valid: false, errors: [`Invalid run_id: ${runIdResult.errors.join(', ')}`] };
  }

  const release = await heartbeatLock.acquire();
  try {
    const key = heartbeatKey(specIdResult.sanitized, runIdResult.sanitized, node_id);
    const now = new Date().toISOString();

    const existing = heartbeatStore.get(key);
    const entry: HeartbeatEntry = {
      node_id,
      spec_id: specIdResult.sanitized,
      run_id: runIdResult.sanitized,
      last_heartbeat: now,
      heartbeat_count: existing ? existing.heartbeat_count + 1 : 1,
      status: 'healthy',
      metadata: { ...existing?.metadata, ...metadata },
    };

    heartbeatStore.set(key, entry);

    return { valid: true, errors: [], entry };
  } finally {
    release();
  }
}

/**
 * Checks the status of all heartbeats and identifies stale/dead nodes.
 * Thread-safe: uses async lock for concurrent access protection.
 */
export async function checkHeartbeats(
  config: Partial<HeartbeatConfig> = {},
): Promise<StaleNodesResult> {
  const effectiveConfig = { ...DEFAULT_CONFIG, ...config };
  const now = Date.now();

  const release = await heartbeatLock.acquire();
  try {
    const stale: string[] = [];
    const dead: string[] = [];
    let healthyCount = 0;

    for (const [key, entry] of heartbeatStore.entries()) {
      const lastHeartbeatTime = new Date(entry.last_heartbeat).getTime();
      const elapsed = now - lastHeartbeatTime;

      if (elapsed > effectiveConfig.dead_threshold_ms) {
        entry.status = 'dead';
        dead.push(key);
      } else if (elapsed > effectiveConfig.stale_threshold_ms) {
        entry.status = 'stale';
        stale.push(key);
      } else {
        entry.status = 'healthy';
        healthyCount++;
      }
    }

    return {
      stale,
      dead,
      healthy_count: healthyCount,
    };
  } finally {
    release();
  }
}

/**
 * Gets the heartbeat entry for a specific node.
 */
export async function getHeartbeat(
  spec_id: string,
  run_id: string,
  node_id: string,
): Promise<HeartbeatEntry | undefined> {
  const specIdResult = sanitizeSpecId(spec_id);
  const runIdResult = sanitizeRunId(run_id);

  if (!specIdResult.valid || !runIdResult.valid) {
    return undefined;
  }

  const key = heartbeatKey(specIdResult.sanitized, runIdResult.sanitized, node_id);
  return heartbeatStore.get(key);
}

/**
 * Lists all heartbeat entries, optionally filtered by spec_id or run_id.
 */
export function listHeartbeats(filter?: { spec_id?: string; run_id?: string }): HeartbeatEntry[] {
  const all = Array.from(heartbeatStore.values());
  if (filter?.spec_id) {
    const specIdResult = sanitizeSpecId(filter.spec_id);
    if (!specIdResult.valid) {
      return [];
    }
    return all.filter((h) => h.spec_id === specIdResult.sanitized);
  }
  if (filter?.run_id) {
    const runIdResult = sanitizeRunId(filter.run_id);
    if (!runIdResult.valid) {
      return [];
    }
    return all.filter((h) => h.run_id === runIdResult.sanitized);
  }
  return all;
}

/**
 * Clears the heartbeat store. Intended for testing only.
 * PRODUCTION GUARD: Blocked when NODE_ENV is 'production' or when ALLOW_CLEAR is not set.
 */
export function _clearHeartbeats(): void {
  if (process.env.NODE_ENV === 'production' && process.env.ALLOW_CLEAR !== '1') {
    throw new Error(
      '_clearHeartbeats is blocked in production. Set ALLOW_CLEAR=1 to override (testing only).',
    );
  }
  heartbeatStore.clear();
}

/**
 * Export lock metrics for monitoring (read-only).
 */
export function getHeartbeatLockMetrics(): { isLocked: boolean; queueLength: number } {
  return {
    isLocked: heartbeatLock.isLocked,
    queueLength: heartbeatLock.queueLength,
  };
}
