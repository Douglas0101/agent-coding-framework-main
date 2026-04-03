import { canAutoApprove, type SpecDiffResult } from './spec-diff.js';
import type { ImpactReport } from './impact-analyzer.js';
import type { PolicyGuardianReport } from './policy-enforcer.js';
import type { CompiledDAG } from './spec-compiler.js';
import { assertMinimumLinks } from './spec-linker.js';
import type { SpecStatus, SpecValidationResult } from './spec-registry.js';

export type ApprovalDecision = 'allow' | 'review' | 'block';

export interface ApprovalGateInput {
  current_dag_id?: string;
  current_spec_id?: string;
  run_id?: string;
  minimum_traceability_score?: number;
  human_approval_granted?: boolean;
  spec_status?: SpecStatus;
  validation?: SpecValidationResult;
  diff?: SpecDiffResult;
  impact?: ImpactReport;
  dag?: Pick<CompiledDAG, 'policy_violations' | 'requires_human_approval' | 'nodes'>;
  resolved_approvals?: string[];
  resolved_evidence?: string[];
  policy_report?: PolicyGuardianReport;
}

export interface ApprovalGateResult {
  decision: ApprovalDecision;
  reasons: string[];
  validation: SpecValidationResult;
  signals: {
    spec_status?: SpecStatus;
    compatibility?: string;
    risk_level?: string;
    requires_human_approval: boolean;
    policy_violation_count: number;
    traceability_score?: number;
  };
}

function hasMatchingPolicyReport(input: ApprovalGateInput): boolean {
  return (
    input.current_dag_id !== undefined &&
    input.policy_report?.policy_guardian_report.dag_id === input.current_dag_id
  );
}

function hasPendingEvidence(input: ApprovalGateInput): boolean {
  const resolvedEvidence = new Set(input.resolved_evidence ?? []);
  return (
    input.dag?.nodes.some((node) =>
      node.required_evidence.some((evidence) => !resolvedEvidence.has(evidence)),
    ) ?? false
  );
}

function hasPendingApprovals(input: ApprovalGateInput): boolean {
  const resolvedApprovals = new Set(input.resolved_approvals ?? []);
  const genericApprovalPending =
    input.dag?.requires_human_approval === true &&
    (input.dag.nodes.every((node) => node.required_approvals.length === 0) ?? true) &&
    input.human_approval_granted !== true;

  return (
    input.dag?.nodes.some((node) =>
      node.required_approvals.some((approval) => !resolvedApprovals.has(approval)),
    ) ||
    genericApprovalPending ||
    false
  );
}

function hasUncorrelatedPolicyReport(input: ApprovalGateInput): boolean {
  return input.policy_report !== undefined && !hasMatchingPolicyReport(input);
}

function requiresTraceabilityGate(input: ApprovalGateInput): boolean {
  if (input.impact?.payload.risk_level === 'critical') {
    return true;
  }

  return (
    input.dag?.nodes.some((node) => node.risk_level === 'critical' || node.type === 'release') ??
    false
  );
}

export function evaluateApprovalGate(input: ApprovalGateInput): ApprovalGateResult {
  const validation = input.validation ?? { valid: true, errors: [] };
  const reasons: string[] = [];
  const specStatus = input.spec_status;
  const compatibility = input.impact?.compatibility_assessment ?? input.diff?.classification;
  const riskLevel = input.impact?.payload.risk_level;
  const pendingApprovals = hasPendingApprovals(input);
  const pendingEvidence = hasPendingEvidence(input);
  const matchingPolicyReport = hasMatchingPolicyReport(input);
  const uncorrelatedPolicyReport = hasUncorrelatedPolicyReport(input);
  const dagPolicyViolationCount = input.dag?.policy_violations.length ?? 0;
  const traceabilityRequired = requiresTraceabilityGate(input);
  const reportPolicyViolationCount = matchingPolicyReport
    ? (input.policy_report?.policy_guardian_report.violations_found ?? 0)
    : undefined;
  const policyViolationCount = Math.max(dagPolicyViolationCount, reportPolicyViolationCount ?? 0);
  let traceabilityScore: number | undefined;
  let traceabilityBlocked = false;

  if (!validation.valid) {
    reasons.push(...validation.errors);
  }

  if (specStatus && specStatus !== 'approved') {
    reasons.push(`Spec status "${specStatus}" cannot pass the approval gate.`);
  }

  if (policyViolationCount > 0) {
    reasons.push(`Compiled DAG has ${policyViolationCount} policy violation(s).`);
  }

  if (
    matchingPolicyReport &&
    reportPolicyViolationCount !== undefined &&
    reportPolicyViolationCount !== dagPolicyViolationCount
  ) {
    reasons.push('DAG policy violations diverge from the matching policy guardian report.');
  }

  if (uncorrelatedPolicyReport) {
    reasons.push('Policy guardian report requires a matching current_dag_id.');
  }

  if (matchingPolicyReport && input.policy_report?.policy_guardian_report.decision === 'block') {
    reasons.push('Policy guardian reported a blocking decision.');
  }

  if (compatibility === 'breaking') {
    reasons.push('Breaking compatibility assessment requires an explicit block.');
  }

  if (riskLevel === 'critical') {
    reasons.push('Critical impact requires manual intervention before execution.');
  }

  if (traceabilityRequired) {
    if (!input.current_spec_id || !input.run_id) {
      reasons.push('Critical execution requires traceability context (spec_id + run_id).');
      traceabilityBlocked = true;
    } else {
      const traceabilityValidation = assertMinimumLinks(
        input.current_spec_id,
        input.run_id,
        input.minimum_traceability_score ?? 0.75,
      );

      traceabilityScore = traceabilityValidation.completeness_score;
      if (!traceabilityValidation.valid) {
        reasons.push(...traceabilityValidation.errors);
        traceabilityBlocked = true;
      }
    }
  }

  const shouldBlock =
    !validation.valid ||
    (specStatus !== undefined && specStatus !== 'approved') ||
    policyViolationCount > 0 ||
    uncorrelatedPolicyReport ||
    (matchingPolicyReport &&
      reportPolicyViolationCount !== undefined &&
      reportPolicyViolationCount !== dagPolicyViolationCount) ||
    (matchingPolicyReport && input.policy_report?.policy_guardian_report.decision === 'block') ||
    traceabilityBlocked ||
    compatibility === 'breaking' ||
    riskLevel === 'critical';

  if (shouldBlock) {
    return {
      decision: 'block',
      reasons,
      validation,
      signals: {
        spec_status: specStatus,
        compatibility,
        risk_level: riskLevel,
        requires_human_approval: pendingApprovals,
        policy_violation_count: policyViolationCount,
        traceability_score: traceabilityScore,
      },
    };
  }

  if (input.diff && !canAutoApprove(input.diff)) {
    reasons.push('Spec diff requires human review before approval.');
  }

  if (riskLevel === 'high') {
    reasons.push('High impact requires review before continuing.');
  }

  if (pendingApprovals) {
    reasons.push('Required approvals are still pending.');
  }

  if (pendingEvidence) {
    reasons.push('Required evidence is still pending.');
  }

  const shouldReview = reasons.length > 0;

  return {
    decision: shouldReview ? 'review' : 'allow',
    reasons,
    validation,
    signals: {
      spec_status: specStatus,
      compatibility,
      risk_level: riskLevel,
      requires_human_approval: pendingApprovals,
      policy_violation_count: policyViolationCount,
      traceability_score: traceabilityScore,
    },
  };
}
