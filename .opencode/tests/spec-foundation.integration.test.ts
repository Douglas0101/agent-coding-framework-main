import { beforeEach, describe, expect, it } from 'bun:test';

import { _clearLinks, appendToLink, resolveLink } from '../tools/spec-linker.js';
import {
  _clearRegistry,
  approveSpec,
  registerSpec,
} from '../tools/spec-registry.js';
import { compileDAG, compileDAGWithRunManifest } from '../tools/spec-compiler.js';

async function approveRegisteredSpec(spec_id: string, version: string, approved_by: string): Promise<void> {
  const approval = await approveSpec(spec_id, version, {
    approved_by,
    requirement_refs: ['req://payments/routing'],
    code_refs: [`spec://${spec_id}@${version}`],
    test_cases: [`IT: approval ${spec_id}`],
    evidence_refs: [`evidence://${spec_id}/${version}`],
    owner_technical: 'platform-team',
    owner_domain: 'payments',
    approval_run_id: `approval:${spec_id}@${version}`,
  });

  expect(approval.valid).toBe(true);
}

async function registerFoundationSpecs(): Promise<void> {
  expect(
    (await registerSpec(
      'capability.payment-routing',
      'capability',
      '1.0.0',
      'proposed',
      'payments',
      {
        spec_id: 'capability.payment-routing',
        version: '1.0.0',
        status: 'proposed',
        domain: 'payments',
        objective: 'Route payment requests safely between processors.',
        inputs: [{ name: 'request', type: 'PaymentRequest' }],
        outputs: [{ name: 'decision', type: 'RoutingDecision' }],
        invariants: ['All routing decisions must be auditable.'],
        traceability: {
          requirement_refs: ['req://payments/routing'],
          owner_technical: 'platform-team',
          owner_domain: 'payments',
        },
      },
      'spec-architect',
    )).valid,
  ).toBe(true);
  await approveRegisteredSpec('capability.payment-routing', '1.0.0', 'domain-reviewer');

  expect(
    (await registerSpec(
      'workflow.payment-routing',
      'behavior',
      '1.0.0',
      'proposed',
      'payments',
      {
        behavior_id: 'workflow.payment-routing',
        version: '1.0.0',
        capability_ref: 'capability.payment-routing',
        states: ['received', 'validated'],
        initial_state: 'received',
        terminal_states: ['validated'],
        transitions: [{ from: 'received', to: 'validated', action: 'validate' }],
      },
      'spec-architect',
    )).valid,
  ).toBe(true);
  await approveRegisteredSpec('workflow.payment-routing', '1.0.0', 'workflow-reviewer');

  expect(
    (await registerSpec(
      'policy.payment-routing',
      'policy',
      '1.0.0',
      'proposed',
      'payments',
      {
        policy_bundle: 'policy.payment-routing',
        version: '1.0.0',
        rules: [],
      },
      'policy-architect',
    )).valid,
  ).toBe(true);
  await approveRegisteredSpec('policy.payment-routing', '1.0.0', 'policy-reviewer');

  expect(
    (await registerSpec(
      'verification.payment-routing',
      'verification',
      '1.0.0',
      'proposed',
      'payments',
      {
        verification_id: 'verification.payment-routing',
        version: '1.0.0',
        capability_ref: 'capability.payment-routing',
        acceptance_criteria: ['validated transitions produce audit evidence'],
        properties: [],
        generated_tests: ['state_transition_tests'],
      },
      'verification-architect',
    )).valid,
  ).toBe(true);
  await approveRegisteredSpec('verification.payment-routing', '1.0.0', 'verification-reviewer');
}

describe('IT: spec foundation traceability bootstrap', () => {
  beforeEach(() => {
    _clearRegistry();
    _clearLinks();
  });

  it('builds a traceability bootstrap and initial run manifest without changing compileDAG contract', async () => {
    await registerFoundationSpecs();

    const legacy = compileDAG(
      'capability.payment-routing',
      'workflow.payment-routing',
      'policy.payment-routing',
      'verification.payment-routing',
      'run-123',
    );
    const enriched = await compileDAGWithRunManifest(
      'capability.payment-routing',
      'workflow.payment-routing',
      'policy.payment-routing',
      'verification.payment-routing',
      'run-123',
      {
        timestamp: '2026-04-02T00:00:00.000Z',
        code_refs: ['.opencode/tools/spec-compiler.ts:327'],
        test_cases: ['IT: spec foundation traceability bootstrap'],
        agents_activated: [{ agent: 'spec-compiler', verdict: 'pass' }],
        artifacts_produced: [
          {
            artifact_type: 'dag-compiled',
            path: 'artifacts/codex-swarm/run-123/dag-compiled.json',
          },
        ],
      },
    );

    expect(legacy.success).toBe(true);
    expect(enriched.success).toBe(true);
    expect(legacy.dag?.spec_id).toBe(enriched.dag?.spec_id);
    expect(legacy.dag?.nodes).toHaveLength(enriched.dag?.nodes.length ?? 0);
    expect(legacy.dag?.execution_order).toEqual(enriched.dag?.execution_order);

    expect(enriched.traceability_link?.spec_id).toBe('capability.payment-routing');
    expect(enriched.traceability_link?.links.dag_nodes).toEqual(
      enriched.dag?.nodes.map((node) => node.task_id),
    );
    expect(enriched.traceability_validation?.completeness_score).toBeGreaterThan(0.75);

    expect(enriched.run_manifest?.status).toBe('running');
    expect(enriched.run_manifest?.dag_id).toBe(enriched.dag?.dag_id);
    expect(enriched.run_manifest?.traceability_link_id).toBe(enriched.traceability_link?.link_id);
    expect(enriched.run_manifest?.spec_id).toBe('capability.payment-routing');
    expect(enriched.run_manifest?.trace_links?.requirements).toContain('req://payments/routing');
    expect(enriched.run_manifest?.trace_links?.owner_technical).toBe('platform-team');

    const stored = resolveLink({
      spec_id: 'capability.payment-routing',
      run_id: 'run-123',
    });
    expect(stored?.link_id).toBe(enriched.traceability_link?.link_id);

    const enrichedLink = await appendToLink('capability.payment-routing', 'run-123', {
      runtime_trace_ids: ['trace-123'],
      evidence_refs: ['evidence://runtime/trace-123'],
    });
    expect(enrichedLink?.links.runtime_trace_ids).toEqual(['trace-123']);

    const recompilation = await compileDAGWithRunManifest(
      'capability.payment-routing',
      'workflow.payment-routing',
      'policy.payment-routing',
      'verification.payment-routing',
      'run-123',
      {
        timestamp: '2026-04-02T00:01:00.000Z',
        code_refs: ['.opencode/tools/spec-compiler.ts:327'],
        test_cases: ['IT: spec foundation traceability bootstrap'],
      },
    );

    expect(recompilation.success).toBe(true);
    expect(recompilation.traceability_link?.link_id).toBe(enriched.traceability_link?.link_id);
    expect(recompilation.traceability_link?.links.runtime_trace_ids).toContain('trace-123');
    expect(recompilation.run_manifest?.traceability_link_id).toBe(enriched.traceability_link?.link_id);
  });
});
