import { beforeEach, describe, expect, it } from 'bun:test';

import { analyzeImpact } from '../tools/impact-analyzer.js';
import { approveSpec, _clearRegistry, registerSpec } from '../tools/spec-registry.js';

async function registerCapability(
  version: string,
  payload: Record<string, unknown>,
  status: 'draft' | 'proposed' | 'approved' = 'approved',
): Promise<void> {
  const result = await registerSpec(
    'capability.payment-routing',
    'capability',
    version,
    status === 'approved' ? 'proposed' : status,
    'payments',
    {
      spec_id: 'capability.payment-routing',
      version,
      status: status === 'approved' ? 'proposed' : status,
      domain: 'payments',
      objective: 'Route payment requests safely between processors.',
      inputs: [{ name: 'request', type: 'PaymentRequest' }],
      outputs: [{ name: 'decision', type: 'RoutingDecision' }],
      invariants: ['All routing decisions must be auditable.'],
      ...payload,
    },
    'test-suite',
  );

  expect(result.valid).toBe(true);

  if (status === 'approved') {
    const approval = await approveSpec('capability.payment-routing', version, {
      approved_by: 'domain-reviewer',
      approval_run_id: `run-approve-capability-${version}`,
      requirement_refs: ['req://payments/routing'],
      code_refs: ['.opencode/specs/capabilities/payment-routing.capability.yaml:1'],
      test_cases: ['UT: impact-analyzer capability approval'],
      evidence_refs: [`spec://capability.payment-routing@${version}`],
      owner_technical: 'platform-team',
      owner_domain: 'payments',
    });
    expect(approval.valid).toBe(true);
  }
}

async function registerBehavior(
  version: string,
  payload: Record<string, unknown>,
  status: 'draft' | 'proposed' | 'approved' = 'approved',
): Promise<void> {
  const result = await registerSpec(
    'workflow.payment-routing',
    'behavior',
    version,
    status === 'approved' ? 'proposed' : status,
    'payments',
    {
      behavior_id: 'workflow.payment-routing',
      version,
      capability_ref: 'capability.payment-routing',
      states: ['draft', 'approved'],
      initial_state: 'draft',
      terminal_states: ['approved'],
      transitions: [{ from: 'draft', to: 'approved', action: 'approve' }],
      ...payload,
    },
    'test-suite',
  );

  expect(result.valid).toBe(true);

  if (status === 'approved') {
    const approval = await approveSpec('workflow.payment-routing', version, {
      approved_by: 'workflow-reviewer',
      approval_run_id: `run-approve-behavior-${version}`,
      requirement_refs: ['req://payments/routing'],
      code_refs: ['.opencode/specs/behaviors/payment-routing.behavior.yaml:1'],
      test_cases: ['UT: impact-analyzer behavior approval'],
      evidence_refs: [`spec://workflow.payment-routing@${version}`],
      owner_technical: 'platform-team',
      owner_domain: 'payments',
    });
    expect(approval.valid).toBe(true);
  }
}

describe('UT: impact-analyzer.ts', () => {
  beforeEach(() => {
    _clearRegistry();
  });

  it('uses a deterministic fallback when there is no previous version', async () => {
    await registerCapability('1.0.0', {
      change_surface: 'code',
      risk_level: 'low',
      impact_scope: {
        services: ['payments-api'],
        contracts: ['routing-contract'],
        datastores: [],
        slos: [],
      },
    });

    const result = analyzeImpact('capability.payment-routing', {
      run_id: 'run-impact-001',
      timestamp: '2026-04-02T00:00:00.000Z',
      evidence_refs: ['evidence://repo/.opencode/tools/spec-registry.ts'],
    });

    expect(result.previous_spec).toBeUndefined();
    expect(result.diff).toBeUndefined();
    expect(result.report.compatibility_assessment).toBe('behavior-compatible');
    expect(result.report.payload.risk_level).toBe('low');
    expect(result.report.timestamp).toBe('2026-04-02T00:00:00.000Z');
  });

  it('reuses spec-diff when a breaking previous version exists', async () => {
    await registerBehavior('1.0.0', {
      description: 'Baseline approval workflow.',
    });
    await registerBehavior('2.0.0', {
      initial_state: 'queued',
      change_surface: 'api',
    });

    const result = analyzeImpact('workflow.payment-routing', {
      run_id: 'run-impact-002',
      known_consumers: ['router-worker'],
    });

    expect(result.previous_spec?.version).toBe('1.0.0');
    expect(result.diff?.classification).toBe('breaking');
    expect(result.report.compatibility_assessment).toBe('breaking');
    expect(result.report.payload.risk_level).toBe('critical');
  });

  it('captures risky-compatible and additive-compatible baselines', async () => {
    await registerBehavior('1.0.0', {
      description: 'Baseline approval workflow.',
    });
    await registerBehavior('1.1.0', {
      description: 'Baseline approval workflow with richer logging.',
      timeout_ms: 1000,
    });

    const additive = analyzeImpact('workflow.payment-routing', {
      run_id: 'run-impact-003',
    });

    expect(additive.diff?.classification).toBe('additive-compatible');
    expect(additive.auto_approvable).toBe(true);

    await registerBehavior('1.2.0', {
      description: 'Baseline approval workflow with richer logging.',
      timeout_ms: 2000,
    });

    const risky = analyzeImpact('workflow.payment-routing', {
      run_id: 'run-impact-004',
    });

    expect(risky.diff?.classification).toBe('risky-compatible');
    expect(risky.report.compatibility_assessment).toBe('risky-compatible');
    expect(risky.report.payload.risk_level).toBe('medium');
  });

  it('elevates risk level when blast radius grows beyond the safe threshold', async () => {
    await registerCapability('1.0.0', {
      risk_level: 'low',
    });

    const result = analyzeImpact('capability.payment-routing', {
      run_id: 'run-impact-005',
      known_consumers: ['a', 'b', 'c', 'd', 'e', 'f'],
    });

    expect(result.report.payload.blast_radius.consumers).toBe(6);
    expect(result.report.payload.risk_level).toBe('high');
  });

  it('uses the latest approved baseline when history contains non-approved versions', async () => {
    await registerBehavior('1.0.0', {
      description: 'Approved baseline workflow.',
    });
    await registerBehavior('1.1.0', {
      description: 'Proposed intermediate workflow.',
      timeout_ms: 1000,
    }, 'proposed');
    await registerBehavior('1.2.0', {
      initial_state: 'queued',
    });

    const result = analyzeImpact('workflow.payment-routing', {
      run_id: 'run-impact-006',
    });

    expect(result.previous_spec?.version).toBe('1.0.0');
    expect(result.diff?.from_version).toBe('1.0.0');
    expect(result.diff?.to_version).toBe('1.2.0');
    expect(result.diff?.classification).toBe('breaking');
  });

  it('targets the latest registered version even when it is only proposed', async () => {
    await registerBehavior('1.0.0', {
      description: 'Approved baseline workflow.',
    });
    await registerBehavior('1.1.0', {
      timeout_ms: 1000,
    }, 'proposed');

    const result = analyzeImpact('workflow.payment-routing', {
      run_id: 'run-impact-007',
    });

    expect(result.spec.version).toBe('1.1.0');
    expect(result.previous_spec?.version).toBe('1.0.0');
    expect(result.diff?.from_version).toBe('1.0.0');
    expect(result.diff?.to_version).toBe('1.1.0');
  });
});
