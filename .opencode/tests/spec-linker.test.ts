import { beforeEach, describe, expect, it } from 'bun:test';

import {
  _clearLinks,
  appendToLink,
  assertMinimumLinks,
  computeScore,
  createLink,
  listGaps,
  listLinks,
  resolveLink,
  type TraceLinks,
} from '../tools/spec-linker.js';

function makeLinks(overrides: Partial<TraceLinks> = {}): Partial<TraceLinks> {
  return {
    requirements: ['req://payments/routing'],
    code_refs: ['.opencode/tools/spec-linker.ts:1'],
    test_cases: ['UT: spec-linker createLink'],
    evidence_refs: ['evidence://spec-linker/basic'],
    owner_technical: 'platform-team',
    owner_domain: 'payments',
    ...overrides,
  };
}

describe('UT: spec-linker.ts', () => {
  beforeEach(() => {
    _clearLinks();
  });

  it('creates a traceability link with spec fallback and resolves it by both keys', () => {
    const created = createLink('capability.payment-routing', '1.0.0', 'run-link-001', makeLinks());

    expect(created.link.link_id).toMatch(/^tl_capability\.payment-routing_run-link-001_/);
    expect(created.link.links.specs).toEqual(['capability.payment-routing']);
    expect(created.link.completeness_score).toBeGreaterThan(0.65);

    const byLinkId = resolveLink({ link_id: created.link.link_id });
    const byCompositeKey = resolveLink({
      spec_id: 'capability.payment-routing',
      run_id: 'run-link-001',
    });

    expect(byLinkId?.link_id).toBe(created.link.link_id);
    expect(byCompositeKey?.link_id).toBe(created.link.link_id);
    expect(listLinks({ spec_id: 'capability.payment-routing' })).toHaveLength(1);
  });

  it('computes weighted score and classifies missing gaps correctly', () => {
    const partialLinks: TraceLinks = {
      requirements: ['req://payments/routing'],
      specs: ['capability.payment-routing'],
      dag_nodes: [],
      code_refs: [],
      test_cases: [],
      evidence_refs: [],
      runtime_trace_ids: [],
      owner_technical: 'platform-team',
      owner_domain: 'payments',
    };

    expect(computeScore(partialLinks)).toBe(0.35);

    const gaps = listGaps(partialLinks);
    expect(gaps.find((gap) => gap.type === 'code_refs')?.severity).toBe('error');
    expect(gaps.find((gap) => gap.type === 'test_cases')?.severity).toBe('error');
    expect(gaps.find((gap) => gap.type === 'evidence_refs')?.severity).toBe('blocking');
    expect(gaps.find((gap) => gap.type === 'dag_nodes')?.severity).toBe('warning');
    expect(gaps.find((gap) => gap.type === 'runtime_trace_ids')?.severity).toBe('warning');
  });

  it('blocks when a link is missing or below the minimum threshold', () => {
    const missing = assertMinimumLinks('capability.payment-routing', 'run-missing');
    expect(missing.valid).toBe(false);
    expect(missing.errors.some((error) => error.includes('No traceability link found'))).toBe(true);

    createLink('capability.payment-routing', '1.0.0', 'run-partial', {
      requirements: ['req://payments/routing'],
      owner_technical: 'platform-team',
      owner_domain: 'payments',
    });

    const belowThreshold = assertMinimumLinks('capability.payment-routing', 'run-partial');
    expect(belowThreshold.valid).toBe(false);
    expect(belowThreshold.errors.some((error) => error.includes('below minimum 0.75'))).toBe(true);
  });

  it('allows when a link is sufficiently complete', () => {
    createLink('capability.payment-routing', '1.0.0', 'run-complete', {
      requirements: ['req://payments/routing'],
      dag_nodes: ['received_to_validated_000'],
      code_refs: ['.opencode/tools/spec-linker.ts:1'],
      test_cases: ['UT: spec-linker sufficient'],
      evidence_refs: ['evidence://spec-linker/sufficient'],
      runtime_trace_ids: ['trace-123'],
      owner_technical: 'platform-team',
      owner_domain: 'payments',
    });

    const valid = assertMinimumLinks('capability.payment-routing', 'run-complete');
    expect(valid.valid).toBe(true);
    expect(valid.completeness_score).toBe(1);
  });

  it('appends links with deduplication and recalculates completeness', () => {
    const created = createLink('capability.payment-routing', '1.0.0', 'run-append', {
      requirements: ['req://payments/routing'],
      owner_technical: 'platform-team',
      owner_domain: 'payments',
    });

    const updated = appendToLink('capability.payment-routing', 'run-append', {
      requirements: ['req://payments/routing'],
      dag_nodes: ['received_to_validated_000'],
      code_refs: ['.opencode/tools/spec-linker.ts:1'],
      test_cases: ['UT: spec-linker append'],
      evidence_refs: ['evidence://spec-linker/append'],
      runtime_trace_ids: ['trace-123', 'trace-123'],
    });

    expect(updated).not.toBeNull();
    expect(updated?.links.requirements).toEqual(['req://payments/routing']);
    expect(updated?.links.runtime_trace_ids).toEqual(['trace-123']);
    expect(updated?.completeness_score).toBeGreaterThan(created.link.completeness_score);
    expect(updated?.missing_links.some((gap) => gap.type === 'code_refs')).toBe(false);
  });
});
