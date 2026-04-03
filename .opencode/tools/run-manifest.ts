import type { CompiledDAG, RiskLevel } from './spec-compiler.js';
import type { TraceabilityLink } from './spec-linker.js';

export type RunManifestStatus = 'running' | 'completed' | 'failed' | 'cancelled' | 'blocked';

export interface RunManifestAgentActivation {
  agent: string;
  verdict: 'pass' | 'pass_with_notes' | 'fail' | 'skipped';
  confidence?: number;
  duration_ms?: number;
}

export interface RunManifestArtifact {
  artifact_type: string;
  path: string;
  checksum?: string;
}

export interface RunManifest {
  schema_version: string;
  artifact_type: 'run-manifest';
  run_id: string;
  spec_id: string;
  spec_version: string;
  dag_id?: string;
  traceability_link_id?: string;
  timestamp: string;
  status: RunManifestStatus;
  budget?: {
    max_tokens?: number;
    used_tokens?: number;
    max_cost_usd?: number;
    used_cost_usd?: number;
  };
  agents_activated: RunManifestAgentActivation[];
  artifacts_produced: RunManifestArtifact[];
  trace_links?: {
    requirements?: string[];
    code_refs?: string[];
    test_cases?: string[];
    evidence_refs?: string[];
    owner_technical?: string;
    owner_domain?: string;
  };
  traceability_completeness_score?: number;
  risk_level?: RiskLevel;
  remaining_risks?: string[];
  next_steps?: string[];
}

export interface BuildInitialRunManifestInput {
  run_id: string;
  dag: Pick<CompiledDAG, 'dag_id' | 'spec_id' | 'spec_version' | 'nodes'>;
  traceability_link?: Pick<TraceabilityLink, 'link_id' | 'completeness_score' | 'links'>;
  timestamp?: string;
  status?: RunManifestStatus;
  agents_activated?: RunManifestAgentActivation[];
  artifacts_produced?: RunManifestArtifact[];
  budget?: RunManifest['budget'];
  risk_level?: RiskLevel;
  remaining_risks?: string[];
  next_steps?: string[];
}

const RISK_ORDER: Record<RiskLevel, number> = {
  low: 0,
  medium: 1,
  high: 2,
  critical: 3,
};

function toManifestTraceLinks(
  link?: Pick<TraceabilityLink, 'links'>,
): RunManifest['trace_links'] | undefined {
  if (!link) return undefined;

  return {
    requirements: link.links.requirements,
    code_refs: link.links.code_refs,
    test_cases: link.links.test_cases,
    evidence_refs: link.links.evidence_refs,
    owner_technical: link.links.owner_technical,
    owner_domain: link.links.owner_domain,
  };
}

function deriveRiskLevel(dag: Pick<CompiledDAG, 'nodes'>): RiskLevel | undefined {
  const nodeRiskLevels = dag.nodes.map((node) => node.risk_level);
  if (nodeRiskLevels.length === 0) return undefined;

  return nodeRiskLevels.reduce((highest, current) =>
    RISK_ORDER[current] > RISK_ORDER[highest] ? current : highest,
  );
}

export function buildInitialRunManifest(input: BuildInitialRunManifestInput): RunManifest {
  const traceLinks = toManifestTraceLinks(input.traceability_link);
  const riskLevel = input.risk_level ?? deriveRiskLevel(input.dag);

  return {
    schema_version: '1.0.0',
    artifact_type: 'run-manifest',
    run_id: input.run_id,
    spec_id: input.dag.spec_id,
    spec_version: input.dag.spec_version,
    timestamp: input.timestamp ?? new Date().toISOString(),
    status: input.status ?? 'running',
    dag_id: input.dag.dag_id,
    ...(input.traceability_link
      ? {
          traceability_link_id: input.traceability_link.link_id,
          traceability_completeness_score: input.traceability_link.completeness_score,
        }
      : {}),
    ...(input.budget ? { budget: input.budget } : {}),
    agents_activated: input.agents_activated ?? [],
    artifacts_produced: input.artifacts_produced ?? [],
    ...(traceLinks ? { trace_links: traceLinks } : {}),
    ...(riskLevel ? { risk_level: riskLevel } : {}),
    ...(input.remaining_risks ? { remaining_risks: input.remaining_risks } : {}),
    ...(input.next_steps ? { next_steps: input.next_steps } : {}),
  };
}
