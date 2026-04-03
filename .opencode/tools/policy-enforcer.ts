import path from 'node:path';

import type { CompiledDAG, RiskLevel, TaskNode } from './spec-compiler.js';

export type PolicyDecision = 'allow' | 'review' | 'block';
export type PolicyViolationSeverity = 'blocking' | 'error' | 'warning';

export interface PolicyConstraintBundle {
  retry_policy?: {
    max_attempts?: number;
  };
  budget?: {
    max_tokens?: number;
    max_tokens_critical?: number;
  };
  required_approvals?: {
    required_for_risk_levels?: RiskLevel[];
  };
  required_evidence?: {
    required_for_risk_levels?: RiskLevel[];
  };
  circuit_breaker?: {
    required_for_risk_levels?: RiskLevel[];
  };
}

export interface PolicyViolation {
  node_id: string;
  rule_id: string;
  severity: PolicyViolationSeverity;
  detail: string;
  resolution: string;
}

export interface PolicyAutoResolution {
  node_id: string;
  action: string;
  reason: string;
}

export interface SerializedExecutionEdge {
  from: string;
  to: string;
  reason: string;
}

export interface PolicyEnforcementOptions {
  timestamp?: string;
  granted_approvals?: string[];
  evidence_refs?: string[];
}

export interface PolicyGuardianReport {
  policy_guardian_report: {
    dag_id: string;
    timestamp: string;
    nodes_checked: number;
    violations_found: number;
    violations: PolicyViolation[];
    auto_resolved: PolicyAutoResolution[];
    effective_execution_order: string[];
    serialized_edges: SerializedExecutionEdge[];
    approved: boolean;
    decision: PolicyDecision;
  };
}

const DEFAULT_APPROVAL_RISKS: RiskLevel[] = ['high', 'critical'];
const DEFAULT_EVIDENCE_RISKS: RiskLevel[] = ['medium', 'high', 'critical'];
const DEFAULT_CIRCUIT_BREAKER_RISKS: RiskLevel[] = ['medium', 'high', 'critical'];

function normalizeScopePath(scope: string): string {
  if (scope.trim() === '' || scope === '.' || scope === './') return '.';
  const normalized = path.posix.normalize(scope.replace(/\\/g, '/'));
  if (normalized === '.' || normalized === '/') return normalized;
  const trimmed = normalized.replace(/\/+$/, '');
  return scope.endsWith('/') ? `${trimmed}/` : trimmed;
}

function scopesOverlap(left: string, right: string): boolean {
  const normalizedLeft = normalizeScopePath(left);
  const normalizedRight = normalizeScopePath(right);

  if (normalizedLeft === normalizedRight) return true;
  if (normalizedLeft === '.' || normalizedRight === '.') return true;

  if (normalizedLeft.endsWith('/')) {
    return normalizedRight.startsWith(normalizedLeft);
  }

  if (normalizedRight.endsWith('/')) {
    return normalizedLeft.startsWith(normalizedRight);
  }

  return normalizedLeft.startsWith(`${normalizedRight}/`) || normalizedRight.startsWith(`${normalizedLeft}/`);
}

function hasIntersection(left: string[], right: string[]): boolean {
  return left.some((leftValue) => right.some((rightValue) => scopesOverlap(leftValue, rightValue)));
}

function buildAncestorMap(nodes: TaskNode[]): Map<string, Set<string>> {
  const nodeMap = new Map(nodes.map((node) => [node.task_id, node]));
  const ancestors = new Map<string, Set<string>>();
  const visiting = new Set<string>();

  function visit(taskId: string): Set<string> {
    const cached = ancestors.get(taskId);
    if (cached) return cached;
    if (visiting.has(taskId)) {
      throw new Error(`Circular dependency detected in policy preflight at node "${taskId}"`);
    }

    const node = nodeMap.get(taskId);
    const result = new Set<string>();
    if (!node) {
      throw new Error(`Unknown dependency detected in policy preflight at node "${taskId}"`);
    }

    visiting.add(taskId);

    for (const dependency of node.dependencies) {
      result.add(dependency);
      for (const ancestor of visit(dependency)) {
        result.add(ancestor);
      }
    }

    visiting.delete(taskId);
    ancestors.set(taskId, result);
    return result;
  }

  for (const node of nodes) {
    visit(node.task_id);
  }

  return ancestors;
}

function canRunInParallel(left: TaskNode, right: TaskNode, ancestors: Map<string, Set<string>>): boolean {
  const leftAncestors = ancestors.get(left.task_id) ?? new Set<string>();
  const rightAncestors = ancestors.get(right.task_id) ?? new Set<string>();
  return !leftAncestors.has(right.task_id) && !rightAncestors.has(left.task_id);
}

function riskRequires(level: RiskLevel, requiredFor: RiskLevel[]): boolean {
  return requiredFor.includes(level);
}

function normalizeNodes(dagOrNodes: CompiledDAG | TaskNode[]): { dag_id: string; nodes: TaskNode[] } {
  if (Array.isArray(dagOrNodes)) {
    return { dag_id: 'detached-dag', nodes: dagOrNodes };
  }
  return { dag_id: dagOrNodes.dag_id, nodes: dagOrNodes.nodes };
}

function buildDependencyMap(nodes: TaskNode[]): Map<string, Set<string>> {
  return new Map(nodes.map((node) => [node.task_id, new Set(node.dependencies)]));
}

function buildAncestorMapFromDependencies(
  nodes: TaskNode[],
  dependencyMap: Map<string, Set<string>>,
): Map<string, Set<string>> {
  const nodeMap = new Map(nodes.map((node) => [node.task_id, node]));
  const ancestors = new Map<string, Set<string>>();
  const visiting = new Set<string>();

  function visit(taskId: string): Set<string> {
    const cached = ancestors.get(taskId);
    if (cached) return cached;
    if (visiting.has(taskId)) {
      throw new Error(`Circular dependency detected in policy preflight at node "${taskId}"`);
    }

    if (!nodeMap.has(taskId)) {
      throw new Error(`Unknown dependency detected in policy preflight at node "${taskId}"`);
    }

    visiting.add(taskId);
    const result = new Set<string>();
    const dependencies = dependencyMap.get(taskId) ?? new Set<string>();

    for (const dependency of dependencies) {
      if (!nodeMap.has(dependency)) {
        throw new Error(`Unknown dependency detected in policy preflight at node "${dependency}"`);
      }
      result.add(dependency);
      for (const ancestor of visit(dependency)) {
        result.add(ancestor);
      }
    }

    visiting.delete(taskId);
    ancestors.set(taskId, result);
    return result;
  }

  for (const node of nodes) {
    visit(node.task_id);
  }

  return ancestors;
}

function getPreferredExecutionOrder(dagOrNodes: CompiledDAG | TaskNode[], nodes: TaskNode[]): string[] {
  if (!Array.isArray(dagOrNodes)) {
    const dagOrder = dagOrNodes.execution_order.filter((taskId) => nodes.some((node) => node.task_id === taskId));
    if (dagOrder.length === nodes.length && new Set(dagOrder).size === nodes.length) {
      return dagOrder;
    }
  }

  return nodes.map((node) => node.task_id).sort((left, right) => left.localeCompare(right));
}

function topologicalSort(
  nodes: TaskNode[],
  dependencyMap: Map<string, Set<string>>,
  preferredOrder: string[],
): string[] {
  const nodeMap = new Map(nodes.map((node) => [node.task_id, node]));
  const preference = new Map(preferredOrder.map((taskId, index) => [taskId, index]));
  const inDegree = new Map<string, number>();
  const dependents = new Map<string, string[]>();

  for (const node of nodes) {
    inDegree.set(node.task_id, 0);
    dependents.set(node.task_id, []);
  }

  for (const [taskId, dependencies] of dependencyMap.entries()) {
    if (!nodeMap.has(taskId)) {
      throw new Error(`Unknown dependency detected in policy preflight at node "${taskId}"`);
    }

    for (const dependency of dependencies) {
      if (!nodeMap.has(dependency)) {
        throw new Error(`Unknown dependency detected in policy preflight at node "${dependency}"`);
      }
      inDegree.set(taskId, (inDegree.get(taskId) ?? 0) + 1);
      dependents.get(dependency)?.push(taskId);
    }
  }

  const compareTaskIds = (left: string, right: string): number => {
    const leftRank = preference.get(left) ?? Number.MAX_SAFE_INTEGER;
    const rightRank = preference.get(right) ?? Number.MAX_SAFE_INTEGER;
    if (leftRank !== rightRank) {
      return leftRank - rightRank;
    }
    return left.localeCompare(right);
  };

  const ready = [...nodes.map((node) => node.task_id).filter((taskId) => (inDegree.get(taskId) ?? 0) === 0)].sort(compareTaskIds);
  const ordered: string[] = [];

  while (ready.length > 0) {
    const taskId = ready.shift() as string;
    ordered.push(taskId);

    for (const dependent of dependents.get(taskId) ?? []) {
      const nextDegree = (inDegree.get(dependent) ?? 0) - 1;
      inDegree.set(dependent, nextDegree);
      if (nextDegree === 0) {
        ready.push(dependent);
        ready.sort(compareTaskIds);
      }
    }
  }

  if (ordered.length !== nodes.length) {
    throw new Error('Circular dependency detected in policy preflight while deriving effective execution order');
  }

  return ordered;
}

export function enforcePolicyPreflight(
  dagOrNodes: CompiledDAG | TaskNode[],
  policyBundle: PolicyConstraintBundle = {},
  options: PolicyEnforcementOptions = {},
): PolicyGuardianReport {
  const { dag_id, nodes } = normalizeNodes(dagOrNodes);
  const violations: PolicyViolation[] = [];
  const auto_resolved: PolicyAutoResolution[] = [];
  const serialized_edges: SerializedExecutionEdge[] = [];
  const grantedApprovals = new Set(options.granted_approvals ?? []);
  const evidenceRefs = new Set(options.evidence_refs ?? []);
  const maxAttempts = policyBundle.retry_policy?.max_attempts ?? 3;
  const criticalMaxTokens =
    policyBundle.budget?.max_tokens_critical ?? policyBundle.budget?.max_tokens ?? 8192;
  const approvalRisks = policyBundle.required_approvals?.required_for_risk_levels ?? DEFAULT_APPROVAL_RISKS;
  const evidenceRisks = policyBundle.required_evidence?.required_for_risk_levels ?? DEFAULT_EVIDENCE_RISKS;
  const circuitBreakerRisks =
    policyBundle.circuit_breaker?.required_for_risk_levels ?? DEFAULT_CIRCUIT_BREAKER_RISKS;

  for (const node of nodes) {
    if (node.conformance_checks.some((check) => check.includes('forbidden_transition_check: BLOCKED'))) {
      violations.push({
        node_id: node.task_id,
        rule_id: 'forbidden_transition_check',
        severity: 'blocking',
        detail: `Node "${node.task_id}" contains a forbidden transition check marked as BLOCKED.`,
        resolution: 'Remove the forbidden transition or redesign the behavior before execution.',
      });
    }

    if (riskRequires(node.risk_level, approvalRisks) && node.required_approvals.length > 0) {
      const missingApprovals = node.required_approvals.filter((approval) => !grantedApprovals.has(approval));
      if (missingApprovals.length > 0) {
        violations.push({
          node_id: node.task_id,
          rule_id: 'required_approvals',
          severity: 'error',
          detail: `Node "${node.task_id}" is missing approval(s): ${missingApprovals.join(', ')}.`,
          resolution: 'Collect the required approvals before scheduling this node.',
        });
      }
    }

    if (riskRequires(node.risk_level, evidenceRisks) && node.required_evidence.length > 0) {
      const missingEvidence = node.required_evidence.filter((ref) => !evidenceRefs.has(ref));
      if (missingEvidence.length > 0) {
        violations.push({
          node_id: node.task_id,
          rule_id: 'required_evidence',
          severity: 'error',
          detail: `Node "${node.task_id}" is missing evidence reference(s): ${missingEvidence.join(', ')}.`,
          resolution: 'Attach the required evidence before execution.',
        });
      }
    }

    if (node.retry_policy.max_attempts > maxAttempts) {
      violations.push({
        node_id: node.task_id,
        rule_id: 'retry_policy.max_attempts',
        severity: 'error',
        detail: `Node "${node.task_id}" exceeds retry_policy.max_attempts (${node.retry_policy.max_attempts} > ${maxAttempts}).`,
        resolution: 'Lower max_attempts to the policy limit.',
      });
    }

    if (node.risk_level === 'critical' && node.budget.max_tokens > criticalMaxTokens) {
      violations.push({
        node_id: node.task_id,
        rule_id: 'budget.max_tokens',
        severity: 'error',
        detail: `Critical node "${node.task_id}" exceeds max token budget (${node.budget.max_tokens} > ${criticalMaxTokens}).`,
        resolution: 'Reduce the token budget or lower the node risk before execution.',
      });
    }

    if (riskRequires(node.risk_level, circuitBreakerRisks) && !node.retry_policy.circuit_breaker) {
      violations.push({
        node_id: node.task_id,
        rule_id: 'retry_policy.circuit_breaker',
        severity: 'error',
        detail: `Node "${node.task_id}" requires circuit_breaker=true for risk level "${node.risk_level}".`,
        resolution: 'Enable the circuit breaker before execution.',
      });
    }
  }

  let effective_execution_order = getPreferredExecutionOrder(dagOrNodes, nodes);

  try {
    const dependencyMap = buildDependencyMap(nodes);
    const nodeMap = new Map(nodes.map((node) => [node.task_id, node]));

    // Pre-validate: detect orphan dependencies before serialization
    for (const node of nodes) {
      for (const dep of node.dependencies) {
        if (!nodeMap.has(dep)) {
          violations.push({
            node_id: node.task_id,
            rule_id: 'orphan_dependency',
            severity: 'blocking',
            detail: `Node "${node.task_id}" depends on unknown node "${dep}".`,
            resolution: 'Remove the orphan dependency or add the missing node before policy validation.',
          });
        }
      }
    }

    // Only proceed with serialization if no orphan deps exist
    if (!violations.some((v) => v.rule_id === 'orphan_dependency')) {
      let ancestors = buildAncestorMapFromDependencies(nodes, dependencyMap);
      const orderedNodes = effective_execution_order
        .map((taskId) => nodeMap.get(taskId))
        .filter((node): node is TaskNode => Boolean(node));

      // Batch collect all serialization edges first
      const pendingEdges: Array<{left: TaskNode; right: TaskNode}> = [];
      for (let i = 0; i < orderedNodes.length; i++) {
        for (let j = i + 1; j < orderedNodes.length; j++) {
          const left = orderedNodes[i];
          const right = orderedNodes[j];
          if (!canRunInParallel(left, right, ancestors)) continue;
          if (!hasIntersection(left.write_scope, right.write_scope)) continue;
          pendingEdges.push({ left, right });
        }
      }

      // Apply all edges at once, then rebuild ancestors once
      for (const { left, right } of pendingEdges) {
        const rightDependencies = dependencyMap.get(right.task_id);
        if (!rightDependencies) {
          violations.push({
            node_id: right.task_id,
            rule_id: 'serialized_execution_missing_node',
            severity: 'blocking',
            detail: `Unable to derive serialized execution plan for node "${right.task_id}".`,
            resolution: 'Repair the DAG node map before policy validation.',
          });
          continue;
        }
        rightDependencies.add(left.task_id);
      }

      if (pendingEdges.length > 0) {
        ancestors = buildAncestorMapFromDependencies(nodes, dependencyMap);
        for (const { left, right } of pendingEdges) {
          serialized_edges.push({
            from: left.task_id,
            to: right.task_id,
            reason: `serialize overlapping write_scope between "${left.task_id}" and "${right.task_id}"`,
          });
          auto_resolved.push({
            node_id: `${left.task_id},${right.task_id}`,
            action: 'serialized_parallel_execution',
            reason: `Derived effective dependency ${left.task_id} -> ${right.task_id} to serialize overlapping write_scope.`,
          });
        }
      }

      effective_execution_order = topologicalSort(nodes, dependencyMap, effective_execution_order);
    }
  } catch (error) {
    const message = (error as Error).message;
    const ruleId = message.includes('orphan') ? 'orphan_dependency' : 'dag_cycle';
    violations.push({
      node_id: dag_id,
      rule_id: ruleId,
      severity: 'blocking',
      detail: message,
      resolution: 'Remove the cycle or orphan dependency from the DAG before policy validation.',
    });
  }

  const hasBlocking = violations.some((violation) => violation.severity === 'blocking');
  const hasErrors = violations.some((violation) => violation.severity === 'error');
  const decision: PolicyDecision = hasBlocking || hasErrors ? 'block' : 'allow';

  return {
    policy_guardian_report: {
      dag_id,
      timestamp: options.timestamp ?? new Date().toISOString(),
      nodes_checked: nodes.length,
      violations_found: violations.length,
      violations,
      auto_resolved,
      effective_execution_order,
      serialized_edges,
      approved: decision === 'allow',
      decision,
    },
  };
}
