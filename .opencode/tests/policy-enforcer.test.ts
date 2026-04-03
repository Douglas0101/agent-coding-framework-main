import { describe, expect, it } from 'bun:test';

import { enforcePolicyPreflight } from '../tools/policy-enforcer.js';
import type { CompiledDAG, TaskNode } from '../tools/spec-compiler.js';

function makeNode(task_id: string, overrides: Partial<TaskNode> = {}): TaskNode {
  return {
    task_id,
    derived_from_specs: ['behavior.payment@1.0.0'],
    type: 'implementation',
    label: task_id,
    inputs: {},
    dependencies: [],
    write_scope: [`artifacts/${task_id}.json`],
    invariants: [],
    admissible_outputs: [],
    retry_policy: { max_attempts: 2, backoff: 'fixed', circuit_breaker: true },
    budget: { max_tokens: 2048, max_cost_usd: 0.02, timeout_ms: 1000 },
    required_evidence: [],
    required_approvals: [],
    conformance_checks: [],
    risk_level: 'low',
    ...overrides,
  };
}

function makeDag(nodes: TaskNode[]): CompiledDAG {
  return {
    dag_id: 'dag-policy-test',
    spec_id: 'capability.payment-routing',
    spec_version: '1.0.0',
    compiled_at: '2026-04-02T00:00:00.000Z',
    nodes,
    execution_order: nodes.map((node) => node.task_id),
    policy_violations: [],
    requires_human_approval: nodes.some((node) => node.required_approvals.length > 0),
  };
}

describe('UT: policy-enforcer.ts', () => {
  it('approves a clean DAG', () => {
    const report = enforcePolicyPreflight(
      makeDag([makeNode('node-clean')]),
      {
        retry_policy: { max_attempts: 3 },
        budget: { max_tokens_critical: 8192 },
      },
      { timestamp: '2026-04-02T00:00:00.000Z' },
    );

    expect(report.policy_guardian_report.decision).toBe('allow');
    expect(report.policy_guardian_report.violations_found).toBe(0);
    expect(report.policy_guardian_report.effective_execution_order).toEqual(['node-clean']);
    expect(report.policy_guardian_report.serialized_edges).toEqual([]);
  });

  it('blocks forbidden transitions immediately', () => {
    const report = enforcePolicyPreflight(
      makeDag([
        makeNode('node-blocked', {
          conformance_checks: ['forbidden_transition_check: BLOCKED (draft -> release)'],
        }),
      ]),
    );

    expect(report.policy_guardian_report.decision).toBe('block');
    expect(report.policy_guardian_report.violations[0]?.rule_id).toBe('forbidden_transition_check');
  });

  it('blocks when approvals or evidence are still pending', () => {
    const report = enforcePolicyPreflight(
      makeDag([
        makeNode('node-review', {
          risk_level: 'high',
          required_approvals: ['tech-lead'],
          required_evidence: ['evidence://transition/plan'],
        }),
      ]),
    );

    expect(report.policy_guardian_report.decision).toBe('block');
    expect(report.policy_guardian_report.violations.map((violation) => violation.rule_id)).toEqual([
      'required_approvals',
      'required_evidence',
    ]);
  });

  it('blocks retry limit excess and missing circuit breaker', () => {
    const report = enforcePolicyPreflight(
      makeDag([
        makeNode('node-retry', {
          risk_level: 'medium',
          retry_policy: { max_attempts: 5, backoff: 'fixed', circuit_breaker: false },
        }),
      ]),
      {
        retry_policy: { max_attempts: 3 },
      },
    );

    expect(report.policy_guardian_report.decision).toBe('block');
    expect(report.policy_guardian_report.violations.map((violation) => violation.rule_id)).toEqual([
      'retry_policy.max_attempts',
      'retry_policy.circuit_breaker',
    ]);
  });

  it('checks critical token budgets', () => {
    const report = enforcePolicyPreflight(
      makeDag([
        makeNode('node-budget', {
          risk_level: 'critical',
          budget: { max_tokens: 9000, max_cost_usd: 0.05, timeout_ms: 1000 },
        }),
      ]),
      {
        budget: { max_tokens_critical: 8192 },
      },
    );

    expect(report.policy_guardian_report.decision).toBe('block');
    expect(report.policy_guardian_report.violations[0]?.rule_id).toBe('budget.max_tokens');
  });

  it('blocks cyclic task graphs deterministically', () => {
    const report = enforcePolicyPreflight(
      makeDag([
        makeNode('node-a', { dependencies: ['node-b'] }),
        makeNode('node-b', { dependencies: ['node-a'] }),
      ]),
    );

    expect(report.policy_guardian_report.decision).toBe('block');
    expect(report.policy_guardian_report.violations[0]?.rule_id).toBe('dag_cycle');
  });

  it('blocks orphan dependencies deterministically', () => {
    const report = enforcePolicyPreflight(
      makeDag([
        makeNode('node-a', { dependencies: ['node-missing'] }),
      ]),
    );

    expect(report.policy_guardian_report.decision).toBe('block');
    expect(report.policy_guardian_report.violations[0]?.rule_id).toBe('orphan_dependency');
    expect(report.policy_guardian_report.violations[0]?.detail.includes('unknown node')).toBe(true);
  });

  it('serializes conflicting write scopes between parallel nodes', () => {
    const report = enforcePolicyPreflight(
      makeDag([
        makeNode('node-left', { write_scope: ['artifacts/shared.json'] }),
        makeNode('node-right', { write_scope: ['artifacts/shared.json'] }),
      ]),
    );

    expect(report.policy_guardian_report.decision).toBe('allow');
    expect(report.policy_guardian_report.violations).toHaveLength(0);
    expect(report.policy_guardian_report.auto_resolved[0]?.action).toBe('serialized_parallel_execution');
    expect(report.policy_guardian_report.serialized_edges).toEqual([
      {
        from: 'node-left',
        to: 'node-right',
        reason: 'serialize overlapping write_scope between "node-left" and "node-right"',
      },
    ]);
    expect(report.policy_guardian_report.effective_execution_order).toEqual(['node-left', 'node-right']);
  });

  it('serializes directory and file write scope overlap for parallel nodes', () => {
    const report = enforcePolicyPreflight(
      makeDag([
        makeNode('node-dir', { write_scope: ['artifacts/codex-swarm/run-1/'] }),
        makeNode('node-file', { write_scope: ['artifacts/codex-swarm/run-1/report.json'] }),
      ]),
    );

    expect(report.policy_guardian_report.decision).toBe('allow');
    expect(report.policy_guardian_report.serialized_edges).toHaveLength(1);
  });

  it('serializes directory and subdirectory write scope overlap for parallel nodes', () => {
    const report = enforcePolicyPreflight(
      makeDag([
        makeNode('node-parent', { write_scope: ['artifacts/codex-swarm/run-1/'] }),
        makeNode('node-child', { write_scope: ['artifacts/codex-swarm/run-1/subdir/'] }),
      ]),
    );

    expect(report.policy_guardian_report.decision).toBe('allow');
    expect(report.policy_guardian_report.serialized_edges).toHaveLength(1);
  });

  it('serializes dot write scope as universal conflict', () => {
    const report = enforcePolicyPreflight(
      makeDag([
        makeNode('node-root', { write_scope: ['.'] }),
        makeNode('node-file', { write_scope: ['artifacts/codex-swarm/run-1/report.json'] }),
      ]),
    );

    expect(report.policy_guardian_report.decision).toBe('allow');
    expect(report.policy_guardian_report.serialized_edges).toHaveLength(1);
  });

  it('serializes dot-slash write scope as universal conflict', () => {
    const report = enforcePolicyPreflight(
      makeDag([
        makeNode('node-root', { write_scope: ['./'] }),
        makeNode('node-dir', { write_scope: ['artifacts/codex-swarm/run-1/'] }),
      ]),
    );

    expect(report.policy_guardian_report.decision).toBe('allow');
    expect(report.policy_guardian_report.serialized_edges).toHaveLength(1);
  });

  it('serializes empty write scope as universal conflict after normalization', () => {
    const report = enforcePolicyPreflight(
      makeDag([
        makeNode('node-empty', { write_scope: [''] }),
        makeNode('node-dir', { write_scope: ['artifacts/codex-swarm/run-1/'] }),
      ]),
    );

    expect(report.policy_guardian_report.decision).toBe('allow');
    expect(report.policy_guardian_report.serialized_edges).toHaveLength(1);
  });

  it('keeps the original DAG execution order untouched while deriving a serialized plan', () => {
    const dag = makeDag([
      makeNode('node-b', { write_scope: ['artifacts/shared.json'] }),
      makeNode('node-a', { write_scope: ['artifacts/shared.json'] }),
    ]);
    dag.execution_order = ['node-b', 'node-a'];

    const report = enforcePolicyPreflight(dag);

    expect(dag.nodes[1]?.dependencies).toEqual([]);
    expect(dag.execution_order).toEqual(['node-b', 'node-a']);
    expect(report.policy_guardian_report.effective_execution_order).toEqual(['node-b', 'node-a']);
    expect(report.policy_guardian_report.serialized_edges).toEqual([
      {
        from: 'node-b',
        to: 'node-a',
        reason: 'serialize overlapping write_scope between "node-b" and "node-a"',
      },
    ]);
  });
});
