import { registerSpec, updateSpecStatus, approveSpec, getSpec, listSpecs, _clearRegistry } from './tools/spec-registry.js';

_clearRegistry();

const policyPayload: Record<string, unknown> = {
  policy_bundle: 'routing-suite-governance',
  version: '1.0.0',
  rules: [
    { id: 'require_evidence_for_routing_fix', description: 'Bug fix de routing requer evidencia', action: 'require_evidence', when: { risk_level: ['critical', 'high'] }, evidence_types: ['test_output', 'live_routing_test'] },
    { id: 'require_approval_for_config_change', description: 'Mudancas em configs requerem aprovacao', action: 'require_approval', when: { paths: ['opencode.json'] }, approvers: ['tech-lead', 'validation'] },
    { id: 'block_direct_write_without_spec', description: 'Nenhuma modificacao sem spec aprovada', action: 'block_direct_write', when: { change_surface: ['routing', 'config'] } },
    { id: 'require_field_in_manifest', description: 'Manifest completeness >= 0.75', action: 'require_field', field: 'traceability_completeness_score', constraint: '>= 0.75' },
  ],
};

// Step 1: Register
console.log('=== STEP 1: REGISTER ===');
const regResult = registerSpec('policy.bugfix.routing-suite', 'policy', '1.0.0', 'draft', 'runtime-routing', policyPayload, 'orchestrator');
console.log('Register result:', JSON.stringify(regResult, null, 2));

// Step 2: Check store after register
console.log('\n=== STEP 2: LIST ALL SPECS AFTER REGISTER ===');
const allAfterReg = listSpecs();
console.log('Total specs:', allAfterReg.length);
for (const s of allAfterReg) {
  console.log(`  spec_id: ${s.spec_id} | type: ${s.spec_type} | status: ${s.status} | version: ${s.version}`);
}

// Step 3: Propose
console.log('\n=== STEP 3: PROPOSE ===');
const propResult = updateSpecStatus('policy.bugfix.routing-suite', '1.0.0', 'proposed');
console.log('Propose result:', JSON.stringify(propResult, null, 2));

// Step 4: Check store after propose
console.log('\n=== STEP 4: LIST ALL SPECS AFTER PROPOSE ===');
const allAfterProp = listSpecs();
console.log('Total specs:', allAfterProp.length);
for (const s of allAfterProp) {
  console.log(`  spec_id: ${s.spec_id} | type: ${s.spec_type} | status: ${s.status} | version: ${s.version}`);
}

// Step 5: Approve
console.log('\n=== STEP 5: APPROVE ===');
const appResult = approveSpec('policy.bugfix.routing-suite', '1.0.0', {
  approved_by: 'validation',
  requirement_refs: ['AGENTS.md Known Issues'],
  code_refs: ['opencode.json'],
  evidence_refs: ['policy-enforcer-output'],
  owner_technical: 'orchestrator',
  owner_domain: 'runtime-routing',
  approval_run_id: 'run:policy-diagnostic-001',
});
console.log('Approve result:', JSON.stringify(appResult, null, 2));

// Step 6: Check store after approve
console.log('\n=== STEP 6: LIST ALL SPECS AFTER APPROVE ===');
const allAfterApp = listSpecs();
console.log('Total specs:', allAfterApp.length);
for (const s of allAfterApp) {
  console.log(`  spec_id: ${s.spec_id} | type: ${s.spec_type} | status: ${s.status} | version: ${s.version} | has_approval: ${!!s.approval}`);
}

// Step 7: getSpec lookup
console.log('\n=== STEP 7: getSpec LOOKUP ===');
const specById = getSpec('policy.bugfix.routing-suite');
console.log('getSpec("policy.bugfix.routing-suite"):', specById ? `${specById.spec_id}@${specById.version} status=${specById.status}` : 'undefined');

const specByIdVersion = getSpec('policy.bugfix.routing-suite', '1.0.0');
console.log('getSpec("policy.bugfix.routing-suite", "1.0.0"):', specByIdVersion ? `${specByIdVersion.spec_id}@${specByIdVersion.version} status=${specByIdVersion.status}` : 'undefined');

// Step 8: Check store internals
console.log('\n=== STEP 8: STORE INTERNALS ===');
const allSpecs = listSpecs({});
console.log('listSpecs({}) count:', allSpecs.length);
for (const s of allSpecs) {
  console.log(`  ${s.spec_id}@${s.version} → ${s.status} (type: ${s.spec_type})`);
}

// Step 9: Filter by type
console.log('\n=== STEP 9: FILTER BY TYPE ===');
const policySpecs = listSpecs({ spec_type: 'policy' });
console.log('listSpecs({ spec_type: "policy" }) count:', policySpecs.length);
for (const s of policySpecs) {
  console.log(`  ${s.spec_id}@${s.version} → ${s.status}`);
}

console.log('\n=== DIAGNOSTIC COMPLETE ===');
