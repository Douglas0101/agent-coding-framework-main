import { beforeEach, describe, expect, it } from 'bun:test';

import { _clearLinks, resolveLink } from '../tools/spec-linker.js';
import {
  _clearRegistry,
  approveSpec,
  getSpec,
  registerSpec,
  updateSpecStatus,
} from '../tools/spec-registry.js';

function buildCapabilityPayload(version: string, status: 'draft' | 'proposed' | 'approved' = 'draft') {
  return {
    spec_id: 'capability.order-routing',
    version,
    status,
    domain: 'payments',
    objective: 'Route orders through compliant payment processors.',
    inputs: [{ name: 'request', type: 'OrderRequest' }],
    outputs: [{ name: 'decision', type: 'RoutingDecision' }],
    invariants: ['All routing decisions must be auditable.'],
    traceability: {
      owner_technical: 'platform-team',
      owner_domain: 'payments',
      requirement_refs: ['req://payments/order-routing'],
    },
  };
}

describe('UT: spec-registry.ts', () => {
  beforeEach(() => {
    _clearRegistry();
    _clearLinks();
  });

  it('requires formal approval flow and creates traceability on approval', async () => {
    const register = await registerSpec(
      'capability.order-routing',
      'capability',
      '1.0.0',
      'draft',
      'payments',
      buildCapabilityPayload('1.0.0', 'draft'),
      'spec-architect',
    );

    expect(register.valid).toBe(true);
    expect((await updateSpecStatus('capability.order-routing', '1.0.0', 'proposed')).valid).toBe(true);

    const approval = await approveSpec('capability.order-routing', '1.0.0', {
      approved_by: 'tech-lead',
      approval_run_id: 'run-approve-order-routing',
      code_refs: ['.opencode/specs/capabilities/order-routing.capability.yaml:1'],
      test_cases: ['UT: spec-registry approval traceability'],
      evidence_refs: ['evidence://spec-review/order-routing'],
    });

    expect(approval.valid).toBe(true);

    const spec = getSpec('capability.order-routing', '1.0.0');
    expect(spec?.status).toBe('approved');
    expect(spec?.approval?.approved_by).toBe('tech-lead');
    expect(spec?.approval?.traceability_link_id).toBeDefined();

    const traceLink = resolveLink({
      spec_id: 'capability.order-routing',
      run_id: 'run-approve-order-routing',
    });
    expect(traceLink?.spec_id).toBe('capability.order-routing');
  });

  it('rejects direct approval registration and direct approved transition', async () => {
    const directApproved = await registerSpec(
      'capability.order-routing',
      'capability',
      '1.0.0',
      'approved',
      'payments',
      buildCapabilityPayload('1.0.0', 'approved'),
      'spec-architect',
    );

    expect(directApproved.valid).toBe(false);
    expect(directApproved.errors.some((error) => error.includes('Direct registration as "approved"'))).toBe(true);

    const register = await registerSpec(
      'capability.order-routing',
      'capability',
      '1.0.0',
      'draft',
      'payments',
      buildCapabilityPayload('1.0.0', 'draft'),
      'spec-architect',
    );

    expect(register.valid).toBe(true);
    expect((await updateSpecStatus('capability.order-routing', '1.0.0', 'approved')).valid).toBe(false);
  });

  it('rejects approval metadata without a real approver identity', async () => {
    expect(
      (await registerSpec(
        'capability.order-routing',
        'capability',
        '1.0.0',
        'draft',
        'payments',
        buildCapabilityPayload('1.0.0', 'draft'),
        'spec-architect',
      )).valid,
    ).toBe(true);
    expect((await updateSpecStatus('capability.order-routing', '1.0.0', 'proposed')).valid).toBe(true);

    const emptyApprover = await approveSpec('capability.order-routing', '1.0.0', {
      approved_by: '   ',
    });
    expect(emptyApprover.valid).toBe(false);

    const emptyRunId = await approveSpec('capability.order-routing', '1.0.0', {
      approved_by: 'tech-lead',
      approval_run_id: '   ',
    });
    expect(emptyRunId.valid).toBe(false);
  });

  it('rejects approval when traceability minimums are missing', async () => {
    expect(
      (await registerSpec(
        'capability.order-routing',
        'capability',
        '1.0.0',
        'draft',
        'payments',
        buildCapabilityPayload('1.0.0', 'draft'),
        'spec-architect',
      )).valid,
    ).toBe(true);
    expect((await updateSpecStatus('capability.order-routing', '1.0.0', 'proposed')).valid).toBe(true);

    const approval = await approveSpec('capability.order-routing', '1.0.0', {
      approved_by: 'tech-lead',
      evidence_refs: ['evidence://spec-review/order-routing'],
    });

    expect(approval.valid).toBe(false);
    expect(approval.errors.some((error) => error.includes('Code references'))).toBe(true);
  });

  it('rejects invalid specs in under 100ms', async () => {
    const start = performance.now();
    const result = await registerSpec(
      'capability.invalid-routing',
      'capability',
      '1.0.0',
      'draft',
      'payments',
      {
        spec_id: 'capability.invalid-routing',
        version: '1.0.0',
        status: 'draft',
        domain: 'payments',
        objective: 'Invalid spec for latency bound test.',
        inputs: [],
        outputs: [],
      },
      'spec-architect',
    );
    const elapsed = performance.now() - start;

    expect(result.valid).toBe(false);
    expect(elapsed).toBeLessThan(100);
  });
});
