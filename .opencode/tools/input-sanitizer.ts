/**
 * input-sanitizer.ts
 *
 * Input validation and sanitization for spec-driven framework identifiers.
 * Prevents injection attacks, path traversal, and malformed identifiers.
 *
 * This module is pure TypeScript with no external runtime dependencies.
 */

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MAX_ID_LENGTH = 128;
const MAX_RUN_ID_LENGTH = 256;
const MAX_VERSION_LENGTH = 32;
const MAX_DOMAIN_LENGTH = 64;

// Allowed characters for identifiers: alphanumeric, hyphens, underscores, dots
const ID_PATTERN = /^[a-zA-Z0-9][a-zA-Z0-9._-]*$/;
const VERSION_PATTERN = /^\d+\.\d+\.\d+$/;
const RUN_ID_PATTERN = /^[a-zA-Z0-9][a-zA-Z0-9._:@/-]*$/;
const DOMAIN_PATTERN = /^[a-zA-Z0-9][a-zA-Z0-9._-]*$/;

// Blocked path segments to prevent path traversal
const BLOCKED_PATH_SEGMENTS = [
  '..',
  '~',
  '/etc/',
  '/proc/',
  '/sys/',
  '/var/',
  '/tmp/',
  'node_modules',
  '.env',
  '.git',
  'passwd',
  'shadow',
  'sudoers',
];

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SanitizationResult {
  valid: boolean;
  sanitized: string;
  errors: string[];
}

// ---------------------------------------------------------------------------
// Sanitization Functions
// ---------------------------------------------------------------------------

/**
 * Sanitize and validate a spec_id.
 * Returns a SanitizationResult with the sanitized value or errors.
 */
export function sanitizeSpecId(input: string): SanitizationResult {
  const errors: string[] = [];
  const trimmed = input.trim();

  if (!trimmed) {
    return { valid: false, sanitized: '', errors: ['spec_id cannot be empty'] };
  }

  if (trimmed.length > MAX_ID_LENGTH) {
    errors.push(`spec_id exceeds maximum length of ${MAX_ID_LENGTH} characters`);
  }

  if (!ID_PATTERN.test(trimmed)) {
    errors.push(
      `spec_id contains invalid characters. Only alphanumeric, hyphens, underscores, and dots are allowed, and must start with alphanumeric`,
    );
  }

  // Check for path traversal attempts
  if (containsBlockedPath(trimmed)) {
    errors.push('spec_id contains blocked path segments');
  }

  return {
    valid: errors.length === 0,
    sanitized: trimmed.toLowerCase(),
    errors,
  };
}

/**
 * Sanitize and validate a version string (semver format).
 */
export function sanitizeVersion(input: string): SanitizationResult {
  const errors: string[] = [];
  const trimmed = input.trim();

  if (!trimmed) {
    return { valid: false, sanitized: '', errors: ['version cannot be empty'] };
  }

  if (trimmed.length > MAX_VERSION_LENGTH) {
    errors.push(`version exceeds maximum length of ${MAX_VERSION_LENGTH} characters`);
  }

  if (!VERSION_PATTERN.test(trimmed)) {
    errors.push('version must be in semver format (major.minor.patch)');
  }

  return {
    valid: errors.length === 0,
    sanitized: trimmed,
    errors,
  };
}

/**
 * Sanitize and validate a run_id.
 */
export function sanitizeRunId(input: string): SanitizationResult {
  const errors: string[] = [];
  const trimmed = input.trim();

  if (!trimmed) {
    return { valid: false, sanitized: '', errors: ['run_id cannot be empty'] };
  }

  if (trimmed.length > MAX_RUN_ID_LENGTH) {
    errors.push(`run_id exceeds maximum length of ${MAX_RUN_ID_LENGTH} characters`);
  }

  if (!RUN_ID_PATTERN.test(trimmed)) {
    errors.push(
      `run_id contains invalid characters. Only alphanumeric, hyphens, underscores, dots, colons, and forward slashes are allowed`,
    );
  }

  if (containsBlockedPath(trimmed)) {
    errors.push('run_id contains blocked path segments');
  }

  return {
    valid: errors.length === 0,
    sanitized: trimmed,
    errors,
  };
}

/**
 * Sanitize and validate a domain name.
 */
export function sanitizeDomain(input: string): SanitizationResult {
  const errors: string[] = [];
  const trimmed = input.trim();

  if (!trimmed) {
    return { valid: false, sanitized: '', errors: ['domain cannot be empty'] };
  }

  if (trimmed.length > MAX_DOMAIN_LENGTH) {
    errors.push(`domain exceeds maximum length of ${MAX_DOMAIN_LENGTH} characters`);
  }

  if (!DOMAIN_PATTERN.test(trimmed)) {
    errors.push(
      `domain contains invalid characters. Only alphanumeric, hyphens, underscores, and dots are allowed`,
    );
  }

  return {
    valid: errors.length === 0,
    sanitized: trimmed.toLowerCase(),
    errors,
  };
}

/**
 * Sanitize an agent identity string.
 */
export function sanitizeAgentIdentity(input: string): SanitizationResult {
  const errors: string[] = [];
  const trimmed = input.trim();

  if (!trimmed) {
    return { valid: false, sanitized: '', errors: ['agent identity cannot be empty'] };
  }

  if (trimmed.length > MAX_ID_LENGTH) {
    errors.push(`agent identity exceeds maximum length of ${MAX_ID_LENGTH} characters`);
  }

  if (!ID_PATTERN.test(trimmed)) {
    errors.push(
      `agent identity contains invalid characters. Only alphanumeric, hyphens, underscores, and dots are allowed`,
    );
  }

  return {
    valid: errors.length === 0,
    sanitized: trimmed.toLowerCase(),
    errors,
  };
}

/**
 * Check if a string contains blocked path segments.
 */
function containsBlockedPath(input: string): boolean {
  const lower = input.toLowerCase();
  return BLOCKED_PATH_SEGMENTS.some((segment) => lower.includes(segment.toLowerCase()));
}

/**
 * Validate multiple inputs at once. Returns combined result.
 */
export function sanitizeMultiple(
  inputs: Record<string, string>,
  sanitizers: Record<string, (input: string) => SanitizationResult>,
): { valid: boolean; results: Record<string, SanitizationResult> } {
  const results: Record<string, SanitizationResult> = {};
  let allValid = true;

  for (const [key, value] of Object.entries(inputs)) {
    const sanitizer = sanitizers[key];
    if (!sanitizer) {
      results[key] = {
        valid: false,
        sanitized: '',
        errors: [`No sanitizer defined for field: ${key}`],
      };
      allValid = false;
      continue;
    }

    const result = sanitizer(value);
    results[key] = result;
    if (!result.valid) {
      allValid = false;
    }
  }

  return { valid: allValid, results };
}
