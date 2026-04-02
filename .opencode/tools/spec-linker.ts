/**
 * spec-linker.ts
 *
 * Maintains bidirectional traceability across the full chain:
 *   requirement → spec → DAG node → code change → test case → evidence → runtime trace → SLO impact
 *
 * Core operations:
 *   - createLink()       : registers a new trace link for a run
 *   - resolveLink()      : retrieves link by link_id or (spec_id + run_id)
 *   - computeScore()     : calculates completeness score (0.0–1.0)
 *   - assertMinimumLinks(): gate check — blocks critical releases with incomplete traceability
 *   - listGaps()         : lists missing link categories with severity
 *
 * No external runtime dependencies.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface TraceLinks {
  requirements: string[];
  specs: string[];
  dag_nodes: string[];
  code_refs: string[];
  test_cases: string[];
  evidence_refs: string[];
  runtime_trace_ids: string[];
  owner_technical: string;
  owner_domain: string;
}

export interface TraceGap {
  type: keyof TraceLinks;
  severity: 'warning' | 'error' | 'blocking';
  description: string;
}

export interface TraceabilityLink {
  link_id: string;
  schema_version: string;
  spec_id: string;
  spec_version: string;
  run_id: string;
  timestamp: string;
  completeness_score: number;
  links: TraceLinks;
  missing_links: TraceGap[];
}

export interface LinkerValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  completeness_score: number;
}

// ---------------------------------------------------------------------------
// Weights for completeness score
// Ordered by criticality: ownership first, then chain topology.
// ---------------------------------------------------------------------------

interface LinkWeight {
  weight: number;
  severity_if_missing: TraceGap['severity'];
  description: string;
}

const LINK_WEIGHTS: Record<keyof TraceLinks, LinkWeight> = {
  requirements: {
    weight: 0.15,
    severity_if_missing: 'error',
    description: 'At least one requirement or RFC reference is required',
  },
  specs: {
    weight: 0.15,
    severity_if_missing: 'blocking',
    description: 'The spec_id link is mandatory for all critical changes',
  },
  dag_nodes: {
    weight: 0.10,
    severity_if_missing: 'warning',
    description: 'DAG node IDs improve execution traceability',
  },
  code_refs: {
    weight: 0.20,
    severity_if_missing: 'error',
    description: 'Code references (file + line) are required for implementation traces',
  },
  test_cases: {
    weight: 0.15,
    severity_if_missing: 'error',
    description: 'Test case references are required to demonstrate verification',
  },
  evidence_refs: {
    weight: 0.15,
    severity_if_missing: 'blocking',
    description: 'Evidence references are required for runs with risk_level >= high',
  },
  runtime_trace_ids: {
    weight: 0.05,
    severity_if_missing: 'warning',
    description: 'Runtime trace IDs improve incident response correlation',
  },
  owner_technical: {
    weight: 0.025,
    severity_if_missing: 'warning',
    description: 'Technical owner identification is required',
  },
  owner_domain: {
    weight: 0.025,
    severity_if_missing: 'warning',
    description: 'Domain owner identification is required',
  },
};

// ---------------------------------------------------------------------------
// In-memory store
// ---------------------------------------------------------------------------

const linkStore = new Map<string, TraceabilityLink>();

function linkKey(spec_id: string, run_id: string): string {
  return `${spec_id}::${run_id}`;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function countPresent(links: TraceLinks): Record<keyof TraceLinks, boolean> {
  return {
    requirements: links.requirements.length > 0,
    specs: links.specs.length > 0,
    dag_nodes: links.dag_nodes.length > 0,
    code_refs: links.code_refs.length > 0,
    test_cases: links.test_cases.length > 0,
    evidence_refs: links.evidence_refs.length > 0,
    runtime_trace_ids: links.runtime_trace_ids.length > 0,
    owner_technical: Boolean(links.owner_technical?.trim()),
    owner_domain: Boolean(links.owner_domain?.trim()),
  };
}

/**
 * Computes a weighted completeness score in [0.0, 1.0].
 */
export function computeScore(links: TraceLinks): number {
  const presence = countPresent(links);
  let score = 0;
  for (const [key, meta] of Object.entries(LINK_WEIGHTS)) {
    if (presence[key as keyof TraceLinks]) {
      score += meta.weight;
    }
  }
  return Math.min(Math.max(Math.round(score * 1000) / 1000, 0), 1);
}

/**
 * Lists categories with missing links and their severity.
 */
export function listGaps(links: TraceLinks): TraceGap[] {
  const presence = countPresent(links);
  const gaps: TraceGap[] = [];

  for (const [key, meta] of Object.entries(LINK_WEIGHTS)) {
    if (!presence[key as keyof TraceLinks]) {
      gaps.push({
        type: key as keyof TraceLinks,
        severity: meta.severity_if_missing,
        description: meta.description,
      });
    }
  }

  return gaps;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Creates and persists a new traceability link for a run.
 * Returns a validation result including the completeness score and any gaps.
 */
export function createLink(
  spec_id: string,
  spec_version: string,
  run_id: string,
  links: Partial<TraceLinks>,
): { link: TraceabilityLink; validation: LinkerValidationResult } {
  const fullLinks: TraceLinks = {
    requirements: links.requirements ?? [],
    specs: links.specs ?? [spec_id],
    dag_nodes: links.dag_nodes ?? [],
    code_refs: links.code_refs ?? [],
    test_cases: links.test_cases ?? [],
    evidence_refs: links.evidence_refs ?? [],
    runtime_trace_ids: links.runtime_trace_ids ?? [],
    owner_technical: links.owner_technical ?? '',
    owner_domain: links.owner_domain ?? '',
  };

  const score = computeScore(fullLinks);
  const gaps = listGaps(fullLinks);
  const errors = gaps.filter((g) => g.severity === 'blocking' || g.severity === 'error').map((g) => g.description);
  const warnings = gaps.filter((g) => g.severity === 'warning').map((g) => g.description);

  const link_id = `tl_${spec_id}_${run_id}_${Date.now()}`;

  const traceLink: TraceabilityLink = {
    link_id,
    schema_version: '1.0.0',
    spec_id,
    spec_version,
    run_id,
    timestamp: new Date().toISOString(),
    completeness_score: score,
    links: fullLinks,
    missing_links: gaps,
  };

  linkStore.set(linkKey(spec_id, run_id), traceLink);

  return {
    link: traceLink,
    validation: {
      valid: errors.length === 0,
      errors,
      warnings,
      completeness_score: score,
    },
  };
}

/**
 * Retrieves a traceability link by link_id, or by (spec_id, run_id) composite key.
 */
export function resolveLink(options: { link_id: string } | { spec_id: string; run_id: string }): TraceabilityLink | undefined {
  if ('link_id' in options) {
    for (const link of linkStore.values()) {
      if (link.link_id === options.link_id) return link;
    }
    return undefined;
  }
  return linkStore.get(linkKey(options.spec_id, options.run_id));
}

/**
 * Gate check: asserts minimum traceability requirements before a critical release.
 *
 * Blocks if:
 *   - completeness_score < minimum_score
 *   - any gap with severity === 'blocking' exists
 */
export function assertMinimumLinks(
  spec_id: string,
  run_id: string,
  minimum_score = 0.75,
): LinkerValidationResult {
  const link = resolveLink({ spec_id, run_id });

  if (!link) {
    return {
      valid: false,
      errors: [`No traceability link found for spec="${spec_id}" run="${run_id}". Create a link before release.`],
      warnings: [],
      completeness_score: 0,
    };
  }

  const errors: string[] = [];
  const warnings: string[] = [];

  if (link.completeness_score < minimum_score) {
    errors.push(
      `Traceability score ${link.completeness_score.toFixed(3)} is below minimum ${minimum_score}. ` +
        'Fill missing link categories before proceeding.',
    );
  }

  for (const gap of link.missing_links) {
    if (gap.severity === 'blocking') errors.push(`[blocking] ${gap.description}`);
    else if (gap.severity === 'error') errors.push(`[error] ${gap.description}`);
    else warnings.push(`[warning] ${gap.description}`);
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
    completeness_score: link.completeness_score,
  };
}

/**
 * Appends additional link data to an existing trace link (e.g., runtime trace IDs added post-deploy).
 */
export function appendToLink(
  spec_id: string,
  run_id: string,
  additionalLinks: Partial<TraceLinks>,
): TraceabilityLink | null {
  const existing = linkStore.get(linkKey(spec_id, run_id));
  if (!existing) return null;

  const merged: TraceLinks = {
    requirements: [...new Set([...existing.links.requirements, ...(additionalLinks.requirements ?? [])])],
    specs: [...new Set([...existing.links.specs, ...(additionalLinks.specs ?? [])])],
    dag_nodes: [...new Set([...existing.links.dag_nodes, ...(additionalLinks.dag_nodes ?? [])])],
    code_refs: [...new Set([...existing.links.code_refs, ...(additionalLinks.code_refs ?? [])])],
    test_cases: [...new Set([...existing.links.test_cases, ...(additionalLinks.test_cases ?? [])])],
    evidence_refs: [...new Set([...existing.links.evidence_refs, ...(additionalLinks.evidence_refs ?? [])])],
    runtime_trace_ids: [...new Set([...existing.links.runtime_trace_ids, ...(additionalLinks.runtime_trace_ids ?? [])])],
    owner_technical: additionalLinks.owner_technical ?? existing.links.owner_technical,
    owner_domain: additionalLinks.owner_domain ?? existing.links.owner_domain,
  };

  const updated: TraceabilityLink = {
    ...existing,
    links: merged,
    completeness_score: computeScore(merged),
    missing_links: listGaps(merged),
  };

  linkStore.set(linkKey(spec_id, run_id), updated);
  return updated;
}

/**
 * Lists all trace links, optionally filtered by spec_id.
 */
export function listLinks(filter?: { spec_id?: string }): TraceabilityLink[] {
  const all = Array.from(linkStore.values());
  if (filter?.spec_id) {
    return all.filter((l) => l.spec_id === filter.spec_id);
  }
  return all;
}

/**
 * Clears the link store. Intended for testing only.
 */
export function _clearLinks(): void {
  linkStore.clear();
}
