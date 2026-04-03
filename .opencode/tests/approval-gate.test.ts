import { beforeEach, describe, expect, it } from 'bun:test';

import { evaluateApprovalGate } from '../tools/approval-gate.js';
import type { ImpactReport } from '../tools/impact-analyzer.js';
import type { PolicyGuardianReport } from '../tools/policy-enforcer.js';
import type { TaskNode } from '../tools/spec-compiler.js';
import { _clearLinks, createLink } from '../tools/spec-linker.js';

function makeImpact(risk: ImpactReport['payload']['risk_level'], compatibility: ImpactReport['compatibility_assessment']): ImpactReport {
  return {
    schema_version: '1.0.0',
    artifact_type: 'impact-report',
    producer_agent: 'impact-analyzer',
    spec_id: 'capability.payment-routing',
    spec_version: '1.0.0',
    run_id: 'run-gate',
    timestamp: '2026-04-02T00:00:00.000Z',
    compatibility_assessment: compatibility,
    payload: {
      impact_scope: {
        services: ['payments'],
        contracts: [],
        datastores: [],
        slos: [],
      },
      risk_level: risk,
      blast_radius: {
        files: 1,
        apis: 0,
        consumers: 0,
        databases: 0,
      },
    },
    trace_links: [],
    evidence_refs: ['spec://capability.payment-routing@1.0.0'],
  };
}

function makeNode(overrides: Partial<TaskNode> = {}): TaskNode {
  return {
    task_id: 'node-1',
    derived_from_specs: ['behavior.payment@1.0.0'],
    type: 'implementation',
    label: 'apply change',
    inputs: {},
    dependencies: [],
    write_scope: ['workspace/output.json'],
    invariants: [],
    admissible_outputs: [],
    retry_policy: { max_attempts: 1, backoff: 'fixed', circuit_breaker: true },
    budget: { max_tokens: 1024, max_cost_usd: 0.01, timeout_ms: 1000 },
    required_evidence: [],
    required_approvals: [],
    conformance_checks: [],
    risk_level: 'low',
    ...overrides,
  };
}

function makePolicyReport(overrides: Partial<PolicyGuardianReport['policy_guardian_report']> = {}): PolicyGuardianReport {
  return {
    policy_guardian_report: {
      dag_id: 'dag-policy',
      timestamp: '2026-04-02T00:00:00.000Z',
      nodes_checked: 1,
      violations_found: 0,
      violations: [],
      auto_resolved: [],
      approved: true,
      decision: 'allow',
      ...overrides,
    },
  };
}

describe('UT: approval-gate.ts', () => {
  beforeEach(() => {
    _clearLinks();
  });

  it('allows approved low-risk changes with no pending signals', () => {
    const result = evaluateApprovalGate({
      spec_status: 'approved',
      validation: { valid: true, errors: [] },
      impact: makeImpact('low', 'additive-compatible'),
      dag: {
        policy_violations: [],
        requires_human_approval: false,
        nodes: [makeNode()],
      },
    });

    expect(result.decision).toBe('allow');
    expect(result.reasons).toHaveLength(0);
  });

  it('routes risky or pending approvals to review', () => {
    const result = evaluateApprovalGate({
      spec_status: 'approved',
      validation: { valid: true, errors: [] },
      impact: makeImpact('high', 'risky-compatible'),
      dag: {
        policy_violations: [],
        requires_human_approval: true,
        nodes: [makeNode({ required_approvals: ['tech-lead'] })],
      },
    });

    expect(result.decision).toBe('review');
    expect(result.reasons.some((reason) => reason.includes('High impact'))).toBe(true);
    expect(result.reasons.some((reason) => reason.includes('approvals'))).toBe(true);
  });

  it('allows when approvals and evidence were already satisfied', () => {
    const result = evaluateApprovalGate({
      current_dag_id: 'dag-policy',
      spec_status: 'approved',
      validation: { valid: true, errors: [] },
      impact: makeImpact('low', 'additive-compatible'),
      resolved_approvals: ['tech-lead'],
      resolved_evidence: ['evidence://transition/plan'],
      dag: {
        policy_violations: [],
        requires_human_approval: false,
        nodes: [
          makeNode({
            required_approvals: ['tech-lead'],
            required_evidence: ['evidence://transition/plan'],
          }),
        ],
      },
      policy_report: makePolicyReport(),
    });

    expect(result.decision).toBe('allow');
    expect(result.reasons).toHaveLength(0);
  });

  it('does not trust an approved policy report from another DAG', () => {
    const result = evaluateApprovalGate({
      current_dag_id: 'dag-current',
      spec_status: 'approved',
      validation: { valid: true, errors: [] },
      impact: makeImpact('low', 'additive-compatible'),
      dag: {
        policy_violations: [],
        requires_human_approval: false,
        nodes: [
          makeNode({
            required_approvals: ['tech-lead'],
            required_evidence: ['evidence://transition/plan'],
          }),
        ],
      },
      policy_report: makePolicyReport({ dag_id: 'dag-other', approved: true, decision: 'allow' }),
    });

    expect(result.decision).toBe('block');
    expect(result.reasons.some((reason) => reason.includes('matching current_dag_id'))).toBe(true);
  });

  it('blocks when the DAG already carries policy violations even with an approved matching report', () => {
    const result = evaluateApprovalGate({
      current_dag_id: 'dag-policy',
      spec_status: 'approved',
      validation: { valid: true, errors: [] },
      impact: makeImpact('low', 'additive-compatible'),
      dag: {
        policy_violations: ['write scope conflict'],
        requires_human_approval: false,
        nodes: [makeNode()],
      },
      policy_report: makePolicyReport({ dag_id: 'dag-policy', approved: true, decision: 'allow', violations_found: 0 }),
    });

    expect(result.decision).toBe('block');
    expect(result.reasons.some((reason) => reason.includes('policy violation'))).toBe(true);
    expect(result.reasons.some((reason) => reason.includes('diverge'))).toBe(true);
  });

  it('does not let an approved matching policy report clear pending approvals or evidence', () => {
    const result = evaluateApprovalGate({
      current_dag_id: 'dag-policy',
      spec_status: 'approved',
      validation: { valid: true, errors: [] },
      impact: makeImpact('low', 'additive-compatible'),
      dag: {
        policy_violations: [],
        requires_human_approval: false,
        nodes: [
          makeNode({
            required_approvals: ['tech-lead'],
            required_evidence: ['evidence://transition/plan'],
          }),
        ],
      },
      policy_report: makePolicyReport({ dag_id: 'dag-policy', approved: true, decision: 'allow', violations_found: 0 }),
    });

    expect(result.decision).toBe('review');
    expect(result.reasons.some((reason) => reason.includes('approvals'))).toBe(true);
    expect(result.reasons.some((reason) => reason.includes('evidence'))).toBe(true);
  });

  it('does not treat arbitrary resolved approvals as satisfying generic human approval', () => {
    const result = evaluateApprovalGate({
      spec_status: 'approved',
      validation: { valid: true, errors: [] },
      impact: makeImpact('low', 'additive-compatible'),
      resolved_approvals: ['placeholder'],
      dag: {
        policy_violations: [],
        requires_human_approval: true,
        nodes: [makeNode()],
      },
    });

    expect(result.decision).toBe('review');
    expect(result.reasons.some((reason) => reason.includes('approvals'))).toBe(true);
  });

  it('allows generic human approval only when explicitly granted', () => {
    const result = evaluateApprovalGate({
      spec_status: 'approved',
      validation: { valid: true, errors: [] },
      impact: makeImpact('low', 'additive-compatible'),
      human_approval_granted: true,
      dag: {
        policy_violations: [],
        requires_human_approval: true,
        nodes: [makeNode()],
      },
    });

    expect(result.decision).toBe('allow');
  });

  it('blocks invalid or breaking inputs', () => {
    const result = evaluateApprovalGate({
      spec_status: 'proposed',
      validation: { valid: false, errors: ['schema mismatch'] },
      impact: makeImpact('critical', 'breaking'),
      dag: {
        policy_violations: ['budget exceeded'],
        requires_human_approval: false,
        nodes: [makeNode()],
      },
    });

    expect(result.decision).toBe('block');
    expect(result.reasons).toContain('schema mismatch');
    expect(result.reasons.some((reason) => reason.includes('policy violation'))).toBe(true);
  });

  it('blocks release execution without minimum trace links', () => {
    const result = evaluateApprovalGate({
      current_spec_id: 'capability.payment-routing',
      run_id: 'run-release-missing-trace',
      spec_status: 'approved',
      validation: { valid: true, errors: [] },
      impact: makeImpact('low', 'additive-compatible'),
      dag: {
        policy_violations: [],
        requires_human_approval: false,
        nodes: [makeNode({ type: 'release' })],
      },
    });

    expect(result.decision).toBe('block');
    expect(result.reasons.some((reason) => reason.includes('No traceability link found'))).toBe(true);
  });

  it('allows release execution when minimum trace links exist', async () => {
    await createLink('capability.payment-routing', '1.0.0', 'run-release-ready', {
      requirements: ['req://payment-routing/1'],
      code_refs: ['.opencode/tools/approval-gate.ts:1'],
      test_cases: ['UT: approval-gate traceability'],
      evidence_refs: ['evidence://approval-gate/traceability'],
      owner_technical: 'platform-team',
      owner_domain: 'payments',
    });

    const result = evaluateApprovalGate({
      current_spec_id: 'capability.payment-routing',
      run_id: 'run-release-ready',
      spec_status: 'approved',
      validation: { valid: true, errors: [] },
      impact: makeImpact('low', 'additive-compatible'),
      dag: {
        policy_violations: [],
        requires_human_approval: false,
        nodes: [makeNode({ type: 'release' })],
      },
    });

    expect(result.decision).toBe('allow');
    expect(result.signals.traceability_score).toBeGreaterThanOrEqual(0.75);
  });
});
