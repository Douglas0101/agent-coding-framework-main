/**
 * golden-trace.ts
 *
 * Golden trace system for verification by trace comparison.
 * Stores expected execution traces and compares actual runs against them.
 *
 * This module is pure TypeScript with no external runtime dependencies.
 */

import { AsyncLock } from './async-lock.js';
import { sanitizeSpecId, sanitizeRunId } from './input-sanitizer.js';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface TraceStep {
  step_id: string;
  node_id: string;
  action: string;
  expected_output?: Record<string, unknown>;
  actual_output?: Record<string, unknown>;
  duration_ms: number;
  status: 'pending' | 'success' | 'failure' | 'skipped';
  error?: string;
}

export interface GoldenTrace {
  trace_id: string;
  spec_id: string;
  name: string;
  description: string;
  version: string;
  created_at: string;
  steps: TraceStep[];
  metadata: Record<string, unknown>;
}

export interface RunTrace {
  run_id: string;
  golden_trace_id: string;
  spec_id: string;
  started_at: string;
  completed_at?: string;
  steps: TraceStep[];
  match_score: number; // 0.0 - 1.0
  mismatches: TraceMismatch[];
}

export interface TraceMismatch {
  step_id: string;
  node_id: string;
  mismatch_type: 'missing_step' | 'extra_step' | 'output_differs' | 'status_differs' | 'duration_anomaly';
  expected: unknown;
  actual: unknown;
  severity: 'warning' | 'error' | 'critical';
  description: string;
}

export interface TraceComparisonResult {
  valid: boolean;
  errors: string[];
  match_score: number;
  mismatches: TraceMismatch[];
  run_trace?: RunTrace;
}

// ---------------------------------------------------------------------------
// In-memory store with concurrency control
// ---------------------------------------------------------------------------

const goldenTraceStore = new Map<string, GoldenTrace>();
const runTraceStore = new Map<string, RunTrace>();
const goldenTraceLock = new AsyncLock();

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Registers a new golden trace for comparison.
 * Thread-safe: uses async lock for concurrent access protection.
 */
export async function registerGoldenTrace(
  spec_id: string,
  name: string,
  description: string,
  version: string,
  steps: TraceStep[],
  metadata: Record<string, unknown> = {},
): Promise<{ valid: boolean; errors: string[]; trace?: GoldenTrace }> {
  const specIdResult = sanitizeSpecId(spec_id);
  if (!specIdResult.valid) {
    return { valid: false, errors: [`Invalid spec_id: ${specIdResult.errors.join(', ')}`] };
  }

  if (!name || name.trim().length === 0) {
    return { valid: false, errors: ['Trace name cannot be empty'] };
  }

  if (!version || !/^\d+\.\d+\.\d+$/.test(version)) {
    return { valid: false, errors: ['Version must be in semver format (x.y.z)'] };
  }

  const release = await goldenTraceLock.acquire();
  try {
    const trace_id = `gt_${specIdResult.sanitized}_${name}_${version}`.toLowerCase();

    // Check for duplicate
    if (goldenTraceStore.has(trace_id)) {
      return {
        valid: false,
        errors: [`Golden trace "${trace_id}" already exists. Use a different version.`],
      };
    }

    const trace: GoldenTrace = {
      trace_id,
      spec_id: specIdResult.sanitized,
      name: name.trim(),
      description: description.trim(),
      version,
      created_at: new Date().toISOString(),
      steps,
      metadata,
    };

    goldenTraceStore.set(trace_id, trace);

    return { valid: true, errors: [], trace };
  } finally {
    release();
  }
}

/**
 * Compares a run trace against a golden trace.
 * Thread-safe: uses async lock for concurrent access protection.
 */
export async function compareAgainstGolden(
  run_id: string,
  golden_trace_id: string,
  spec_id: string,
  actual_steps: TraceStep[],
): Promise<TraceComparisonResult> {
  const runIdResult = sanitizeRunId(run_id);
  const specIdResult = sanitizeSpecId(spec_id);

  if (!runIdResult.valid) {
    return { valid: false, errors: [`Invalid run_id: ${runIdResult.errors.join(', ')}`], match_score: 0, mismatches: [] };
  }

  if (!specIdResult.valid) {
    return { valid: false, errors: [`Invalid spec_id: ${specIdResult.errors.join(', ')}`], match_score: 0, mismatches: [] };
  }

  const release = await goldenTraceLock.acquire();
  try {
    const goldenTrace = goldenTraceStore.get(golden_trace_id);
    if (!goldenTrace) {
      return {
        valid: false,
        errors: [`Golden trace "${golden_trace_id}" not found. Register it first.`],
        match_score: 0,
        mismatches: [],
      };
    }

    const mismatches: TraceMismatch[] = [];

    // Build maps for comparison
    const goldenSteps = new Map(goldenTrace.steps.map((s) => [s.step_id, s]));
    const actualSteps = new Map(actual_steps.map((s) => [s.step_id, s]));

    // Check for missing steps (in golden but not in actual)
    for (const [stepId, goldenStep] of goldenSteps) {
      if (!actualSteps.has(stepId)) {
        mismatches.push({
          step_id: stepId,
          node_id: goldenStep.node_id,
          mismatch_type: 'missing_step',
          expected: 'present',
          actual: 'missing',
          severity: 'error',
          description: `Step "${stepId}" (node: ${goldenStep.node_id}) is expected but not found in actual trace`,
        });
      }
    }

    // Check for extra steps (in actual but not in golden)
    for (const [stepId, actualStep] of actualSteps) {
      if (!goldenSteps.has(stepId)) {
        mismatches.push({
          step_id: stepId,
          node_id: actualStep.node_id,
          mismatch_type: 'extra_step',
          expected: 'absent',
          actual: 'present',
          severity: 'warning',
          description: `Step "${stepId}" (node: ${actualStep.node_id}) is not expected in golden trace`,
        });
      }
    }

    // Compare matching steps
    for (const [stepId, goldenStep] of goldenSteps) {
      const actualStep = actualSteps.get(stepId);
      if (!actualStep) continue;

      // Status comparison
      if (goldenStep.status !== actualStep.status) {
        mismatches.push({
          step_id: stepId,
          node_id: goldenStep.node_id,
          mismatch_type: 'status_differs',
          expected: goldenStep.status,
          actual: actualStep.status,
          severity: actualStep.status === 'failure' ? 'critical' : 'error',
          description: `Step "${stepId}" status differs: expected "${goldenStep.status}", got "${actualStep.status}"`,
        });
      }

      // Output comparison (if both have outputs)
      if (goldenStep.expected_output && actualStep.actual_output) {
        const outputsMatch = JSON.stringify(goldenStep.expected_output) === JSON.stringify(actualStep.actual_output);
        if (!outputsMatch) {
          mismatches.push({
            step_id: stepId,
            node_id: goldenStep.node_id,
            mismatch_type: 'output_differs',
            expected: goldenStep.expected_output,
            actual: actualStep.actual_output,
            severity: 'error',
            description: `Step "${stepId}" output differs from expected`,
          });
        }
      }

      // Duration anomaly detection (> 3x golden duration)
      if (goldenStep.duration_ms > 0 && actualStep.duration_ms > goldenStep.duration_ms * 3) {
        mismatches.push({
          step_id: stepId,
          node_id: goldenStep.node_id,
          mismatch_type: 'duration_anomaly',
          expected: `${goldenStep.duration_ms}ms`,
          actual: `${actualStep.duration_ms}ms`,
          severity: 'warning',
          description: `Step "${stepId}" duration (${actualStep.duration_ms}ms) is more than 3x the golden trace duration (${goldenStep.duration_ms}ms)`,
        });
      }
    }

    // Calculate match score
    const totalSteps = goldenTrace.steps.length;
    const matchingSteps = totalSteps - mismatches.filter((m) => m.mismatch_type === 'missing_step').length;
    const matchScore = totalSteps > 0 ? Math.round((matchingSteps / totalSteps) * 1000) / 1000 : 1;

    const runTrace: RunTrace = {
      run_id: runIdResult.sanitized,
      golden_trace_id,
      spec_id: specIdResult.sanitized,
      started_at: new Date().toISOString(),
      steps: actual_steps,
      match_score: matchScore,
      mismatches,
    };

    runTraceStore.set(runIdResult.sanitized, runTrace);

    return {
      valid: mismatches.filter((m) => m.severity === 'critical' || m.severity === 'error').length === 0,
      errors: mismatches.filter((m) => m.severity === 'critical' || m.severity === 'error').map((m) => m.description),
      match_score: matchScore,
      mismatches,
      run_trace: runTrace,
    };
  } finally {
    release();
  }
}

/**
 * Gets a golden trace by ID.
 */
export function getGoldenTrace(trace_id: string): GoldenTrace | undefined {
  return goldenTraceStore.get(trace_id);
}

/**
 * Lists all golden traces, optionally filtered by spec_id.
 */
export function listGoldenTraces(filter?: { spec_id?: string }): GoldenTrace[] {
  const all = Array.from(goldenTraceStore.values());
  if (filter?.spec_id) {
    const specIdResult = sanitizeSpecId(filter.spec_id);
    if (!specIdResult.valid) {
      return [];
    }
    return all.filter((t) => t.spec_id === specIdResult.sanitized);
  }
  return all;
}

/**
 * Gets a run trace by run_id.
 */
export function getRunTrace(run_id: string): RunTrace | undefined {
  const runIdResult = sanitizeRunId(run_id);
  if (!runIdResult.valid) {
    return undefined;
  }
  return runTraceStore.get(runIdResult.sanitized);
}

/**
 * Clears the golden trace stores. Intended for testing only.
 * PRODUCTION GUARD: Blocked when NODE_ENV is 'production' or when ALLOW_CLEAR is not set.
 */
export function _clearGoldenTraces(): void {
  if (process.env.NODE_ENV === 'production' && process.env.ALLOW_CLEAR !== '1') {
    throw new Error(
      '_clearGoldenTraces is blocked in production. Set ALLOW_CLEAR=1 to override (testing only).',
    );
  }
  goldenTraceStore.clear();
  runTraceStore.clear();
}

/**
 * Export lock metrics for monitoring (read-only).
 */
export function getGoldenTraceLockMetrics(): { isLocked: boolean; queueLength: number } {
  return {
    isLocked: goldenTraceLock.isLocked,
    queueLength: goldenTraceLock.queueLength,
  };
}
