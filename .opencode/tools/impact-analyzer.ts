import type { ChangeClassification, SpecDiffResult } from './spec-diff.js';
import { canAutoApprove, diffSpecs } from './spec-diff.js';
import { getSpec, getSpecHistory, type SpecEntry } from './spec-registry.js';

export type ImpactRiskLevel = 'low' | 'medium' | 'high' | 'critical';
export type ChangeSurface = 'code' | 'api' | 'data' | 'auth' | 'runtime';

export interface ImpactScope {
  services: string[];
  contracts: string[];
  datastores: string[];
  slos: string[];
}

export interface BlastRadius {
  files: number;
  apis: number;
  consumers: number;
  databases: number;
}

export interface ImpactReport {
  schema_version: string;
  artifact_type: 'impact-report';
  producer_agent: string;
  spec_id: string;
  spec_version: string;
  run_id: string;
  timestamp: string;
  compatibility_assessment: ChangeClassification;
  payload: {
    impact_scope: ImpactScope;
    risk_level: ImpactRiskLevel;
    blast_radius: BlastRadius;
  };
  trace_links: string[];
  evidence_refs: string[];
  checksum?: string;
}

export interface AnalyzeImpactOptions {
  version?: string;
  run_id: string;
  timestamp?: string;
  producer_agent?: string;
  change_surface?: ChangeSurface;
  known_consumers?: string[];
  trace_links?: string[];
  evidence_refs?: string[];
  impact_scope?: Partial<ImpactScope>;
  blast_radius?: Partial<BlastRadius>;
}

export interface ImpactAnalysisResult {
  spec: SpecEntry;
  previous_spec?: SpecEntry;
  diff?: SpecDiffResult;
  auto_approvable: boolean;
  report: ImpactReport;
}

const RISK_SEVERITY: Record<ImpactRiskLevel, number> = {
  low: 0,
  medium: 1,
  high: 2,
  critical: 3,
};

function maxRisk(a: ImpactRiskLevel, b: ImpactRiskLevel): ImpactRiskLevel {
  return RISK_SEVERITY[a] >= RISK_SEVERITY[b] ? a : b;
}

function toStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === 'string');
}

function uniqueSorted(values: string[]): string[] {
  return [...new Set(values)].sort((a, b) => a.localeCompare(b));
}

function extractImpactScope(spec: SpecEntry, options: AnalyzeImpactOptions): ImpactScope {
  const payloadScope = (spec.payload['impact_scope'] as Record<string, unknown> | undefined) ?? {};
  const optionScope = options.impact_scope ?? {};

  const services = uniqueSorted([
    ...toStringArray(payloadScope['services']),
    ...toStringArray(spec.payload['services']),
    ...(typeof optionScope.services?.[0] === 'string' ? optionScope.services : []),
    spec.domain,
  ]);

  const contracts = uniqueSorted([
    ...toStringArray(payloadScope['contracts']),
    ...toStringArray(spec.payload['contracts']),
    ...(typeof optionScope.contracts?.[0] === 'string' ? optionScope.contracts : []),
  ]);

  const datastores = uniqueSorted([
    ...toStringArray(payloadScope['datastores']),
    ...toStringArray(spec.payload['datastores']),
    ...(typeof optionScope.datastores?.[0] === 'string' ? optionScope.datastores : []),
  ]);

  const slos = uniqueSorted([
    ...toStringArray(payloadScope['slos']),
    ...toStringArray(spec.payload['slos']),
    ...(typeof optionScope.slos?.[0] === 'string' ? optionScope.slos : []),
  ]);

  return { services, contracts, datastores, slos };
}

function detectPreviousSpec(spec: SpecEntry): SpecEntry | undefined {
  const history = getSpecHistory(spec.spec_id);
  const currentIndex = history.findIndex((entry) => entry.version === spec.version);
  if (currentIndex <= 0) return undefined;

  for (let index = currentIndex - 1; index >= 0; index--) {
    if (history[index]?.status !== 'approved') continue;
    const candidate = getSpec(spec.spec_id, history[index]?.version);
    if (candidate?.status === 'approved') return candidate;
  }

  return undefined;
}

function resolveTargetSpec(spec_id: string, version?: string): SpecEntry | undefined {
  if (version) {
    return getSpec(spec_id, version);
  }

  const history = getSpecHistory(spec_id);
  const latestVersion = history[history.length - 1]?.version;
  return latestVersion ? getSpec(spec_id, latestVersion) : undefined;
}

function buildComparablePayload(payload: Record<string, unknown>): Record<string, unknown> {
  const comparable = { ...payload };
  delete comparable['version'];
  delete comparable['status'];
  return comparable;
}

function classifyWithoutBaseline(changeSurface: ChangeSurface | undefined): ChangeClassification {
  if (changeSurface === 'api' || changeSurface === 'runtime') return 'risky-compatible';
  if (changeSurface === 'data' || changeSurface === 'auth') return 'breaking';
  if (changeSurface === 'code') return 'behavior-compatible';
  return 'additive-compatible';
}

function deriveBlastRadius(
  spec: SpecEntry,
  impactScope: ImpactScope,
  diff: SpecDiffResult | undefined,
  options: AnalyzeImpactOptions,
): BlastRadius {
  const payloadBlast = (spec.payload['blast_radius'] as Record<string, unknown> | undefined) ?? {};
  const payloadConsumers = toStringArray(spec.payload['consumers']);
  const optionConsumers = options.known_consumers ?? [];
  const evidenceRefs = uniqueSorted(options.evidence_refs ?? []);

  const files =
    options.blast_radius?.files ??
    (typeof payloadBlast['files'] === 'number'
      ? payloadBlast['files']
      : Math.max(
          evidenceRefs.length,
          impactScope.services.length +
            impactScope.contracts.length +
            impactScope.datastores.length +
            impactScope.slos.length +
            (diff?.changes.length ?? 0),
        ));

  const apis =
    options.blast_radius?.apis ??
    (typeof payloadBlast['apis'] === 'number'
      ? payloadBlast['apis']
      : Math.max(
          impactScope.contracts.length,
          diff?.changes.filter((change) => /input|output|contract|api/i.test(change.path)).length ?? 0,
        ));

  const consumers =
    options.blast_radius?.consumers ??
    (typeof payloadBlast['consumers'] === 'number'
      ? payloadBlast['consumers']
      : uniqueSorted([...payloadConsumers, ...optionConsumers]).length);

  const databases =
    options.blast_radius?.databases ??
    (typeof payloadBlast['databases'] === 'number'
      ? payloadBlast['databases']
      : impactScope.datastores.length);

  return { files, apis, consumers, databases };
}

function deriveBaseRisk(spec: SpecEntry, compatibility: ChangeClassification): ImpactRiskLevel {
  const declaredRisk = spec.payload['risk_level'];
  const baseRisk: ImpactRiskLevel =
    declaredRisk === 'low' || declaredRisk === 'medium' || declaredRisk === 'high' || declaredRisk === 'critical'
      ? declaredRisk
      : 'low';

  if (compatibility === 'breaking') return 'critical';
  if (compatibility === 'risky-compatible') return maxRisk(baseRisk, 'medium');
  if (compatibility === 'behavior-compatible') return maxRisk(baseRisk, 'low');
  return baseRisk;
}

function deriveRiskLevel(
  baseRisk: ImpactRiskLevel,
  compatibility: ChangeClassification,
  blastRadius: BlastRadius,
  impactScope: ImpactScope,
): ImpactRiskLevel {
  let risk = baseRisk;

  if (compatibility === 'breaking') return 'critical';
  if (compatibility === 'risky-compatible') risk = maxRisk(risk, 'medium');

  if (
    blastRadius.consumers > 5 ||
    blastRadius.apis > 2 ||
    blastRadius.databases > 1 ||
    impactScope.slos.length > 0
  ) {
    risk = maxRisk(risk, 'high');
  }

  return risk;
}

export function analyzeImpact(spec_id: string, options: AnalyzeImpactOptions): ImpactAnalysisResult {
  const spec = resolveTargetSpec(spec_id, options.version);
  if (!spec) {
    throw new Error(`Spec "${spec_id}"${options.version ? `@${options.version}` : ''} not found`);
  }

  const previousSpec = detectPreviousSpec(spec);
  const diff = previousSpec
    ? diffSpecs(
        spec.spec_id,
        previousSpec.version,
        spec.version,
        buildComparablePayload(previousSpec.payload),
        buildComparablePayload(spec.payload),
        options.known_consumers ?? [],
      )
    : undefined;

  const changeSurface =
    options.change_surface ??
    (typeof spec.payload['change_surface'] === 'string'
      ? (spec.payload['change_surface'] as ChangeSurface)
      : undefined);

  const compatibility = diff?.classification ?? classifyWithoutBaseline(changeSurface);
  const impactScope = extractImpactScope(spec, options);
  const blastRadius = deriveBlastRadius(spec, impactScope, diff, options);
  const riskLevel = deriveRiskLevel(deriveBaseRisk(spec, compatibility), compatibility, blastRadius, impactScope);
  const traceLinks = uniqueSorted([
    ...toStringArray((spec.payload['traceability'] as Record<string, unknown> | undefined)?.['requirement_refs']),
    ...(options.trace_links ?? []),
  ]);
  const evidenceRefs = uniqueSorted(options.evidence_refs ?? [`spec://${spec.spec_id}@${spec.version}`]);

  const report: ImpactReport = {
    schema_version: '1.0.0',
    artifact_type: 'impact-report',
    producer_agent: options.producer_agent ?? 'impact-analyst',
    spec_id: spec.spec_id,
    spec_version: spec.version,
    run_id: options.run_id,
    timestamp: options.timestamp ?? spec.registered_at,
    compatibility_assessment: compatibility,
    payload: {
      impact_scope: impactScope,
      risk_level: riskLevel,
      blast_radius: blastRadius,
    },
    trace_links: traceLinks,
    evidence_refs: evidenceRefs,
  };

  return {
    spec,
    previous_spec: previousSpec,
    diff,
    auto_approvable: diff ? canAutoApprove(diff) : compatibility === 'additive-compatible',
    report,
  };
}
