# PRD Final Executivo
## Framework 2.0 — Governança Operacional por Contrato

**Status:** aprovado para execução  
**Data-base:** 4 de abril de 2026  

## 1. Resumo executivo

O framework já possui base sólida: **Core domain-agnostic**, **Agent Mode Contracts**, **Domain Packs**, **Extension Registry**, protocolo formal de **Verifier / Synthesizer / Handoff / Evidence**, budgets por modo e suíte de conformidade. Também já opera com a regra de **4 modos principais** (`explore`, `reviewer`, `orchestrator`, `autocoder`) e skills incrementais por modo, sem proliferar agentes no plano mental do operador.

O gap real não é falta de arquitetura-base. O gap real é que o repositório ainda está em estágio de **foundation operacional + enforcement parcial**, com baixa evidência de **conformance runtime**, **observabilidade madura**, **memory curation operacional** e **release intelligence**.

**Decisão executiva:** a 2.0 deve priorizar **runtime governado**, **planner explícito**, **skills governadas por modo**, **observabilidade/evidência/replay** e **evolução segura por contrato**. O plano de alta performance continua como trilha futura e opcional, ativada apenas por benchmark e SLO comprovados.

## 2. Problema do produto

Hoje o framework já evita várias falhas estruturais, mas ainda sofre com quatro limitações operacionais centrais:

1. o sistema ainda herda parte da governança do paradigma **routing + maxSteps**, o que não basta para controlar custo, memória e semântica por modo;
2. o **planner** continua implícito no orquestrador;
3. o **handoff** é estruturalmente forte, mas ainda precisa de economics de contexto, compressão seletiva e reidratação sob demanda;
4. o runtime ainda não prova, no mesmo nível, uma camada madura de **policy enforcement**, **approval gate**, **artifact ledger**, **trace exporter** e **release intelligence**.

## 3. Objetivo do produto

Transformar o framework em uma **plataforma contratual governada, extensível e observável**, preservando:

- o **Core domain-agnostic**;
- os **4 modos** como superfície operacional principal;
- os **Domain Packs** como extensões contratuais;
- o fluxo **Evidence → Verifier → Synthesizer**;
- a separação entre superfície pública e runtime interno.

## 4. Princípios obrigatórios

1. **Contrato é a fonte da verdade**  
   `opencode.json` continua binding leve; o comportamento nasce do YAML contratual do modo.

2. **4 modos permanecem a superfície principal**  
   Novas capacidades entram como skills contextuais por modo, não como novos agentes top-level.

3. **Core continua magro**  
   O Core define protocolos; packs implementam, mas não redefinem o Core.

4. **Verifier continua gate obrigatório**  
   O synthesizer permanece o único writer final do run package.

5. **Otimização pesada só com prova**  
   eBPF, lock-free, SIMD, JIT, CRDT, Wasm universal e demais opções avançadas não entram como compromisso base deste ciclo.

## 5. Escopo do ciclo 2.0

### Incluído
- runtime governado;
- planner explícito;
- governança de skills por modo;
- observabilidade e evidence store;
- replay mínimo;
- classificação inicial de risco de mudança;
- baseline econômico por modo e por handoff.

### Fora de escopo neste ciclo
- reescrita completa do runtime;
- substituição do modelo Core + Domain Packs;
- declaração de maturidade completa em observability ou release intelligence;
- adoção mandatória de infraestrutura de baixa latência extrema do plano anexo.

## 6. Requisitos funcionais

### RF-01 — Runtime governado
O runtime deve incorporar, como componentes operacionais claros:

- `contract-verifier`
- `policy-enforcer`
- `approval-gate`
- tracking de conformidade por execução

Esses componentes devem operar sobre os contratos de modo já existentes, sem duplicar a semântica em configuração paralela.

### RF-02 — Planner explícito
O papel de planejamento deve tornar-se um subcontrato formal do `orchestrator` ou um módulo explícito que produza:

- plano estruturado;
- pré-condições;
- pós-condições;
- budget allocation;
- política de handoff;
- critério de encerramento.

### RF-03 — Budget multidimensional
Cada modo deve operar com budget verificável de:

- input tokens
- output tokens
- context tokens
- retrieval chunks
- iterations
- handoffs
- timeout

O runtime deve bloquear excesso de budget e registrar a causa da falha.

### RF-04 — Política formal de memória
O runtime deve separar e tratar de forma distinta:

- `operational_context`
- `session_state`
- `structural_memory`

Também deve aplicar regra de compressão seletiva em handoffs, preservando referências de evidência íntegras.

### RF-05 — Handoff econômico
O runtime deve suportar:

- `summary+refs`
- compressão seletiva
- reidratação sob demanda
- limite de tokens por payload
- conservação hierárquica de budget em delegação (`sum(children) <= parent`)

### RF-06 — Skills governadas por modo
Toda skill nova deve possuir:

- modo-alvo;
- contrato de ativação;
- contrato de entrada/saída;
- orçamento esperado;
- política de evidência;
- testes de regressão;
- justificativa de por que não pertence ao Core ou a um Domain Pack.

## 7. Requisitos não funcionais

- compatibilidade com os invariantes constitucionais;
- backward compatibility de contratos públicos, sobretudo handoff;
- fail-fast para drift crítico, schema inválido e budget excedido;
- auditabilidade de decisões de retry, handoff, compressão e budget;
- manutenção da superfície pública sanitizada;
- execução segura com write scopes disjuntos e sem fallback silencioso.

## 8. Arquitetura-alvo deste ciclo

A arquitetura 2.0 permanece:

**Core domain-agnostic → Mode Contracts → Mode Skills → Domain Packs → Runtime governado**

O ganho deste ciclo não é multiplicar camadas novas, mas **dar enforcement e observabilidade reais** ao que já foi desenhado. O estado-alvo passa de “routing + guardrails” para “contratos operacionais por modo com enforcement, budget, memória e handoff economics”.

## 9. Portfolio inicial de execução

### Explore
- `repo_topology_map`
- `change_impact_deep`
- `dependency_surface`

### Reviewer
- `contract_drift_audit`
- `policy_gate_plus`
- `boundary_leak_detector`

### Orchestrator
- `explicit_planner`
- `budget_allocator`
- `handoff_compressor`
- `memory_curator_v2`

### Autocoder
Permanece **execution-puro**, sem inflar a camada analítica do modo.

## 10. Roadmap de implementação

### Fase 0 — Baseline e decisão arquitetural
Entregas:
- benchmark harness mínimo;
- workloads canônicos;
- ADRs de taxonomia, planner, budget, skill contract e evidence policy.

### Fase 1 — Runtime governado P0
Entregas:
- `contract-verifier`
- `policy-enforcer`
- `approval-gate`
- conformance tracking mínimo
- tracing inicial

### Fase 2 — Skills v2 por modo
Entregas:
- 1 skill crítica para `explore`
- 1 skill crítica para `reviewer`
- 1 skill crítica para `orchestrator`
- contratos e testes dessas skills

### Fase 3 — Observabilidade e evidência
Entregas:
- artifact ledger mínimo
- evidence store
- histórico de handoff
- custo por modo
- custo por handoff
- drift auditável

### Fase 4 — Replay e release intelligence inicial
Entregas:
- replay mínimo de runs críticas
- classificação de mudança
- golden traces iniciais
- matriz de impacto por contrato/skill/pack

### Fase 5 — Conservação e otimização
Entregas:
- enforcement hierárquico de budget
- reidratação sob demanda
- compressão mais eficiente
- trilha opcional de otimização avançada, condicionada a benchmark

## 11. KPIs do ciclo

### Custo
- tokens médios por run
- custo por modo
- custo por handoff
- taxa de compressão de contexto

### Confiabilidade
- taxa de `verifier_pass`
- taxa de `budget_exceeded`
- taxa de `partial_success`
- taxa de handoff inválido

### Arquitetura
- percentual de modos com contrato formal exercitado
- percentual de skills com contrato + teste + evidência
- percentual de workflows com planner explícito

### Qualidade
- drift detectado antes do merge
- cobertura de testes de conformidade
- replayabilidade de runs críticas

## 12. Critérios de aceite

Este ciclo será considerado entregue quando:

- os **4 modos** permanecerem a superfície principal sem aumento de complexidade operacional;
- `contract-verifier`, `policy-enforcer` e `approval-gate` estiverem funcionando sobre os contratos atuais;
- houver pelo menos **3 skills v2** governadas por contrato, budget e evidência;
- o runtime medir consumo por modo e bloquear excesso configurado;
- handoffs operarem com `summary+refs` e budget de contexto;
- execuções críticas produzirem rastro auditável mínimo;
- existir baseline de custo, tempo, handoff e drift;
- a release pipeline conseguir classificar mudanças de forma inicial por risco.

## 13. Riscos principais

- sobreengenharia antes de benchmark;
- duplicação entre config leve e contrato rico;
- enforcement fragmentado entre docs, testes e runtime;
- expansão de skills sem lifecycle claro;
- confusão taxonômica entre Core, skill e Domain Pack.

## 14. Instrução operacional para o agent coding

A execução deve seguir esta ordem:

1. fechar ADRs curtos de taxonomia e planner;
2. levantar baseline técnico do estado atual;
3. implementar `contract-verifier`;
4. implementar `policy-enforcer`;
5. implementar `approval-gate`;
6. formalizar `explicit_planner`;
7. subir 3 skills v2 prioritárias;
8. adicionar tracing, artifact ledger e evidence store mínimos;
9. adicionar replay mínimo e classificação inicial de mudança;
10. só então avaliar otimizações pesadas.

## 15. Decisão final

**Aprovar a execução da 2.0 como evolução contratual governada do framework, preservando Core, 4 modos e Domain Packs, e priorizando enforcement runtime, planner explícito, skills por modo, observabilidade e replay antes de qualquer reengenharia de alta complexidade.**
