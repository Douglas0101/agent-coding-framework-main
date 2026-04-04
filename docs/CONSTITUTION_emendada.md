# CONSTITUTION.md — Agent Orchestration Framework

**Status:** Draft v0.2  
**Adoption Date:** [Preencher]  
**Architecture Model:** Spec-Driven Architecture (SDA)  
**Architecture Scope:** Core as Domain-Agnostic Orchestration Layer; Domains as Contractual Extensions  
**Governance Model:** Contract-Based Decoupling  

---

## 1. Princípios Constitucionais

Este framework segue **Spec-Driven Architecture (SDA)**: especificações são artefatos primários que definem, validam e governam comportamento. Código é derivado, validado contra contratos e subordinado à arquitetura declarada.

### 1.1 Invariantes Arquiteturais (Não Negociáveis)

```yaml
constitutional_invariants:
  - id: INV-001
    statement: "O Core permanece domain-agnostic; nenhuma lógica de negócio específica de ML, Medical, Finance, Legal ou outros domínios verticais é permitida no nível 0"
    enforcement: build_failure

  - id: INV-002
    statement: "Toda capacidade domain-specific deve implementar o contrato DomainPack e registrar-se via Extension Registry"
    enforcement: runtime_exception

  - id: INV-003
    statement: "Evidence Trail é imutável, auditável e cross-domain; nenhum pack pode modificar, sanitizar ou sobrescrever evidências produzidas por outro pack"
    enforcement: cryptographic_verification

  - id: INV-004
    statement: "Handoff Contracts do Core são versionados e backward-compatible; quebra de compatibilidade exige major version bump do Core"
    enforcement: ci_validation

  - id: INV-005
    statement: "Gates, Verifier e Synthesizer são protocolos do Core; domínios podem fornecer implementações compatíveis, mas não podem alterar o protocolo"
    enforcement: interface_segregation

  - id: INV-006
    statement: "Dados sensíveis regulados e semânticas específicas de domínio não pertencem ao Core; no nível 0 só são permitidas referências criptográficas, hashes, metadados minimizados ou envelopes de acesso controlado"
    enforcement: static_analysis

  - id: INV-007
    statement: "Contratos públicos podem ser sanitizados e versionados; implementações operacionais podem residir em repositórios privados, desde que permaneçam conformes aos contratos públicos"
    enforcement: release_governance
```

### 1.2 Hierarquia de Verdade

1. **Specification Layer** (`/specs/`) — fonte da verdade autoritária do Core
2. **Contract Layer** (`/domains/*/contract.yaml`) — contratos formais de extensões de domínio
3. **Generated Code** (`/generated/` ou `/src/generated/`) — derivado, regenerável, descartável
4. **Hand-written Code** (`/src/core/`, `/domains/*/src/`) — implementação subordinada aos contratos
5. **Runtime State** — materialização transitória de specs e contratos

**Regra:** em caso de conflito, a specification e os contracts prevalecem sobre o código até que a arquitetura seja formalmente emendada.

---

## 2. Especificação do Core (Nível 0)

O Core define a **gramática de orquestração**, não a semântica de qualquer domínio vertical.

### 2.1 Orchestration Contract

```yaml
# specs/core/orchestration-contract.yaml
spec_version: 1.0.0
kind: CoreContract
domain: core.orchestration

interfaces:
  Agent:
    required_methods:
      - execute(context: ExecutionContext) -> Result
      - capabilities() -> Set[Capability]
    invariants:
      - "Nunca bloqueia indefinidamente; deve respeitar timeout do ExecutionContext"
      - "Nunca assume semântica de domínio sem contrato explícito"

  Handoff:
    required_fields:
      from_agent: AgentRef
      to_agent: AgentRef
      context_hash: SHA256
      timestamp: ISO8601
      intent: String
    validation_rules:
      - "context_hash deve corresponder ao hash do contexto serializado"
      - "timestamp deve ser maior que o último handoff da cadeia"

  Gate:
    type: protocol
    implementations_allowed: true
    protocol_methods:
      - evaluate(evidence: Evidence) -> GateDecision
    constraints:
      - "Execução máxima: 5000ms"
      - "Stateless entre avaliações"

  Verifier:
    type: protocol
    extends: Gate
    purpose: "Avaliar completude, consistência e suficiência das evidências antes da síntese final"

  Synthesizer:
    type: protocol
    purpose: "Produzir saída consolidada e auditável a partir de evidências aprovadas"
    constraints:
      - "Não pode operar sem GateDecision compatível do Verifier"

  Evidence:
    immutable: true
    fields:
      content: Any
      provenance: AgentRef
      timestamp: ISO8601
      integrity_hash: SHA256
      sensitivity_class: String
    invariants:
      - "Evidence do Core não armazena payload regulado específico de domínio em formato bruto"
      - "Evidence do Core deve ser serializável, auditável e verificável"

extension_points:
  DomainPack:
    interface: "core.orchestration.DomainPack"
    registration_method: "registry.register(pack: DomainPack)"
    required_manifest_fields:
      - name
      - version
      - capabilities
      - contract_ref
      - owner
    constraints:
      - "Não pode modificar handoff contracts do Core"
      - "Não pode desabilitar o synthesizer final"
      - "Deve expor manifesto de capacidades"
      - "Deve declarar fronteiras de dados e nível de sensibilidade"
```

### 2.2 Security & Boundaries Contract

```yaml
# specs/core/security-contract.yaml
boundary_rules:
  public_api:
    exposed_to: [all_domains]
    guarantee: "Stable; breaking changes apenas em major versions"

  internal_core:
    exposed_to: [core_implementation_only]
    guarantee: "Instável; não disponível para DomainPacks"

  domain_boundary:
    exposed_to: [specific_domain]
    guarantee: "Isolamento lógico completo; nenhum domínio acessa dados de outro sem contrato explícito e evidência autorizada"

sanitization:
  config_handling: "Fail-fast em secrets não sanitizados; validação em build time"
  regulated_sensitive_data: "Nenhum dado regulado específico de domínio deve ser armazenado em bruto no Evidence do Core; usar hashes, referências criptográficas ou envelopes controlados"
  release_policy: "Contratos públicos e exemplos podem ser sanitizados; detalhes operacionais e segredos permanecem fora da superfície pública"
```

### 2.3 Core Capability Model

O Core pode definir apenas capacidades universais de orquestração, por exemplo:

- execução coordenada
- handoff auditável
- coleta e trilha de evidências
- verificação protocolar
- síntese final
- registro de extensões
- detecção de drift entre contrato e implementação
- validação de conformidade arquitetural

O Core **não** define capacidades verticais como DICOM, model lineage, financial reconciliation, legal review ou equivalentes.

---

## 3. Sistema de Domain Contracts (Níveis 1+)

Domínios são **extensões contratuais do Core**, não acoplamentos implícitos nem plugins arbitrários.

### 3.1 Estrutura de um Domain Pack

```text
domains/
└── {domain-name}/
    ├── contract.yaml
    ├── invariants.md
    ├── manifest.json
    └── src/
        ├── agents/
        ├── gates/
        ├── skills/
        └── adapters/
```

### 3.2 Regras Gerais para Domain Packs

Todo Domain Pack deve:

1. Implementar interfaces e protocolos declarados pelo Core
2. Declarar capacidades de forma explícita no `manifest.json`
3. Declarar fronteiras de dados, sensibilidade e retenção
4. Proibir vazamento de semântica vertical para o nível 0
5. Ser validável de forma isolada e integrável via registry
6. Permanecer substituível ou removível sem quebrar o Core

### 3.3 Exemplos Ilustrativos de Domain Contracts

**Nota normativa:** os exemplos abaixo são ilustrativos. Eles demonstram o mecanismo de extensão, não definem a identidade do framework.

#### Exemplo A — Domain Contract para Data/ML

```yaml
# domains/data-ml/contract.yaml
spec_version: 1.0.0
kind: DomainContract
domain: data.ml
implements: core.orchestration.v1

owner: ml-platform-team

ubiquitous_language:
  - term: Experiment
    definition: "Conjunto de runs versionados com métricas rastreáveis"
  - term: ModelArtifact
    definition: "Binário de modelo com lineage e checksum"

dependencies:
  core: "^1.0.0"
  domains: []

capabilities:
  - name: experiment-tracking
    type: skill
    implements: core.orchestration.Agent
    exposed_via: api

  - name: model-lineage-verifier
    type: gate
    implements: core.orchestration.Verifier
    constraints:
      - "Só pode acessar metadata, nunca dados de treino brutos"

invariants:
  - id: ML-INV-001
    statement: "Datasets brutos não são persistidos no Evidence do Core; apenas referências e hashes"
    validation: static_analysis

  - id: ML-INV-002
    statement: "Model lineage deve ser rastreável até o Experiment raiz"
    validation: runtime_audit
```

#### Exemplo B — Domain Contract para Medical Imaging

```yaml
# domains/medical-imaging/contract.yaml
spec_version: 1.0.0
kind: DomainContract
domain: medical.imaging
implements: core.orchestration.v1

owner: healthcare-specialists-team

ubiquitous_language:
  - term: DICOMStudy
    definition: "Conjunto de imagens médicas vinculadas a identificador anonimizado"
  - term: InferenceResult
    definition: "Output especializado com score e artefatos de inferência"

capabilities:
  - name: dicom-processor
    type: skill
    constraints:
      - "Anonimização obrigatória antes de qualquer evidência interoperável com o Core"

  - name: radiology-synthesizer
    type: specialized_synthesizer
    implements: core.orchestration.Synthesizer
    constraints:
      - "Deve respeitar o protocolo do Core"
      - "Não pode contornar o Verifier"

boundary_rules:
  cross_domain_access: "Proibido sem contrato explícito, autorização e evidência adequada"
  retention: "Conforme política do domínio e exigências regulatórias aplicáveis"
```

---

## 4. Registry e Descoberta de Extensões

### 4.1 Extension Registry

```yaml
# registry/registry.yaml
core_version: 1.0.0

registered_domain_packs:
  - name: data-ml
    version: 1.2.0
    contract_ref: domains/data-ml/contract.yaml
    status: active

  - name: medical-imaging
    version: 0.9.0
    contract_ref: domains/medical-imaging/contract.yaml
    status: experimental
```

### 4.2 Garantias do Registry

- O Registry é o ponto único de descoberta de Domain Packs
- O Core não depende hard-coded de nenhum pack
- Packs podem ser carregados, validados, desativados ou removidos sem redefinir o contrato do Core
- Capacidades verticais só existem no runtime quando o pack correspondente está registrado e validado

---

## 5. Governança e Validação

### 5.1 Camadas de Validação

```yaml
validation_pipeline:
  stages:
    - name: spec_lint
      tool: spectral
      validates: "Sintaxe e consistência de YAML/JSON de specs e contracts"
      gate: pre_commit

    - name: contract_compliance
      tool: custom_validator
      validates:
        - "DomainContract implementa interfaces declaradas"
        - "Não há violação dos invariants do Core"
        - "Dados sensíveis regulados não vazam para o nível 0"
      gate: ci_required

    - name: drift_detection
      tool: contract_diff
      validates:
        - "Código em /domains/*/src/ está em conformidade com contract.yaml"
        - "Não há métodos públicos não especificados"
      gate: ci_required

    - name: integration_contract_test
      tool: pact
      validates: "Interações entre domínios respeitam contratos de comunicação"
      gate: pre_merge

    - name: constitutional_compliance
      tool: architecture_guardian
      validates: "Nenhuma mudança viola INV-001 a INV-007"
      gate: merge_blocker
```

### 5.2 Processo de Adoção de Novo Domínio

1. Identificar necessidade de novo domínio
2. Escrever `contract.yaml` e `invariants.md`
3. Validar aderência constitucional
4. Gerar scaffolding via tooling do framework
5. Implementar código do domínio nas restrições do contrato
6. Passar 100% do pipeline de validação
7. Registrar o domínio no `registry.yaml`

---

## 6. Estratégia de Migração (Estado Atual → SDA)

### 6.1 Fase 1 — Extração de Especificações

Extrair do estado atual:

- o que é Core de orquestração
- o que é capacidade funcional genérica
- o que é domínio vertical
- o que é detalhe operacional privado

Exemplo:

```bash
./tools/extract-specs   --source=src/current   --output=specs/extracted/   --domain-inference=core,functional,vertical
```

### 6.2 Fase 2 — Refatoração do Core

1. Mover toda lógica genérica para `src/core/`
2. Remover referências verticais do nível 0
3. Introduzir `Extension Registry`
4. Garantir que o Core opere sem dependência hard-coded de qualquer domínio

### 6.3 Fase 3 — Isolamento de Domínios

Para cada domínio:

1. Criar `domains/{name}/`
2. Escrever `contract.yaml`
3. Mover implementação para `domains/{name}/src/`
4. Declarar manifesto e fronteiras
5. Registrar no Registry

### 6.4 Fase 4 — Alinhamento da Superfície Pública

1. Publicar apenas contracts, manifests e exemplos sanitizados
2. Manter implementações operacionais, segredos e runtime state fora da superfície pública
3. Garantir que documentação pública descreva o Core como domain-agnostic
4. Tratar catálogos verticais como extensões opcionais, nunca como identidade do framework

### 6.5 Fase 5 — Validação de Conformidade

Executar pipeline completo para provar que:

- o Core está livre de semântica vertical
- Domain Packs permanecem desacoplados
- handoffs obedecem ao contrato
- evidências permanecem auditáveis
- implementações privadas continuam conformes aos contratos públicos

---

## 7. Geração de Código e Tooling

### 7.1 Comandos de CLI

```bash
framework generate-pack   --contract=domains/new-domain/contract.yaml   --output=domains/new-domain/

framework validate-domain   --domain=new-domain   --against=specs/core/orchestration-contract.yaml

framework generate-bindings   --from=domain-a   --to=domain-b   --output=generated/bindings/

framework detect-drift   --spec=domains/new-domain/contract.yaml   --code=domains/new-domain/src/
```

### 7.2 Artefatos Gerados (Não Commitar)

```text
generated/
├── core/
│   ├── types.ts
│   ├── validators.py
│   └── protocols/
│       ├── base_verifier.py
│       └── base_synthesizer.py
└── domains/
    └── {domain}/
        ├── manifest.json
        └── api_client.py
```

**Regra:** `generated/` deve permanecer fora do versionamento; o CI regenera artefatos em build time.

---

## 8. Decisões de Design Arquitetural

### 8.1 Por que não acoplamento vertical no Core?

Porque o Core deve ser reutilizável por qualquer projeto computacional que precise de orquestração, evidência, verificação e síntese — independentemente de operar em software engineering, ML, saúde, finanças, jurídico ou outro domínio.

### 8.2 Por que Evidence é imutável?

Porque imutabilidade facilita:

- audit trail
- replay
- debugging reprodutível
- conformidade regulatória
- paralelismo seguro
- prova de integridade

### 8.3 Por que Domain Packs em vez de semântica embutida?

Porque isso permite:

- neutralidade arquitetural do Core
- evolução independente por domínio
- governança explícita
- remoção segura de verticalidades
- substituição de implementações sem reescrever o framework

---

## 9. Modelo de Superfície Pública e Implementação Privada

### 9.1 Superfície Pública Permitida

Pode ser público e versionado:

- specs do Core
- contracts de domínio sanitizados
- manifests
- templates
- documentação de interface
- exemplos
- validadores e testes de conformidade sanitizados

### 9.2 Superfície Operacional Privada

Deve permanecer fora da superfície pública quando aplicável:

- segredos
- estados de sessão
- dados regulados brutos
- runtime state
- prompts operacionais sensíveis
- implementações internas dependentes de contexto organizacional

### 9.3 Regra de Compatibilidade

Implementações privadas podem evoluir livremente desde que:

1. não violem a Constituição
2. permaneçam conformes aos contracts publicados
3. não introduzam dependência do Core em semântica vertical não declarada

---

## 10. Apêndices

### 10.1 Glossário

- **Specification Layer:** artefatos declarativos que definem contratos
- **Domain Contract:** especificação formal de um domínio vertical
- **DomainPack:** unidade de extensão registrada no framework
- **Extension Registry:** catálogo runtime de packs disponíveis
- **Evidence:** dado imutável e auditável produzido por agents
- **Gate:** protocolo de verificação no fluxo de orquestração
- **Verifier:** protocolo de decisão pré-síntese
- **Synthesizer:** protocolo de consolidação final
- **Handoff:** transferência formal de controle e contexto entre agents

### 10.2 Nota de Interpretação

Nada nesta Constituição torna ML/AI, Medical Imaging, Finance, Legal ou qualquer outro domínio parte intrínseca do framework. Esses domínios existem apenas como exemplos ou extensões opcionais.

---

## 11. Ratificação e Modificações

Modificações neste documento requerem:

1. **Minor Changes** — clarificações, exemplos, redação:
   - PR aprovado por 2 maintainers do Core

2. **Major Changes** — novos invariants, mudanças em extension points, alteração do contract do Core:
   - RFC público por 7 dias
   - aprovação unânime dos maintainers do Core

3. **Constitutional Amendments** — mudanças em INV-001 a INV-007:
   - votação da comunidade
   - auditoria externa de arquitetura
   - plano explícito de migração de compatibilidade

---

*Este documento é a fonte da verdade autoritária para a arquitetura do framework. O código deve permanecer em conformidade; onde houver conflito, esta Constituição prevalece até que seja formalmente emendada.*
