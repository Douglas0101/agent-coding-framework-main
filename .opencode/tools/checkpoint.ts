/**
 * checkpoint.ts
 *
 * Checkpoint/resume system for DAG node execution.
 * Enables reentrant execution by saving and restoring node state.
 *
 * This module is pure TypeScript with no external runtime dependencies.
 * Persistence is in-memory by default, with optional filesystem hooks.
 */

import { AsyncLock } from './async-lock.js';
import { sanitizeRunId, sanitizeSpecId } from './input-sanitizer.js';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type CheckpointStatus = 'pending' | 'running' | 'completed' | 'failed' | 'retried';

export interface CheckpointNodeState {
  node_id: string;
  status: CheckpointStatus;
  started_at: string;
  completed_at?: string;
  attempt: number;
  max_attempts: number;
  error?: string;
  output?: Record<string, unknown>;
  budget_used: {
    tokens: number;
    cost_usd: number;
    time_ms: number;
  };
}

export interface CheckpointEntry {
  checkpoint_id: string;
  spec_id: string;
  run_id: string;
  dag_id: string;
  created_at: string;
  updated_at: string;
  nodes: Record<string, CheckpointNodeState>;
  metadata: Record<string, unknown>;
}

export interface CheckpointResult {
  valid: boolean;
  errors: string[];
  checkpoint?: CheckpointEntry;
}

export interface ResumeResult {
  can_resume: boolean;
  errors: string[];
  resume_from: string[]; // node_ids to resume from
  checkpoint?: CheckpointEntry;
}

// ---------------------------------------------------------------------------
// In-memory store with concurrency control
// ---------------------------------------------------------------------------

const checkpointStore = new Map<string, CheckpointEntry>();
const checkpointLock = new AsyncLock();

function checkpointKey(spec_id: string, run_id: string, dag_id: string): string {
  return `${spec_id}::${run_id}::${dag_id}`;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Creates a new checkpoint for a DAG execution.
 * Thread-safe: uses async lock for concurrent access protection.
 */
export async function createCheckpoint(
  spec_id: string,
  run_id: string,
  dag_id: string,
  node_ids: string[],
  metadata: Record<string, unknown> = {},
): Promise<CheckpointResult> {
  // Input sanitization
  const specIdResult = sanitizeSpecId(spec_id);
  if (!specIdResult.valid) {
    return { valid: false, errors: [`Invalid spec_id: ${specIdResult.errors.join(', ')}`] };
  }

  const runIdResult = sanitizeRunId(run_id);
  if (!runIdResult.valid) {
    return { valid: false, errors: [`Invalid run_id: ${runIdResult.errors.join(', ')}`] };
  }

  const release = await checkpointLock.acquire();
  try {
    const key = checkpointKey(specIdResult.sanitized, runIdResult.sanitized, dag_id);

    // Check if checkpoint already exists
    if (checkpointStore.has(key)) {
      return {
        valid: false,
        errors: [`Checkpoint already exists for spec="${specIdResult.sanitized}" run="${runIdResult.sanitized}" dag="${dag_id}". Use updateCheckpoint instead.`],
      };
    }

    const now = new Date().toISOString();
    const nodes: Record<string, CheckpointNodeState> = {};
    for (const nodeId of node_ids) {
      nodes[nodeId] = {
        node_id: nodeId,
        status: 'pending',
        started_at: now,
        attempt: 0,
        max_attempts: 3,
        budget_used: { tokens: 0, cost_usd: 0, time_ms: 0 },
      };
    }

    const checkpoint: CheckpointEntry = {
      checkpoint_id: `cp_${specIdResult.sanitized}_${runIdResult.sanitized}_${dag_id}_${Date.now()}`,
      spec_id: specIdResult.sanitized,
      run_id: runIdResult.sanitized,
      dag_id,
      created_at: now,
      updated_at: now,
      nodes,
      metadata,
    };

    checkpointStore.set(key, checkpoint);

    return { valid: true, errors: [], checkpoint };
  } finally {
    release();
  }
}

/**
 * Updates the state of a specific node in the checkpoint.
 * Thread-safe: uses async lock for concurrent access protection.
 */
export async function updateNodeState(
  spec_id: string,
  run_id: string,
  dag_id: string,
  node_id: string,
  state: Partial<CheckpointNodeState>,
): Promise<CheckpointResult> {
  const specIdResult = sanitizeSpecId(spec_id);
  if (!specIdResult.valid) {
    return { valid: false, errors: [`Invalid spec_id: ${specIdResult.errors.join(', ')}`] };
  }

  const runIdResult = sanitizeRunId(run_id);
  if (!runIdResult.valid) {
    return { valid: false, errors: [`Invalid run_id: ${runIdResult.errors.join(', ')}`] };
  }

  const release = await checkpointLock.acquire();
  try {
    const key = checkpointKey(specIdResult.sanitized, runIdResult.sanitized, dag_id);
    const checkpoint = checkpointStore.get(key);

    if (!checkpoint) {
      return {
        valid: false,
        errors: [`No checkpoint found for spec="${specIdResult.sanitized}" run="${runIdResult.sanitized}" dag="${dag_id}". Create a checkpoint first.`],
      };
    }

    const node = checkpoint.nodes[node_id];
    if (!node) {
      return {
        valid: false,
        errors: [`Node "${node_id}" not found in checkpoint. Available nodes: ${Object.keys(checkpoint.nodes).join(', ')}`],
      };
    }

    // Update node state
    Object.assign(node, state, {
      updated_at: new Date().toISOString(),
    });

    // Update checkpoint timestamp
    checkpoint.updated_at = new Date().toISOString();

    return { valid: true, errors: [], checkpoint };
  } finally {
    release();
  }
}

/**
 * Resumes execution from a checkpoint.
 * Returns the list of nodes that need to be re-executed.
 * Thread-safe: uses async lock for concurrent access protection.
 */
export async function resumeFromCheckpoint(
  spec_id: string,
  run_id: string,
  dag_id: string,
): Promise<ResumeResult> {
  const specIdResult = sanitizeSpecId(spec_id);
  if (!specIdResult.valid) {
    return { can_resume: false, errors: [`Invalid spec_id: ${specIdResult.errors.join(', ')}`], resume_from: [] };
  }

  const runIdResult = sanitizeRunId(run_id);
  if (!runIdResult.valid) {
    return { can_resume: false, errors: [`Invalid run_id: ${runIdResult.errors.join(', ')}`], resume_from: [] };
  }

  const release = await checkpointLock.acquire();
  try {
    const key = checkpointKey(specIdResult.sanitized, runIdResult.sanitized, dag_id);
    const checkpoint = checkpointStore.get(key);

    if (!checkpoint) {
      return {
        can_resume: false,
        errors: [`No checkpoint found for spec="${specIdResult.sanitized}" run="${runIdResult.sanitized}" dag="${dag_id}".`],
        resume_from: [],
      };
    }

    // Find nodes that need to be resumed (not completed)
    const resumeFrom: string[] = [];
    for (const [nodeId, nodeState] of Object.entries(checkpoint.nodes)) {
      if (nodeState.status !== 'completed') {
        resumeFrom.push(nodeId);
      }
    }

    if (resumeFrom.length === 0) {
      return {
        can_resume: false,
        errors: ['All nodes are already completed. Nothing to resume.'],
        resume_from: [],
        checkpoint,
      };
    }

    return {
      can_resume: true,
      errors: [],
      resume_from: resumeFrom,
      checkpoint,
    };
  } finally {
    release();
  }
}

/**
 * Retrieves a checkpoint by spec_id, run_id, and dag_id.
 */
export async function getCheckpoint(
  spec_id: string,
  run_id: string,
  dag_id: string,
): Promise<CheckpointEntry | undefined> {
  const specIdResult = sanitizeSpecId(spec_id);
  const runIdResult = sanitizeRunId(run_id);

  if (!specIdResult.valid || !runIdResult.valid) {
    return undefined;
  }

  const key = checkpointKey(specIdResult.sanitized, runIdResult.sanitized, dag_id);
  return checkpointStore.get(key);
}

/**
 * Lists all checkpoints, optionally filtered by spec_id.
 */
export function listCheckpoints(filter?: { spec_id?: string }): CheckpointEntry[] {
  const all = Array.from(checkpointStore.values());
  if (filter?.spec_id) {
    const specIdResult = sanitizeSpecId(filter.spec_id);
    if (!specIdResult.valid) {
      return [];
    }
    return all.filter((c) => c.spec_id === specIdResult.sanitized);
  }
  return all;
}

/**
 * Clears the checkpoint store. Intended for testing only.
 * PRODUCTION GUARD: Blocked when NODE_ENV is 'production' or when ALLOW_CLEAR is not set.
 */
export function _clearCheckpoints(): void {
  if (process.env.NODE_ENV === 'production' && process.env.ALLOW_CLEAR !== '1') {
    throw new Error(
      '_clearCheckpoints is blocked in production. Set ALLOW_CLEAR=1 to override (testing only).',
    );
  }
  checkpointStore.clear();
}

/**
 * Export lock metrics for monitoring (read-only).
 */
export function getCheckpointLockMetrics(): { isLocked: boolean; queueLength: number } {
  return {
    isLocked: checkpointLock.isLocked,
    queueLength: checkpointLock.queueLength,
  };
}
