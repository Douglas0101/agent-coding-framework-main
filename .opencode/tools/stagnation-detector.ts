/**
 * stagnation-detector.ts
 *
 * Detects when execution is stuck (no progress over time).
 * Monitors node state changes and triggers alerts when stagnation is detected.
 *
 * This module is pure TypeScript with no external runtime dependencies.
 */

import { AsyncLock } from './async-lock.js';
import { clearBlockedMessage, isClearAllowed } from './clear-guard.js';
import { sanitizeRunId, sanitizeSpecId } from './input-sanitizer.js';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type StagnationSeverity = 'warning' | 'error' | 'critical';

export interface StagnationEvent {
  event_id: string;
  spec_id: string;
  run_id: string;
  dag_id: string;
  node_id: string;
  severity: StagnationSeverity;
  detected_at: string;
  last_progress_at: string;
  stagnation_duration_ms: number;
  description: string;
  recommendation: string;
}

export interface ProgressRecord {
  node_id: string;
  last_progress_at: string;
  progress_count: number;
  state_changes: Array<{
    from: string;
    to: string;
    timestamp: string;
  }>;
}

export interface StagnationConfig {
  warning_threshold_ms: number; // Default: 60000 (1 minute)
  error_threshold_ms: number; // Default: 180000 (3 minutes)
  critical_threshold_ms: number; // Default: 300000 (5 minutes)
}

export interface StagnationResult {
  detected: boolean;
  events: StagnationEvent[];
  healthy_nodes: string[];
}

// ---------------------------------------------------------------------------
// In-memory store with concurrency control
// ---------------------------------------------------------------------------

const progressStore = new Map<string, ProgressRecord>();
const stagnationEvents: StagnationEvent[] = [];
const stagnationLock = new AsyncLock();

const DEFAULT_CONFIG: StagnationConfig = {
  warning_threshold_ms: 60000,
  error_threshold_ms: 180000,
  critical_threshold_ms: 300000,
};

function progressKey(spec_id: string, run_id: string, dag_id: string, node_id: string): string {
  return `${spec_id}::${run_id}::${dag_id}::${node_id}`;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Records a progress event for a node.
 * Thread-safe: uses async lock for concurrent access protection.
 */
export async function recordProgress(
  spec_id: string,
  run_id: string,
  dag_id: string,
  node_id: string,
  from_state: string,
  to_state: string,
): Promise<void> {
  const specIdResult = sanitizeSpecId(spec_id);
  const runIdResult = sanitizeRunId(run_id);

  if (!specIdResult.valid || !runIdResult.valid) {
    return;
  }

  const release = await stagnationLock.acquire();
  try {
    const key = progressKey(specIdResult.sanitized, runIdResult.sanitized, dag_id, node_id);
    const now = new Date().toISOString();

    const existing = progressStore.get(key);
    const record: ProgressRecord = {
      node_id,
      last_progress_at: now,
      progress_count: existing ? existing.progress_count + 1 : 1,
      state_changes: [
        ...(existing?.state_changes ?? []),
        { from: from_state, to: to_state, timestamp: now },
      ],
    };

    progressStore.set(key, record);
  } finally {
    release();
  }
}

/**
 * Checks for stagnation across all monitored nodes.
 * Thread-safe: uses async lock for concurrent access protection.
 */
export async function checkStagnation(
  spec_id: string,
  run_id: string,
  dag_id: string,
  node_ids: string[],
  config: Partial<StagnationConfig> = {},
): Promise<StagnationResult> {
  const specIdResult = sanitizeSpecId(spec_id);
  const runIdResult = sanitizeRunId(run_id);

  if (!specIdResult.valid || !runIdResult.valid) {
    return { detected: false, events: [], healthy_nodes: [] };
  }

  const effectiveConfig = { ...DEFAULT_CONFIG, ...config };
  const now = Date.now();
  const events: StagnationEvent[] = [];
  const healthyNodes: string[] = [];

  const release = await stagnationLock.acquire();
  try {
    for (const nodeId of node_ids) {
      const key = progressKey(specIdResult.sanitized, runIdResult.sanitized, dag_id, nodeId);
      const record = progressStore.get(key);

      if (!record) {
        // No progress recorded yet - could be initial state
        continue;
      }

      const lastProgressTime = new Date(record.last_progress_at).getTime();
      const elapsed = now - lastProgressTime;

      if (elapsed > effectiveConfig.critical_threshold_ms) {
        const event: StagnationEvent = {
          event_id: `stagnation_${specIdResult.sanitized}_${runIdResult.sanitized}_${dag_id}_${nodeId}_${Date.now()}`,
          spec_id: specIdResult.sanitized,
          run_id: runIdResult.sanitized,
          dag_id,
          node_id: nodeId,
          severity: 'critical',
          detected_at: new Date().toISOString(),
          last_progress_at: record.last_progress_at,
          stagnation_duration_ms: elapsed,
          description: `Node "${nodeId}" has not made progress for ${Math.round(elapsed / 1000)}s (critical threshold: ${Math.round(effectiveConfig.critical_threshold_ms / 1000)}s)`,
          recommendation: 'Consider aborting the run or restarting from the last checkpoint.',
        };
        events.push(event);
        stagnationEvents.push(event);
      } else if (elapsed > effectiveConfig.error_threshold_ms) {
        const event: StagnationEvent = {
          event_id: `stagnation_${specIdResult.sanitized}_${runIdResult.sanitized}_${dag_id}_${nodeId}_${Date.now()}`,
          spec_id: specIdResult.sanitized,
          run_id: runIdResult.sanitized,
          dag_id,
          node_id: nodeId,
          severity: 'error',
          detected_at: new Date().toISOString(),
          last_progress_at: record.last_progress_at,
          stagnation_duration_ms: elapsed,
          description: `Node "${nodeId}" has not made progress for ${Math.round(elapsed / 1000)}s (error threshold: ${Math.round(effectiveConfig.error_threshold_ms / 1000)}s)`,
          recommendation: 'Monitor closely. Consider retrying the node if no progress is made soon.',
        };
        events.push(event);
        stagnationEvents.push(event);
      } else if (elapsed > effectiveConfig.warning_threshold_ms) {
        const event: StagnationEvent = {
          event_id: `stagnation_${specIdResult.sanitized}_${runIdResult.sanitized}_${dag_id}_${nodeId}_${Date.now()}`,
          spec_id: specIdResult.sanitized,
          run_id: runIdResult.sanitized,
          dag_id,
          node_id: nodeId,
          severity: 'warning',
          detected_at: new Date().toISOString(),
          last_progress_at: record.last_progress_at,
          stagnation_duration_ms: elapsed,
          description: `Node "${nodeId}" has not made progress for ${Math.round(elapsed / 1000)}s (warning threshold: ${Math.round(effectiveConfig.warning_threshold_ms / 1000)}s)`,
          recommendation: 'Continue monitoring. This may be normal for long-running operations.',
        };
        events.push(event);
        stagnationEvents.push(event);
      } else {
        healthyNodes.push(nodeId);
      }
    }

    return {
      detected: events.length > 0,
      events,
      healthy_nodes: healthyNodes,
    };
  } finally {
    release();
  }
}

/**
 * Gets all stagnation events for a specific run.
 */
export function getStagnationEvents(spec_id: string, run_id: string): StagnationEvent[] {
  const specIdResult = sanitizeSpecId(spec_id);
  const runIdResult = sanitizeRunId(run_id);

  if (!specIdResult.valid || !runIdResult.valid) {
    return [];
  }

  return stagnationEvents.filter(
    (e) => e.spec_id === specIdResult.sanitized && e.run_id === runIdResult.sanitized,
  );
}

/**
 * Clears the stagnation detector state. Intended for testing only.
 * PRODUCTION GUARD: Blocked when NODE_ENV is 'production' or when ALLOW_CLEAR is not set.
 */
export function _clearStagnationState(): void {
  if (!isClearAllowed()) {
    throw new Error(clearBlockedMessage('_clearStagnationState'));
  }
  progressStore.clear();
  stagnationEvents.length = 0;
}

/**
 * Export lock metrics for monitoring (read-only).
 */
export function getStagnationLockMetrics(): { isLocked: boolean; queueLength: number } {
  return {
    isLocked: stagnationLock.isLocked,
    queueLength: stagnationLock.queueLength,
  };
}
