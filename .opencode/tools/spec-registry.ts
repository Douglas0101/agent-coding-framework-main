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

import { createLink } from './spec-linker.js';
import { AsyncLock } from './async-lock.js';
import { clearBlockedMessage, isClearAllowed } from './clear-guard.js';
import { sanitizeSpecId, sanitizeVersion, sanitizeDomain, sanitizeAgentIdentity } from './input-sanitizer.js';

// ---------------------------------------------------------------------------
// Concurrency Control
// ---------------------------------------------------------------------------

/**
 * AsyncLock to prevent race conditions in concurrent multi-agent execution.
 * All write operations must acquire this lock before modifying the store.
 */
const registryLock = new AsyncLock();

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
  approval?: SpecApprovalMetadata;
}

export interface SpecApprovalMetadata {
  approved_at: string;
  approved_by: string;
  approval_run_id: string;
  traceability_link_id: string;
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

export interface ApproveSpecInput {
  approved_by: string;
  requirement_refs?: string[];
  code_refs?: string[];
  test_cases?: string[];
  evidence_refs?: string[];
  owner_technical?: string;
  owner_domain?: string;
  approval_run_id?: string;
}

export interface ApproveSpecResult extends SpecValidationResult {
  traceability_link_id?: string;
  approval_run_id?: string;
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

function toStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === 'string');
}

function extractTraceabilityDefaults(payload: Record<string, unknown>): {
  requirement_refs: string[];
  owner_technical: string;
  owner_domain: string;
} {
  const traceability = payload['traceability'];
  if (!traceability || typeof traceability !== 'object' || Array.isArray(traceability)) {
    return {
      requirement_refs: [],
      owner_technical: '',
      owner_domain: '',
    };
  }

  const record = traceability as Record<string, unknown>;
  return {
    requirement_refs: toStringArray(record['requirement_refs']),
    owner_technical:
      typeof record['owner_technical'] === 'string' ? record['owner_technical'] : '',
    owner_domain: typeof record['owner_domain'] === 'string' ? record['owner_domain'] : '',
  };
}

function syncPayloadStatus(entry: SpecEntry, status: SpecStatus): void {
  if (entry.spec_type === 'capability') {
    entry.payload = {
      ...entry.payload,
      status,
    };
  }
}

function canTransition(current: SpecStatus, next: SpecStatus): boolean {
  const allowedTransitions: Record<SpecStatus, SpecStatus[]> = {
    draft: ['draft', 'proposed', 'deprecated'],
    proposed: ['proposed', 'approved', 'deprecated'],
    approved: ['approved', 'deprecated'],
    deprecated: ['deprecated'],
  };

  return allowedTransitions[current].includes(next);
}

async function createApprovalMetadata(
  entry: SpecEntry,
  approved_by: string,
  input: Omit<ApproveSpecInput, 'approved_by'>,
  approved_at: string,
): Promise<{
  approval: SpecApprovalMetadata;
  valid: boolean;
  errors: string[];
}> {
  const defaults = extractTraceabilityDefaults(entry.payload);
  const approval_run_id = input.approval_run_id?.trim() || `approval:${entry.spec_id}@${entry.version}`;
  const traceLink = await createLink(entry.spec_id, entry.version, approval_run_id, {
    requirements: input.requirement_refs ?? defaults.requirement_refs,
    code_refs: input.code_refs ?? [],
    test_cases: input.test_cases ?? [],
    evidence_refs: input.evidence_refs ?? [`spec://${entry.spec_id}@${entry.version}`],
    owner_technical: input.owner_technical ?? defaults.owner_technical,
    owner_domain: input.owner_domain ?? defaults.owner_domain,
  });

  return {
    approval: {
      approved_at,
      approved_by,
      approval_run_id,
      traceability_link_id: traceLink.link.link_id,
    },
    valid: traceLink.validation.valid,
    errors: traceLink.validation.errors,
  };
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
export async function registerSpec(
  spec_id: string,
  spec_type: SpecType,
  version: string,
  status: SpecStatus,
  domain: string,
  payload: Record<string, unknown>,
  registered_by: string = 'system',
): Promise<SpecValidationResult> {
  // Input sanitization and validation
  const specIdResult = sanitizeSpecId(spec_id);
  if (!specIdResult.valid) {
    return { valid: false, errors: [`Invalid spec_id: ${specIdResult.errors.join(', ')}`] };
  }

  const versionResult = sanitizeVersion(version);
  if (!versionResult.valid) {
    return { valid: false, errors: [`Invalid version: ${versionResult.errors.join(', ')}`] };
  }

  const domainResult = sanitizeDomain(domain);
  if (!domainResult.valid) {
    return { valid: false, errors: [`Invalid domain: ${domainResult.errors.join(', ')}`] };
  }

  const registeredByResult = sanitizeAgentIdentity(registered_by);
  if (!registeredByResult.valid) {
    return { valid: false, errors: [`Invalid registered_by: ${registeredByResult.errors.join(', ')}`] };
  }

  const sanitizedSpecId = specIdResult.sanitized;
  const sanitizedVersion = versionResult.sanitized;
  const sanitizedDomain = domainResult.sanitized;
  const sanitizedRegisteredBy = registeredByResult.sanitized;

  const validation = validateSpec(payload, spec_type);
  if (!validation.valid) {
    return validation;
  }

  const release = await registryLock.acquire();
  try {
    const key = specKey(sanitizedSpecId);
    const existing = store.get(key) ?? [];

    // Duplicate version check
    if (existing.some((e) => e.version === sanitizedVersion)) {
      return {
        valid: false,
        errors: [`Spec "${sanitizedSpecId}" version "${sanitizedVersion}" already registered. Use a new version.`],
      };
    }

    const latest = existing[existing.length - 1];
    if (latest && compareVersions(sanitizedVersion, latest.version) < 0) {
      return {
        valid: false,
        errors: [
          `Spec "${sanitizedSpecId}" version "${sanitizedVersion}" is older than the latest registered version "${latest.version}". Downgrade registration is blocked.`,
        ],
      };
    }

    if (status === 'approved') {
      return {
        valid: false,
        errors: [
          `Direct registration as "approved" is blocked for "${sanitizedSpecId}@${sanitizedVersion}". Register the spec as "draft" or "proposed" and use approveSpec().`,
        ],
      };
    }

    const normalizedPayload =
      spec_type === 'capability'
        ? {
            ...payload,
            status,
          }
        : { ...payload };

    const registered_at = new Date().toISOString();

    const entry: SpecEntry = {
      spec_id: sanitizedSpecId,
      spec_type,
      version: sanitizedVersion,
      status,
      domain: sanitizedDomain,
      registered_at,
      registered_by: sanitizedRegisteredBy,
      payload: normalizedPayload,
    };

    store.set(key, [...existing, entry].sort((a, b) => compareVersions(a.version, b.version)));

    return { valid: true, errors: [] };
  } finally {
    release();
  }
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
 * Thread-safe: uses async lock for concurrent access protection.
 */
export async function updateSpecStatus(
  spec_id: string,
  version: string,
  new_status: SpecStatus,
): Promise<SpecValidationResult> {
  const specIdResult = sanitizeSpecId(spec_id);
  if (!specIdResult.valid) {
    return { valid: false, errors: [`Invalid spec_id: ${specIdResult.errors.join(', ')}`] };
  }

  const versionResult = sanitizeVersion(version);
  if (!versionResult.valid) {
    return { valid: false, errors: [`Invalid version: ${versionResult.errors.join(', ')}`] };
  }

  const release = await registryLock.acquire();
  try {
    const key = specKey(specIdResult.sanitized);
    const entries = store.get(key);
    if (!entries) {
      return { valid: false, errors: [`Spec "${specIdResult.sanitized}" not found`] };
    }

    const entry = entries.find((e) => e.version === versionResult.sanitized);
    if (!entry) {
      return { valid: false, errors: [`Spec "${specIdResult.sanitized}" version "${versionResult.sanitized}" not found`] };
    }

    if (entry.status === 'deprecated' && new_status !== 'deprecated') {
      return {
        valid: false,
        errors: [`Cannot reactivate deprecated spec "${specIdResult.sanitized}@${versionResult.sanitized}". Create a new version instead.`],
      };
    }

    if (new_status === 'approved') {
      return {
        valid: false,
        errors: [
          `Direct status transition to "approved" is blocked for "${specIdResult.sanitized}@${versionResult.sanitized}". Use approveSpec() to capture approval metadata and traceability.`,
        ],
      };
    }

    if (!canTransition(entry.status, new_status)) {
      return {
        valid: false,
        errors: [
          `Invalid status transition for "${specIdResult.sanitized}@${versionResult.sanitized}": ${entry.status} -> ${new_status}.`,
        ],
      };
    }

    entry.status = new_status;
    syncPayloadStatus(entry, new_status);
    return { valid: true, errors: [] };
  } finally {
    release();
  }
}

/**
 * Formal approval path for a proposed spec version.
 * Approval captures traceability metadata and links the approved spec to a
 * minimal traceability manifest.
 * Thread-safe: uses async lock for concurrent access protection.
 */
export async function approveSpec(
  spec_id: string,
  version: string,
  input: ApproveSpecInput,
): Promise<ApproveSpecResult> {
  const specIdResult = sanitizeSpecId(spec_id);
  if (!specIdResult.valid) {
    return { valid: false, errors: [`Invalid spec_id: ${specIdResult.errors.join(', ')}`] };
  }

  const versionResult = sanitizeVersion(version);
  if (!versionResult.valid) {
    return { valid: false, errors: [`Invalid version: ${versionResult.errors.join(', ')}`] };
  }

  const approvedByResult = sanitizeAgentIdentity(input.approved_by);
  if (!approvedByResult.valid) {
    return { valid: false, errors: [`Invalid approved_by: ${approvedByResult.errors.join(', ')}`] };
  }

  const release = await registryLock.acquire();
  try {
    const key = specKey(specIdResult.sanitized);
    const entries = store.get(key);
    if (!entries) {
      return { valid: false, errors: [`Spec "${specIdResult.sanitized}" not found`] };
    }

    const entry = entries.find((candidate) => candidate.version === versionResult.sanitized);
    if (!entry) {
      return { valid: false, errors: [`Spec "${specIdResult.sanitized}" version "${versionResult.sanitized}" not found`] };
    }

    if (entry.status !== 'proposed') {
      return {
        valid: false,
        errors: [
          `Spec "${specIdResult.sanitized}@${versionResult.sanitized}" must be in status "proposed" before approval. Current status: "${entry.status}".`,
        ],
      };
    }

    const approvedBy = approvedByResult.sanitized;
    if (!approvedBy) {
      return {
        valid: false,
        errors: [`Spec "${specIdResult.sanitized}@${versionResult.sanitized}" approval requires a non-empty approved_by identity.`],
      };
    }

    if (input.approval_run_id !== undefined && input.approval_run_id.trim() === '') {
      return {
        valid: false,
        errors: [`Spec "${specIdResult.sanitized}@${versionResult.sanitized}" approval_run_id must be non-empty when provided.`],
      };
    }

    if (approvedBy === entry.registered_by.trim()) {
      return {
        valid: false,
        errors: [
          `Spec "${specIdResult.sanitized}@${versionResult.sanitized}" cannot be approved by its original author "${entry.registered_by}".`,
        ],
      };
    }

    const approved_at = new Date().toISOString();
    const approvalResult = await createApprovalMetadata(
      entry,
      approvedBy,
      {
        requirement_refs: input.requirement_refs,
        code_refs: input.code_refs,
        test_cases: input.test_cases,
        evidence_refs: input.evidence_refs,
        owner_technical: input.owner_technical,
        owner_domain: input.owner_domain,
        approval_run_id: input.approval_run_id,
      },
      approved_at,
    );

    if (!approvalResult.valid) {
      return {
        valid: false,
        errors: approvalResult.errors,
      };
    }

    entry.status = 'approved';
    entry.approval = approvalResult.approval;
    syncPayloadStatus(entry, 'approved');

    return {
      valid: true,
      errors: [],
      traceability_link_id: approvalResult.approval.traceability_link_id,
      approval_run_id: approvalResult.approval.approval_run_id,
    };
  } finally {
    release();
  }
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
 * PRODUCTION GUARD: Blocked when NODE_ENV is 'production' or when ALLOW_CLEAR is not set.
 */
export function _clearRegistry(): void {
  if (!isClearAllowed()) {
    throw new Error(clearBlockedMessage('_clearRegistry'));
  }
  store.clear();
}

/**
 * Export lock metrics for monitoring (read-only).
 */
export function getRegistryLockMetrics(): { isLocked: boolean; queueLength: number } {
  return {
    isLocked: registryLock.isLocked,
    queueLength: registryLock.queueLength,
  };
}
