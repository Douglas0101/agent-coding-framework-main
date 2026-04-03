/**
 * spec-compiler.ts
 *
 * Compiles a set of versioned specs (behavior + policy + verification) into a
 * typed DAG of TaskNodes. Each node carries:
 *  - inherited invariants from the capability spec
 *  - policy constraints resolved from the policy bundle
 *  - required evidence and conformance checks from the verification spec
 *  - retry policy, budget, and risk_level derived from spec metadata
 *
 * The compiler is deterministic: given the same spec inputs, it always
 * produces the same DAG topology. This is critical for reproducibility.
 *
 * No external runtime dependencies.
 */

import { getSpec, validateSpec, assertSpecApproved, SpecType } from './spec-registry.js';
import {
  appendToLink,
  createLink,
  resolveLink,
  type LinkerValidationResult,
  type TraceabilityLink,
} from './spec-linker.js';
import {
  buildInitialRunManifest,
  type RunManifest,
  type RunManifestAgentActivation,
  type RunManifestArtifact,
} from './run-manifest.js';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type NodeType =
  | 'discovery'
  | 'analysis'
  | 'implementation'
  | 'validation'
  | 'synthesis'
  | 'release';

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export type BackoffStrategy = 'fixed' | 'exponential';

export interface RetryPolicy {
  max_attempts: number;
  backoff: BackoffStrategy;
  circuit_breaker: boolean;
}

export interface Budget {
  max_tokens: number;
  max_cost_usd: number;
  timeout_ms: number;
}

export interface TaskNode {
  task_id: string;
  /** Spec IDs and versions that derived this node */
  derived_from_specs: string[];
  type: NodeType;
  label: string;
  inputs: Record<string, unknown>;
  dependencies: string[];
  write_scope: string[];
  invariants: string[];
  admissible_outputs: string[];
  retry_policy: RetryPolicy;
  budget: Budget;
  required_evidence: string[];
  required_approvals: string[];
  conformance_checks: string[];
  risk_level: RiskLevel;
}

export interface CompiledDAG {
  dag_id: string;
  spec_id: string;
  spec_version: string;
  compiled_at: string;
  nodes: TaskNode[];
  /** Topological execution order (task_id list) */
  execution_order: string[];
  /** Policy violations detected during compilation (non-empty = blocked) */
  policy_violations: string[];
  /** Flag: any node requires human approval */
  requires_human_approval: boolean;
}

export interface CompilerResult {
  success: boolean;
  dag?: CompiledDAG;
  errors: string[];
  warnings: string[];
}

export interface CompilerTraceabilityResult extends CompilerResult {
  traceability_link?: TraceabilityLink;
  traceability_validation?: LinkerValidationResult;
  run_manifest?: RunManifest;
}

export interface CompileDAGWithRunManifestOptions {
  timestamp?: string;
  agents_activated?: RunManifestAgentActivation[];
  artifacts_produced?: RunManifestArtifact[];
  budget?: RunManifest['budget'];
  risk_level?: RunManifest['risk_level'];
  remaining_risks?: string[];
  next_steps?: string[];
  requirement_refs?: string[];
  code_refs?: string[];
  test_cases?: string[];
  evidence_refs?: string[];
  runtime_trace_ids?: string[];
  owner_technical?: string;
  owner_domain?: string;
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function deriveRiskLevel(
  invariantCount: number,
  hasForbiddenTransitions: boolean,
  policyRules: Record<string, unknown>[],
): RiskLevel {
  const criticalRules = policyRules.filter(
    (r) => (r['action'] === 'require_approval' || r['action'] === 'block_direct_write'),
  );
  if (criticalRules.length > 0) return 'critical';
  if (hasForbiddenTransitions || invariantCount > 3) return 'high';
  if (invariantCount > 1) return 'medium';
  return 'low';
}

function buildNodeId(prefix: string, index: number): string {
  return `${prefix}_${String(index).padStart(3, '0')}`;
}

function toStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0);
}

function uniqueNonEmptyStrings(values: string[]): string[] {
  return [...new Set(values.filter((value) => value.trim().length > 0))];
}

function extractTraceabilityDefaults(payload: Record<string, unknown>): {
  requirement_refs: string[];
  owner_technical: string;
  owner_domain: string;
} {
  const traceability = payload['traceability'];
  if (!traceability || typeof traceability !== 'object' || Array.isArray(traceability)) {
    return {
      requirement_refs: [],
      owner_technical: '',
      owner_domain: '',
    };
  }

  const record = traceability as Record<string, unknown>;
  return {
    requirement_refs: toStringArray(record['requirement_refs']),
    owner_technical:
      typeof record['owner_technical'] === 'string' ? record['owner_technical'] : '',
    owner_domain: typeof record['owner_domain'] === 'string' ? record['owner_domain'] : '',
  };
}

function summarizeLinkValidation(link: TraceabilityLink): LinkerValidationResult {
  const errors = link.missing_links
    .filter((gap) => gap.severity === 'blocking' || gap.severity === 'error')
    .map((gap) => gap.description);
  const warnings = link.missing_links
    .filter((gap) => gap.severity === 'warning')
    .map((gap) => gap.description);

  return {
    valid: errors.length === 0,
    errors,
    warnings,
    completeness_score: link.completeness_score,
  };
}

function topoSort(nodes: TaskNode[]): string[] {
  const result: string[] = [];
  const visited = new Set<string>();
  const nodeMap = new Map(nodes.map((n) => [n.task_id, n]));

  function visit(id: string, ancestors: Set<string>): void {
    if (visited.has(id)) return;
    if (ancestors.has(id)) {
      throw new Error(`Circular dependency detected at node "${id}"`);
    }
    const node = nodeMap.get(id);
    if (!node) throw new Error(`Unknown dependency node: "${id}"`);
    ancestors.add(id);
    for (const dep of node.dependencies) {
      visit(dep, new Set(ancestors));
    }
    visited.add(id);
    result.push(id);
  }

  for (const node of nodes) {
    visit(node.task_id, new Set());
  }

  return result;
}

// ---------------------------------------------------------------------------
// Core compiler logic
// ---------------------------------------------------------------------------

/**
 * Derives TaskNodes from a BehaviorSpec state machine.
 * Each state transition becomes an analysis or implementation node.
 * Terminal states become validation or synthesis nodes.
 */
function compileFromBehavior(
  behaviorPayload: Record<string, unknown>,
  invariants: string[],
  riskLevel: RiskLevel,
  specRef: string,
): TaskNode[] {
  const transitions = (behaviorPayload['transitions'] as Array<Record<string, unknown>>) ?? [];
  const terminalStates = (behaviorPayload['terminal_states'] as string[]) ?? [];
  const timeoutMs = (behaviorPayload['timeout_ms'] as number) ?? 5000;
  const forbidden = (behaviorPayload['forbidden'] as Array<Record<string, unknown>>) ?? [];

  const nodes: TaskNode[] = [];
  const seenTransitions = new Set<string>();

  for (let i = 0; i < transitions.length; i++) {
    const t = transitions[i];
    const from = t['from'] as string;
    const to = t['to'] as string;
    const transKey = `${from}->${to}`;

    if (seenTransitions.has(transKey)) continue;
    seenTransitions.add(transKey);

    const isTerminal = terminalStates.includes(to);
    const nodeType: NodeType = isTerminal ? 'validation' : 'implementation';
    const task_id = buildNodeId(`${from}_to_${to}`.replace(/\s+/g, '_'), i);

    // Dependency: find all previously compiled nodes whose write_scope contains `from`.
    // This correctly models data-flow: a node that produces state X must complete
    // before any node that consumes state X as its input.
    const deps = nodes
      .filter((n) => n.write_scope.includes(from))
      .map((n) => n.task_id);

    const conformanceChecks: string[] = [
      `transition_allowed: ${from} -> ${to}`,
      ...(t['guard'] ? [`guard_satisfied: ${t['guard']}`] : []),
    ];

    // Add forbidden transition check
    const isForbiddenPath = forbidden.some((f) => f['from'] === from && f['to'] === to);
    if (isForbiddenPath) {
      conformanceChecks.push(`forbidden_transition_check: BLOCKED (${from} -> ${to})`);
    }

    nodes.push({
      task_id,
      derived_from_specs: [specRef],
      type: nodeType,
      label: t['action'] ? String(t['action']) : `transition: ${from} → ${to}`,
      inputs: { from_state: from, to_state: to, guard: t['guard'] ?? null },
      dependencies: deps,
      write_scope: [to],
      invariants: [...invariants],
      admissible_outputs: [to, ...(t['action'] ? [String(t['action'])] : [])],
      retry_policy: {
        max_attempts: riskLevel === 'critical' ? 1 : 3,
        backoff: 'exponential',
        circuit_breaker: riskLevel !== 'low',
      },
      budget: {
        max_tokens: 4096,
        max_cost_usd: 0.05,
        timeout_ms: timeoutMs,
      },
      required_evidence: riskLevel === 'low' ? [] : [`evidence://transition/${transKey}`],
      required_approvals: isForbiddenPath ? ['tech-lead'] : [],
      conformance_checks: conformanceChecks,
      risk_level: isForbiddenPath ? 'critical' : riskLevel,
    });
  }

  return nodes;
}

/**
 * Merges policy rules into existing nodes, adding required_approvals,
 * required_evidence and policy violations list.
 */
function applyPolicyBundle(
  nodes: TaskNode[],
  policyPayload: Record<string, unknown>,
): { nodes: TaskNode[]; violations: string[] } {
  const rules = (policyPayload['rules'] as Array<Record<string, unknown>>) ?? [];
  const violations: string[] = [];

  const updatedNodes = nodes.map((node) => {
    const updatedNode = { ...node };

    for (const rule of rules) {
      const when = (rule['when'] as Record<string, unknown>) ?? {};
      const riskLevels = (when['risk_level'] as string[]) ?? [];
      const nodeTypes = (when['node_type'] as string[]) ?? [];

      // Check if rule applies: BOTH conditions must match when specified.
      // An empty list means "match all" for that dimension.
      // Using OR to skip: skip if either specified condition does NOT match.
      const appliesToRisk = riskLevels.length === 0 || riskLevels.includes(node.risk_level);
      const appliesToType = nodeTypes.length === 0 || nodeTypes.includes(node.type);

      if (!appliesToRisk || !appliesToType) continue;

      const action = rule['action'] as string;

      if (action === 'require_approval') {
        const approvers = (rule['approvers'] as string[]) ?? [];
        updatedNode.required_approvals = [
          ...new Set([...updatedNode.required_approvals, ...approvers]),
        ];
      }

      if (action === 'require_evidence') {
        const evidenceTypes = (rule['evidence_types'] as string[]) ?? [];
        updatedNode.required_evidence = [
          ...new Set([...updatedNode.required_evidence, ...evidenceTypes]),
        ];
      }

      if (action === 'require') {
        const constraint = (rule['constraint'] as Record<string, unknown>) ?? {};
        // Enforce max retry constraint
        const maxRetries = constraint['retry_policy.max_attempts_lte'] as number | undefined;
        if (maxRetries !== undefined && updatedNode.retry_policy.max_attempts > maxRetries) {
          violations.push(
            `Policy "${rule['id']}": node "${node.task_id}" has max_attempts=${node.retry_policy.max_attempts} ` +
              `but policy requires <= ${maxRetries}`,
          );
          updatedNode.retry_policy = { ...updatedNode.retry_policy, max_attempts: maxRetries };
        }
      }

      if (action === 'block_direct_write') {
        violations.push(
          `Policy "${rule['id']}": node "${node.task_id}" blocked — ${rule['error'] ?? 'direct write forbidden'}`,
        );
      }
    }

    return updatedNode;
  });

  return { nodes: updatedNodes, violations };
}

/**
 * Merges verification spec into nodes: adds conformance checks and required evidence.
 */
function applyVerificationSpec(
  nodes: TaskNode[],
  verificationPayload: Record<string, unknown>,
): TaskNode[] {
  const acceptanceCriteria = (verificationPayload['acceptance_criteria'] as string[]) ?? [];
  const properties = (verificationPayload['properties'] as Array<Record<string, unknown>>) ?? [];
  const requiredEvidence = (verificationPayload['required_evidence'] as string[]) ?? [];

  // Add acceptance criteria as conformance checks on all nodes
  const criteriaChecks = acceptanceCriteria.map((c) => `acceptance: ${c}`);
  const propertyChecks = properties.map((p) => `property[${p['test_type']}]: ${p['name']}`);

  return nodes.map((node) => ({
    ...node,
    conformance_checks: [
      ...new Set([...node.conformance_checks, ...criteriaChecks, ...propertyChecks]),
    ],
    required_evidence: [...new Set([...node.required_evidence, ...requiredEvidence])],
  }));
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Compiles a full DAG from a trio of specs: behavior + policy + verification.
 * The capability spec must be approved in the registry before compilation proceeds.
 *
 * @param capability_spec_id - The approved capability spec ID (gate check)
 * @param behavior_spec_id   - The behavior spec ID to compile transitions from
 * @param policy_bundle_id   - The policy bundle spec ID to enforce
 * @param verification_spec_id - The verification spec ID to merge
 * @param run_id             - The current run ID for traceability
 */
export function compileDAG(
  capability_spec_id: string,
  behavior_spec_id: string,
  policy_bundle_id: string,
  verification_spec_id: string,
  run_id: string,
): CompilerResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  // --- Gate: capability spec must be approved ---
  const gateResult = assertSpecApproved(capability_spec_id);
  if (!gateResult.valid) {
    return { success: false, errors: gateResult.errors, warnings };
  }

  const capabilityEntry = getSpec(capability_spec_id);
  if (!capabilityEntry) {
    return { success: false, errors: [`Capability spec "${capability_spec_id}" not found`], warnings };
  }

  const behaviorEntry = getSpec(behavior_spec_id);
  if (!behaviorEntry) {
    return { success: false, errors: [`Behavior spec "${behavior_spec_id}" not found or not approved`], warnings };
  }
  if (behaviorEntry.status !== 'approved') {
    return {
      success: false,
      errors: [`Behavior spec "${behavior_spec_id}@${behaviorEntry.version}" is "${behaviorEntry.status}" — must be approved before DAG compilation.`],
      warnings,
    };
  }

  const policyEntry = getSpec(policy_bundle_id);
  if (!policyEntry) {
    warnings.push(`Policy bundle "${policy_bundle_id}" not found; running without policy enforcement.`);
  } else if (policyEntry.status !== 'approved') {
    warnings.push(`Policy bundle "${policy_bundle_id}@${policyEntry.version}" is "${policyEntry.status}"; enforcement may be incomplete.`);
  }

  const verificationEntry = getSpec(verification_spec_id);
  if (!verificationEntry) {
    warnings.push(`Verification spec "${verification_spec_id}" not found; skipping verification merge.`);
  } else if (verificationEntry.status !== 'approved') {
    warnings.push(`Verification spec "${verification_spec_id}@${verificationEntry.version}" is "${verificationEntry.status}"; conformance checks may be incomplete.`);
  }

  // --- Validate behavior spec ---
  const behaviorValidation = validateSpec(behaviorEntry.payload, 'behavior');
  if (!behaviorValidation.valid) {
    return { success: false, errors: behaviorValidation.errors, warnings };
  }

  // --- Extract capability invariants ---
  const invariants = (capabilityEntry.payload['invariants'] as string[]) ?? [];
  const forbidden = (behaviorEntry.payload['forbidden'] as Array<Record<string, unknown>>) ?? [];

  // --- Derive base risk from capability + behavior ---
  const policyRules = policyEntry
    ? ((policyEntry.payload['rules'] as Array<Record<string, unknown>>) ?? [])
    : [];
  const riskLevel = deriveRiskLevel(invariants.length, forbidden.length > 0, policyRules);

  // --- Compile nodes from behavior spec ---
  const specRef = `${behavior_spec_id}@${behaviorEntry.version}`;
  let nodes = compileFromBehavior(behaviorEntry.payload, invariants, riskLevel, specRef);

  if (nodes.length === 0) {
    return {
      success: false,
      errors: ['Behavior spec produced no transitions. DAG compilation aborted.'],
      warnings,
    };
  }

  // --- Apply policy constraints ---
  let policyViolations: string[] = [];
  if (policyEntry) {
    const policyResult = applyPolicyBundle(nodes, policyEntry.payload);
    nodes = policyResult.nodes;
    policyViolations = policyResult.violations;
  }

  // --- Apply verification spec ---
  if (verificationEntry) {
    nodes = applyVerificationSpec(nodes, verificationEntry.payload);
  }

  // --- Topological sort ---
  let executionOrder: string[];
  try {
    executionOrder = topoSort(nodes);
  } catch (e) {
    return {
      success: false,
      errors: [(e as Error).message],
      warnings,
    };
  }

  const requiresApproval = nodes.some((n) => n.required_approvals.length > 0);

  const dag: CompiledDAG = {
    dag_id: `dag_${run_id}_${Date.now()}`,
    spec_id: capability_spec_id,
    spec_version: capabilityEntry.version,
    compiled_at: new Date().toISOString(),
    nodes,
    execution_order: executionOrder,
    policy_violations: policyViolations,
    requires_human_approval: requiresApproval,
  };

  // Soft fail: policy violations are surfaced as errors so consumers can decide
  if (policyViolations.length > 0) {
    return {
      success: false,
      dag,
      errors: policyViolations,
      warnings,
    };
  }

  return { success: true, dag, errors: [], warnings };
}

export async function compileDAGWithRunManifest(
  capability_spec_id: string,
  behavior_spec_id: string,
  policy_bundle_id: string,
  verification_spec_id: string,
  run_id: string,
  options: CompileDAGWithRunManifestOptions = {},
): Promise<CompilerTraceabilityResult> {
  const result = compileDAG(
    capability_spec_id,
    behavior_spec_id,
    policy_bundle_id,
    verification_spec_id,
    run_id,
  );

  if (!result.success || !result.dag) {
    return result;
  }

  const capabilityEntry = getSpec(capability_spec_id);
  const defaults = capabilityEntry
    ? extractTraceabilityDefaults(capabilityEntry.payload)
    : {
        requirement_refs: [],
        owner_technical: '',
        owner_domain: '',
      };

  const traceabilityLinks = {
    requirements: options.requirement_refs ?? defaults.requirement_refs,
    specs: uniqueNonEmptyStrings([
      capability_spec_id,
      behavior_spec_id,
      policy_bundle_id,
      verification_spec_id,
    ]),
    dag_nodes: result.dag.nodes.map((node) => node.task_id),
    code_refs: options.code_refs ?? [],
    test_cases: options.test_cases ?? [],
    evidence_refs: options.evidence_refs ?? [`spec://${capability_spec_id}@${result.dag.spec_version}`],
    runtime_trace_ids: options.runtime_trace_ids ?? [],
    owner_technical: options.owner_technical ?? defaults.owner_technical,
    owner_domain: options.owner_domain ?? defaults.owner_domain,
  };

  const existingLink = resolveLink({ spec_id: capability_spec_id, run_id });
  let traceability:
    | { link: TraceabilityLink; validation: LinkerValidationResult }
    | Awaited<ReturnType<typeof createLink>>;

  if (existingLink) {
    const updatedLink = await appendToLink(capability_spec_id, run_id, traceabilityLinks) ?? existingLink;
    traceability = {
      link: updatedLink,
      validation: summarizeLinkValidation(updatedLink),
    };
  } else {
    traceability = await createLink(capability_spec_id, result.dag.spec_version, run_id, traceabilityLinks);
  }

  const run_manifest = buildInitialRunManifest({
    run_id,
    dag: result.dag,
    traceability_link: traceability.link,
    timestamp: options.timestamp,
    agents_activated: options.agents_activated,
    artifacts_produced: options.artifacts_produced,
    budget: options.budget,
    risk_level: options.risk_level,
    remaining_risks: options.remaining_risks,
    next_steps: options.next_steps,
  });

  return {
    ...result,
    traceability_link: traceability.link,
    traceability_validation: traceability.validation,
    run_manifest,
    warnings: [
      ...result.warnings,
      ...traceability.validation.errors.map((error) => `Traceability bootstrap incomplete: ${error}`),
      ...traceability.validation.warnings.map((warning) => `Traceability bootstrap warning: ${warning}`),
    ],
  };
}
