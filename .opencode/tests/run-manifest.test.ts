import { describe, expect, it } from 'bun:test';

import type { CompiledDAG } from '../tools/spec-compiler.js';
import type { TraceabilityLink } from '../tools/spec-linker.js';
import { buildInitialRunManifest } from '../tools/run-manifest.js';

function makeDag(): CompiledDAG {
  return {
    dag_id: 'dag_run-123_123456',
    spec_id: 'capability.payment-routing',
    spec_version: '1.0.0',
    compiled_at: '2026-04-02T00:00:00.000Z',
    nodes: [
      {
        task_id: 'received_to_validated_000',
        derived_from_specs: ['workflow.payment-routing@1.0.0'],
        type: 'implementation',
        label: 'transition: received → validated',
        inputs: {},
        dependencies: [],
        write_scope: ['validated'],
        invariants: ['All routing decisions must be auditable.'],
        admissible_outputs: ['validated'],
        retry_policy: { max_attempts: 3, backoff: 'exponential', circuit_breaker: true },
        budget: { max_tokens: 4096, max_cost_usd: 0.05, timeout_ms: 1000 },
        required_evidence: [],
        required_approvals: [],
        conformance_checks: ['transition_allowed: received -> validated'],
        risk_level: 'medium',
      },
    ],
    execution_order: ['received_to_validated_000'],
    policy_violations: [],
    requires_human_approval: false,
  };
}

function makeTraceabilityLink(): Pick<TraceabilityLink, 'link_id' | 'completeness_score' | 'links'> {
  return {
    link_id: 'tl_capability.payment-routing_run-123_123456',
    completeness_score: 0.7,
    links: {
      requirements: ['req://payments/routing'],
      specs: ['capability.payment-routing'],
      dag_nodes: ['received_to_validated_000'],
      code_refs: ['.opencode/tools/spec-compiler.ts:327'],
      test_cases: ['IT: run-manifest builder'],
      evidence_refs: ['evidence://spec-compiler/bootstrap'],
      runtime_trace_ids: [],
      owner_technical: 'platform-team',
      owner_domain: 'payments',
    },
  };
}

describe('UT: run-manifest.ts', () => {
  it('builds a minimal initial run manifest from a DAG and trace link', () => {
    const manifest = buildInitialRunManifest({
      run_id: 'run-123',
      dag: makeDag(),
      traceability_link: makeTraceabilityLink(),
      timestamp: '2026-04-02T00:00:00.000Z',
    });

    expect(manifest.schema_version).toBe('1.0.0');
    expect(manifest.artifact_type).toBe('run-manifest');
    expect(manifest.status).toBe('running');
    expect(manifest.dag_id).toBe('dag_run-123_123456');
    expect(manifest.traceability_link_id).toBe('tl_capability.payment-routing_run-123_123456');
    expect(manifest.traceability_completeness_score).toBe(0.7);
    expect(manifest.trace_links?.requirements).toEqual(['req://payments/routing']);
    expect(manifest.trace_links?.owner_technical).toBe('platform-team');
    expect(manifest.risk_level).toBe('medium');
  });

  it('propagates optional execution metadata without duplicating full traceability state', () => {
    const manifest = buildInitialRunManifest({
      run_id: 'run-123',
      dag: makeDag(),
      traceability_link: makeTraceabilityLink(),
      timestamp: '2026-04-02T00:00:00.000Z',
      budget: {
        max_tokens: 8192,
        used_tokens: 1024,
        max_cost_usd: 0.25,
        used_cost_usd: 0.03,
      },
      agents_activated: [{ agent: 'spec-compiler', verdict: 'pass' }],
      artifacts_produced: [{ artifact_type: 'dag-compiled', path: 'artifacts/codex-swarm/run-123/dag-compiled.json' }],
      remaining_risks: ['code refs are bootstrap-only'],
      next_steps: ['append runtime trace ids after execution'],
    });

    expect(manifest.agents_activated).toHaveLength(1);
    expect(manifest.artifacts_produced).toHaveLength(1);
    expect(manifest.budget?.used_tokens).toBe(1024);
    expect(manifest.remaining_risks).toEqual(['code refs are bootstrap-only']);
    expect(manifest.next_steps).toEqual(['append runtime trace ids after execution']);
    expect('runtime_trace_ids' in (manifest.trace_links ?? {})).toBe(false);
  });

  it('schema supports dag and traceability foreign keys', async () => {
    const schema = await Bun.file(`${import.meta.dir}/../lib/artifact-schemas/run-manifest.schema.json`).json();

    expect(schema.properties.dag_id.type).toBe('string');
    expect(schema.properties.traceability_link_id.type).toBe('string');
    expect(schema.properties.trace_links.properties.owner_technical.type).toBe('string');
    expect(schema.required).not.toContain('dag_id');
    expect(schema.required).not.toContain('traceability_link_id');
  });
});
