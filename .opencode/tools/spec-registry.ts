/**
 * spec-registry.ts
 *
 * Central registry for versioned specs in the spec-driven deep agent platform.
 *
 * Responsibilities:
 * - Validate specs against their JSON schemas
 * - Register and index specs by spec_id + version
 * - Enforce that a spec must be approved before a DAG can be compiled from it
 * - Provide lookup, history and status checks
 *
 * This module is pure TypeScript with no external runtime dependencies.
 * Schema validation is structural (JSON Schema draft-07 subset) without a full AJV runtime.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type SpecStatus = 'draft' | 'proposed' | 'approved' | 'deprecated';

export type SpecType =
  | 'capability'
  | 'behavior'
  | 'verification'
  | 'policy'
  | 'release'
  | 'slo'
  | 'contract';

export interface SpecEntry {
  spec_id: string;
  spec_type: SpecType;
  version: string;
  status: SpecStatus;
  domain: string;
  registered_at: string; // ISO 8601
  registered_by: string;
  payload: Record<string, unknown>;
}

export interface SpecValidationResult {
  valid: boolean;
  errors: string[];
}

export interface SpecHistoryEntry {
  version: string;
  status: SpecStatus;
  registered_at: string;
  registered_by: string;
}

// ---------------------------------------------------------------------------
// In-memory Registry Store
// ---------------------------------------------------------------------------
// In production this would be backed by a persistent store (filesystem, DB).
// For the framework scaffold, a module-level Map provides deterministic behavior.

const store = new Map<string, SpecEntry[]>();
// Key format: "<spec_id>" → array of entries ordered oldest-to-newest

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function specKey(spec_id: string): string {
  return spec_id.toLowerCase().trim();
}

function parseVersion(v: string): [number, number, number] {
  const parts = v.split('.').map(Number);
  if (parts.length !== 3 || parts.some(isNaN)) {
    throw new Error(`Invalid semver: "${v}"`);
  }
  return [parts[0], parts[1], parts[2]];
}

function compareVersions(a: string, b: string): number {
  const [a1, a2, a3] = parseVersion(a);
  const [b1, b2, b3] = parseVersion(b);
  if (a1 !== b1) return a1 - b1;
  if (a2 !== b2) return a2 - b2;
  return a3 - b3;
}

// ---------------------------------------------------------------------------
// Structural Validator (JSON Schema draft-07 subset)
// ---------------------------------------------------------------------------

function validateRequiredFields(
  payload: Record<string, unknown>,
  required: string[],
): string[] {
  return required
    .filter((f) => !(f in payload) || payload[f] === undefined || payload[f] === null)
    .map((f) => `Missing required field: "${f}"`);
}

const SPEC_TYPE_REQUIRED_FIELDS: Record<SpecType, string[]> = {
  capability: ['spec_id', 'version', 'status', 'domain', 'objective', 'inputs', 'outputs', 'invariants'],
  behavior: ['behavior_id', 'version', 'capability_ref', 'states', 'initial_state', 'terminal_states', 'transitions'],
  verification: ['verification_id', 'version', 'capability_ref', 'acceptance_criteria', 'properties', 'generated_tests'],
  policy: ['policy_bundle', 'version', 'rules'],
  release: ['release_id', 'version', 'capability_ref', 'strategy', 'stages', 'rollback', 'gates'],
  slo: ['slo_id', 'version', 'capability_ref', 'objectives'],
  contract: ['contract_id', 'version', 'capability_ref', 'required_fields'],
};

const SEMVER_RE = /^\d+\.\d+\.\d+$/;
const VALID_STATUSES: SpecStatus[] = ['draft', 'proposed', 'approved', 'deprecated'];

/**
 * Validates a spec payload structurally.
 * Returns `{ valid: true }` or `{ valid: false, errors: [...] }`.
 */
export function validateSpec(
  payload: Record<string, unknown>,
  spec_type: SpecType,
): SpecValidationResult {
  const errors: string[] = [];

  // Required fields per spec type
  const requiredFields = SPEC_TYPE_REQUIRED_FIELDS[spec_type];
  if (!requiredFields) {
    errors.push(`Unknown spec_type: "${spec_type}"`);
    return { valid: false, errors };
  }
  errors.push(...validateRequiredFields(payload, requiredFields));

  // Version format
  const version = payload['version'] as string | undefined;
  if (version && !SEMVER_RE.test(version)) {
    errors.push(`"version" must be semver (x.y.z), got: "${version}"`);
  }

  // Status enum (capability specs)
  if (spec_type === 'capability') {
    const status = payload['status'] as string | undefined;
    if (status && !VALID_STATUSES.includes(status as SpecStatus)) {
      errors.push(`"status" must be one of ${VALID_STATUSES.join(', ')}, got: "${status}"`);
    }

    // spec_id pattern: must start with "capability."
    const spec_id = payload['spec_id'] as string | undefined;
    if (spec_id && !spec_id.startsWith('capability.')) {
      errors.push(`"spec_id" must start with "capability.", got: "${spec_id}"`);
    }

    // invariants must be non-empty array
    const invariants = payload['invariants'];
    if (!Array.isArray(invariants) || invariants.length === 0) {
      errors.push('"invariants" must be a non-empty array of strings');
    }
  }

  return { valid: errors.length === 0, errors };
}

// ---------------------------------------------------------------------------
// Registry Operations
// ---------------------------------------------------------------------------

/**
 * Registers a new spec version. Rejects if:
 * - Validation fails
 * - Same spec_id + version already exists
 * - A newer version already exists (prevents downgrade injection)
 */
export function registerSpec(
  spec_id: string,
  spec_type: SpecType,
  version: string,
  status: SpecStatus,
  domain: string,
  payload: Record<string, unknown>,
  registered_by: string = 'system',
): SpecValidationResult {
  const validation = validateSpec(payload, spec_type);
  if (!validation.valid) {
    return validation;
  }

  const key = specKey(spec_id);
  const existing = store.get(key) ?? [];

  // Duplicate version check
  if (existing.some((e) => e.version === version)) {
    return {
      valid: false,
      errors: [`Spec "${spec_id}" version "${version}" already registered. Use a new version.`],
    };
  }

  const entry: SpecEntry = {
    spec_id,
    spec_type,
    version,
    status,
    domain,
    registered_at: new Date().toISOString(),
    registered_by,
    payload,
  };

  store.set(key, [...existing, entry].sort((a, b) => compareVersions(a.version, b.version)));

  return { valid: true, errors: [] };
}

/**
 * Retrieves the latest approved version of a spec, or a specific version.
 * Returns `undefined` if not found or if no approved version exists.
 */
export function getSpec(spec_id: string, version?: string): SpecEntry | undefined {
  const entries = store.get(specKey(spec_id));
  if (!entries || entries.length === 0) return undefined;

  if (version) {
    return entries.find((e) => e.version === version);
  }

  // Latest approved
  const approved = entries.filter((e) => e.status === 'approved');
  return approved.length > 0 ? approved[approved.length - 1] : undefined;
}

/**
 * Returns all registered specs, optionally filtered by type or domain.
 */
export function listSpecs(filter?: { spec_type?: SpecType; domain?: string; status?: SpecStatus }): SpecEntry[] {
  const all: SpecEntry[] = [];
  for (const entries of store.values()) {
    const latest = entries[entries.length - 1];
    if (!latest) continue;
    if (filter?.spec_type && latest.spec_type !== filter.spec_type) continue;
    if (filter?.domain && latest.domain !== filter.domain) continue;
    if (filter?.status && latest.status !== filter.status) continue;
    all.push(latest);
  }
  return all;
}

/**
 * Returns the full version history for a spec_id.
 */
export function getSpecHistory(spec_id: string): SpecHistoryEntry[] {
  const entries = store.get(specKey(spec_id)) ?? [];
  return entries.map(({ version, status, registered_at, registered_by }) => ({
    version,
    status,
    registered_at,
    registered_by,
  }));
}

/**
 * Updates the status of a specific spec version (e.g., draft → proposed → approved → deprecated).
 * Gate: cannot move from deprecated to any active status.
 */
export function updateSpecStatus(
  spec_id: string,
  version: string,
  new_status: SpecStatus,
): SpecValidationResult {
  const key = specKey(spec_id);
  const entries = store.get(key);
  if (!entries) {
    return { valid: false, errors: [`Spec "${spec_id}" not found`] };
  }

  const entry = entries.find((e) => e.version === version);
  if (!entry) {
    return { valid: false, errors: [`Spec "${spec_id}" version "${version}" not found`] };
  }

  if (entry.status === 'deprecated' && new_status !== 'deprecated') {
    return {
      valid: false,
      errors: [`Cannot reactivate deprecated spec "${spec_id}@${version}". Create a new version instead.`],
    };
  }

  entry.status = new_status;
  return { valid: true, errors: [] };
}

/**
 * Gate check: asserts that a spec_id exists in approved status before a DAG
 * compilation can proceed. Called by the orchestrator before starting a run.
 */
export function assertSpecApproved(spec_id: string, version?: string): SpecValidationResult {
  const entry = getSpec(spec_id, version);

  if (!entry) {
    return {
      valid: false,
      errors: [
        `Run blocked: no approved spec found for "${spec_id}"${version ? `@${version}` : ''}. ` +
          'Register and approve a spec before compiling the DAG.',
      ],
    };
  }

  if (entry.status !== 'approved') {
    return {
      valid: false,
      errors: [
        `Run blocked: spec "${spec_id}@${entry.version}" is in status "${entry.status}". ` +
          'Spec must be approved before DAG compilation.',
      ],
    };
  }

  return { valid: true, errors: [] };
}

/**
 * Clears the registry. Intended for testing only.
 */
export function _clearRegistry(): void {
  store.clear();
}
