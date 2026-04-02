---
description: Audita a conformidade de uma run contra a spec, gerando conformance-report com score de aderência e drift detectado
usage: /verify-conformance <spec_id> <run_id> [--spec-version <version>]
---

Este command verifica se o comportamento observado em uma run está alinhado com a spec vigente.
Gera um `conformance-report` obrigatório para releases em paths críticos.

## Fluxo obrigatório

1. Recupere a spec aprovada via `getSpec(spec_id)` do spec-registry.
2. Recupere os artefatos da run em `artifacts/codex-swarm/<run_id>/`.
3. **Verificar acceptance_criteria**: para cada critério da verification spec, cheque se há evidência correspondente nos artefatos da run.
4. **Verificar transitions**: compare as transições observadas (extraídas do run-manifest ou logs) com as transições permitidas na behavior spec. Sinalizar qualquer `forbidden` transition.
5. **Calcular scores**:
   - `spec_coverage_score`: % de acceptance_criteria com evidência
   - `runtime_to_spec_alignment`: % de transições observadas que eram permitidas
   - `evidence_sufficiency_score`: calculado via `spec-linker.computeScore()`
6. **Detectar drift**: classifique o tipo de drift observado (spec-to-code, code-to-test, spec-to-runtime, intent-to-spec).
7. **Persistir**: salve o `conformance-report` em `artifacts/codex-swarm/<run_id>/conformance-report.json`.
8. **Notificar**: se `runtime_to_spec_alignment < 0.97`, abra incidente automático (log + alerta).

## Output esperado

```json
{
  "schema_version": "1.0.0",
  "artifact_type": "conformance-report",
  "spec_id": "<spec_id>",
  "spec_version": "<version>",
  "run_id": "<run_id>",
  "timestamp": "<ISO8601>",
  "asserts": {
    "passed": ["<critério>"],
    "failed": [{"assert": "<critério>", "reason": "<razão>", "severity": "high"}]
  },
  "spec_coverage_score": 0.95,
  "runtime_to_spec_alignment": 0.98,
  "evidence_sufficiency_score": 0.87,
  "drift_detected": false,
  "drift_types": []
}
```

## Critérios de bloqueio de release

- `runtime_to_spec_alignment < 0.97` → bloquear release e abrir incidente
- `forbidden_transitions` observadas → bloqueio imediato, relatório obrigatório
- `evidence_sufficiency_score < 0.75` → bloquear se risk_level >= high
