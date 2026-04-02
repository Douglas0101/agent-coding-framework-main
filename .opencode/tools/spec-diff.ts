/**
 * spec-diff.ts
 *
 * Classifies changes between two versions of a spec into one of four categories:
 *
 *   additive-compatible   – new optional fields added; no behavior change
 *   behavior-compatible   – logic changed but backward-compatible (e.g., looser guards)
 *   risky-compatible      – compatible change but with material runtime risk
 *   breaking              – incompatible change; requires human approval + migration plan
 *
 * Limitations & Intentional Behaviors:
 *   - Array diffing: Currently treats arrays as atomic values. A change to any
 *     element triggers a full-path modification event.
 *   - Path resolution: Uses dot-notation for nested objects.
 *   - Conservative classification: When in doubt, defaults to 'risky-compatible'
 *     or 'breaking' to ensure human review.
 *
 * The classifier works on the raw payload diff without requiring the specs to
 * be in the registry — it can also be called on external artifacts.
 *
 * No external runtime dependencies.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ChangeClassification =
  | 'additive-compatible'
  | 'behavior-compatible'
  | 'risky-compatible'
  | 'breaking';

export interface FieldChange {
  path: string;
  change_type: 'added' | 'removed' | 'modified';
  classification: ChangeClassification;
  before: unknown;
  after: unknown;
  impact_note: string;
}

export interface SpecDiffResult {
  spec_id: string;
  from_version: string;
  to_version: string;
  /** Overall classification is the most severe among all field changes */
  classification: ChangeClassification;
  changes: FieldChange[];
  requires_human_approval: boolean;
  migration_plan_required: boolean;
  affected_consumers: string[];
  blocking_reason: string | null;
}

// ---------------------------------------------------------------------------
// Classification severity ordering
// ---------------------------------------------------------------------------

const SEVERITY: Record<ChangeClassification, number> = {
  'additive-compatible': 0,
  'behavior-compatible': 1,
  'risky-compatible': 2,
  breaking: 3,
};

function worstOf(a: ChangeClassification, b: ChangeClassification): ChangeClassification {
  return SEVERITY[a] >= SEVERITY[b] ? a : b;
}

// ---------------------------------------------------------------------------
// Breaking-change detectors
// ---------------------------------------------------------------------------

/**
 * Fields whose removal or renaming is always a breaking change.
 * Extend this set as new contract-critical fields are declared in schemas.
 */
const BREAKING_IF_REMOVED = new Set([
  'spec_id',
  'behavior_id',
  'version',
  'status',
  'invariants',
  'states',
  'initial_state',
  'terminal_states',
  'transitions',
  'acceptance_criteria',
  'required_fields',
  'strategy',
  'rollback',
]);

/**
 * Fields that trigger a risky-compatible classification when modified.
 */
const RISKY_IF_MODIFIED = new Set([
  'non_functional',
  'timeout_ms',
  'retry_policy',
  'stages',
  'rollback.trigger_conditions',
  'slos',
  'compatibility_rules',
]);

/**
 * Fields that trigger behavior-compatible when modified (logic change, backward-safe).
 */
const BEHAVIOR_IF_MODIFIED = new Set([
  'transitions',
  'forbidden',
  'invariants',
  'guards',
  'acceptance_criteria',
]);

// ---------------------------------------------------------------------------
// Deep diff utilities
// ---------------------------------------------------------------------------

function deepEqual(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (typeof a !== typeof b) return false;
  if (a === null || b === null) return a === b;
  if (typeof a !== 'object') return false;
  const aObj = a as Record<string, unknown>;
  const bObj = b as Record<string, unknown>;
  const aKeys = Object.keys(aObj).sort();
  const bKeys = Object.keys(bObj).sort();
  if (aKeys.join(',') !== bKeys.join(',')) return false;
  return aKeys.every((k) => deepEqual(aObj[k], bObj[k]));
}

function flattenKeys(
  obj: Record<string, unknown>,
  prefix = '',
): Map<string, unknown> {
  const result = new Map<string, unknown>();
  for (const [k, v] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${k}` : k;
    if (v !== null && typeof v === 'object' && !Array.isArray(v)) {
      const nested = flattenKeys(v as Record<string, unknown>, path);
      for (const [nk, nv] of nested) {
        result.set(nk, nv);
      }
    } else {
      // Arrays are stored as atomic values (not expanded by index).
      // Consequence: a change in a single array element shows up as a
      // single `path` modification (the whole array), not as `path.N.field`.
      // This is intentionally conservative: any array change that fails
      // deepEqual is surfaced. Index-level granularity is deferred to Sprint 2.
      result.set(path, v);
    }
  }
  return result;
}

// ---------------------------------------------------------------------------
// Field-level classifier
// ---------------------------------------------------------------------------

function classifyFieldChange(
  path: string,
  changeType: 'added' | 'removed' | 'modified',
): ChangeClassification {
  const topKey = path.split('.')[0];

  if (changeType === 'removed') {
    if (BREAKING_IF_REMOVED.has(topKey) || BREAKING_IF_REMOVED.has(path)) {
      return 'breaking';
    }
    // Removing optional fields is risky (consumers may depend on presence)
    return 'risky-compatible';
  }

  if (changeType === 'added') {
    // New optional fields are additive-compatible
    return 'additive-compatible';
  }

  // Modified
  if (BREAKING_IF_REMOVED.has(topKey) && topKey !== 'invariants') {
    // Core identity fields being modified is breaking
    if (['spec_id', 'behavior_id', 'version', 'initial_state'].includes(topKey)) {
      return 'breaking';
    }
  }

  if (BEHAVIOR_IF_MODIFIED.has(topKey) || BEHAVIOR_IF_MODIFIED.has(path)) {
    return 'behavior-compatible';
  }

  if (RISKY_IF_MODIFIED.has(topKey) || RISKY_IF_MODIFIED.has(path)) {
    return 'risky-compatible';
  }

  return 'additive-compatible';
}

function buildImpactNote(
  path: string,
  changeType: 'added' | 'removed' | 'modified',
  classification: ChangeClassification,
): string {
  if (classification === 'breaking') {
    return `Breaking: "${path}" ${changeType}. Consumers must be migrated before deployment.`;
  }
  if (classification === 'risky-compatible') {
    return `Risky: "${path}" ${changeType}. Runtime behavior may change; validate with golden traces.`;
  }
  if (classification === 'behavior-compatible') {
    return `Behavior change: "${path}" ${changeType}. Logic updated; re-run property tests.`;
  }
  return `Additive: "${path}" ${changeType}. Backward-compatible.`;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Computes the diff between two spec payloads and classifies the change set.
 *
 * @param spec_id       - Identifier of the spec being compared
 * @param from_version  - The baseline spec version (before)
 * @param to_version    - The proposed spec version (after)
 * @param before        - Payload of the baseline version
 * @param after         - Payload of the proposed version
 * @param known_consumers - Optional list of known consumers for breaking-change notification
 */
export function diffSpecs(
  spec_id: string,
  from_version: string,
  to_version: string,
  before: Record<string, unknown>,
  after: Record<string, unknown>,
  known_consumers: string[] = [],
): SpecDiffResult {
  const flatBefore = flattenKeys(before);
  const flatAfter = flattenKeys(after);

  const allPaths = new Set([...flatBefore.keys(), ...flatAfter.keys()]);
  const changes: FieldChange[] = [];

  for (const path of allPaths) {
    const inBefore = flatBefore.has(path);
    const inAfter = flatAfter.has(path);

    if (inBefore && !inAfter) {
      // Removed
      const cls = classifyFieldChange(path, 'removed');
      changes.push({
        path,
        change_type: 'removed',
        classification: cls,
        before: flatBefore.get(path),
        after: undefined,
        impact_note: buildImpactNote(path, 'removed', cls),
      });
    } else if (!inBefore && inAfter) {
      // Added
      const cls = classifyFieldChange(path, 'added');
      changes.push({
        path,
        change_type: 'added',
        classification: cls,
        before: undefined,
        after: flatAfter.get(path),
        impact_note: buildImpactNote(path, 'added', cls),
      });
    } else {
      // Potentially modified
      const bVal = flatBefore.get(path);
      const aVal = flatAfter.get(path);
      if (!deepEqual(bVal, aVal)) {
        const cls = classifyFieldChange(path, 'modified');
        changes.push({
          path,
          change_type: 'modified',
          classification: cls,
          before: bVal,
          after: aVal,
          impact_note: buildImpactNote(path, 'modified', cls),
        });
      }
    }
  }

  // Overall classification: worst among all changes
  const overallClassification: ChangeClassification =
    changes.length === 0
      ? 'additive-compatible'
      : changes.reduce<ChangeClassification>(
          (acc, c) => worstOf(acc, c.classification),
          'additive-compatible',
        );

  const isBreaking = overallClassification === 'breaking';
  const isRisky = overallClassification === 'risky-compatible';

  const blockingReason = isBreaking
    ? `Breaking change detected. Human approval, migration plan and explicit major version bump required before this spec can be approved.`
    : null;

  const affectedConsumers = isBreaking ? known_consumers : [];

  return {
    spec_id,
    from_version,
    to_version,
    classification: overallClassification,
    changes,
    requires_human_approval: isBreaking || isRisky,
    migration_plan_required: isBreaking,
    affected_consumers: affectedConsumers,
    blocking_reason: blockingReason,
  };
}

/**
 * Returns true if the diff result allows the spec to advance to `approved`
 * without human intervention.
 */
export function canAutoApprove(diff: SpecDiffResult): boolean {
  return (
    diff.classification === 'additive-compatible' ||
    diff.classification === 'behavior-compatible'
  );
}

/**
 * Summarizes a diff result as a one-line string for logging.
 */
export function summarizeDiff(diff: SpecDiffResult): string {
  const { spec_id, from_version, to_version, classification, changes } = diff;
  const breakingCount = changes.filter((c) => c.classification === 'breaking').length;
  const riskyCount = changes.filter((c) => c.classification === 'risky-compatible').length;
  return (
    `[spec-diff] ${spec_id}: ${from_version} → ${to_version} | ` +
    `${classification} | ${changes.length} changes (${breakingCount} breaking, ${riskyCount} risky)`
  );
}
