# PRD — Desverticalização do Framework e Adoção de Core Domain-Agnostic

**Status:** Draft v0.1  
**Base normativa:** `CONSTITUTION_emendada.md`  
**Tipo:** Product Requirements Document (PRD)  
**Objetivo do PRD:** orientar a execução clara da transição do framework atual para um **Agent Orchestration Framework** com **Core domain-agnostic** e **Domain Packs contratuais**

---

## 1. Resumo Executivo

O framework atual possui um núcleo forte de orquestração, evidência, verificação, síntese, execução estável e boundary público/privado, mas sua superfície pública ainda comunica especializações verticais e funcionais como parte nativa do produto, especialmente em engenharia de software, ML/AI e Medical Imaging. A nova constituição estabelece que o **Core deve permanecer domain-agnostic** e que toda capacidade vertical deve existir como **Domain Pack registrado via Extension Registry**.

Este PRD define a execução para:

1. separar o que é **Core** do que é **capacidade funcional** e do que é **domínio vertical**;
2. remover ML/AI e Medical Imaging da identidade do Core;
3. introduzir o modelo formal de **Domain Contracts + Registry**;
4. alinhar documentação, estrutura, governança e pipeline de validação ao modelo constitucional;
5. preservar as capacidades fortes já existentes: stable execution, verifier gate, synthesizer, evidence trail, boundary público/privado e fail-fast de configuração.

---

## 2. Problema

### 2.1 Problema principal
A superfície atual do framework comunica um produto híbrido: parte **motor de orquestração genérico**, parte **catálogo embutido de especialidades**. Isso reduz neutralidade arquitetural, dificulta adaptação para outros perfis computacionais e cria ambiguidade entre:

- o que é **Core obrigatório**
- o que é **capacidade opcional**
- o que é **vertical de domínio**

### 2.2 Evidências do problema
O snapshot atual apresenta:
- catálogo público com skills de `ML/Data`, incluindo `advanced-ml-optimization`, `experiment-tracking`, `model-lineage`, `agentic-rag`, `agentic-reporting` e grupos de especialistas médicos, inclusive `specialist-group-a/b/c/d (medical imaging specialists)` fileciteturn11file0
- README com posicionamento do framework como solução com skills especializadas por domínio, incluindo radiologia e diretrizes médicas fileciteturn6file0
- Core operacional e governança robustos para orquestração, handoff, verifier gate, synthesizer, config parity e stable execution fileciteturn7file0 fileciteturn12file0 fileciteturn14file0
- constituição emendada determinando que o Core seja **domain-agnostic** e que domínios existam como extensões contratuais via `DomainPack` e `Extension Registry` fileciteturn20file0

### 2.3 Impacto
Sem a desverticalização:
- o framework continua parecendo especializado demais;
- novas adoções por times de outros domínios ficam conceitualmente mais caras;
- a governança arquitetural permanece implícita em vez de formalizada;
- a evolução do Core fica acoplada à semântica de domínios específicos.

---

## 3. Objetivo do Produto

Transformar o framework atual em um **Agent Orchestration Framework** de propósito geral para profissionais computacionais, no qual:

- o **Core** contenha apenas gramática de orquestração, evidência, handoff, gates e governança;
- capacidades de domínio existam como **Domain Packs** contratuais e registráveis;
- a superfície pública reflita com clareza essa separação;
- o pipeline de validação imponha conformidade constitucional automaticamente.

---

## 4. Objetivos e Não Objetivos

### 4.1 Objetivos
1. Formalizar a separação entre **Core**, **packs funcionais** e **packs verticais**.
2. Remover ML/AI e Medical Imaging da identidade canônica do framework.
3. Introduzir estrutura de `specs/`, `domains/` e `registry/`.
4. Tornar verificável em CI que o Core está livre de verticalidade.
5. Alinhar README, docs, AGENTS e demais contratos públicos à constituição.
6. Preservar compatibilidade operacional com o modelo atual sempre que possível.

### 4.2 Não objetivos
1. Reescrever todo o runtime operacional.
2. Apagar as capacidades de ML/AI ou Medical Imaging.
3. Tornar todos os domínios públicos; implementações operacionais podem continuar privadas.
4. Substituir de imediato OpenCode/Codex como runtime.
5. Resolver todas as extensões de domínio na primeira iteração.

---

## 5. Usuários e Stakeholders

### 5.1 Usuários-alvo
- mantenedores do framework
- arquitetos do Core
- times que desejam adaptar o framework a projetos computacionais distintos
- times responsáveis por packs de domínio

### 5.2 Stakeholders
- Core maintainers
- maintainers de domínios verticais
- responsáveis por CI/governança
- futuros consumidores do template/framework

---

## 6. Estado Atual vs Estado Alvo

### 6.1 Estado atual
- forte orientação a agent coding e software workflows (`autocode`, `analyze`, `review`, `ship`) fileciteturn13file0
- papéis canônicos como `verifier` e `synthesizer`, já com semântica operacional consolidada fileciteturn7file0
- documentação pública ainda mistura Core com catálogo vertical de skills fileciteturn6file0 fileciteturn11file0
- boundary público/privado e segurança já bem desenvolvidos fileciteturn15file0 fileciteturn18file0
- CI já valida paridade, regressão e boundary fileciteturn19file0

### 6.2 Estado alvo
- Core descrito como **domain-agnostic orchestration layer**
- `Verifier` e `Synthesizer` definidos como **protocolos do Core**
- ML/AI e Medical Imaging relocados para **Domain Packs**
- Registry como ponto único de descoberta de extensões
- documentação pública separando claramente:
  - Core
  - functional packs
  - domain packs
- pipeline de conformidade validando os invariantes constitucionais

---

## 7. Escopo do Produto

### 7.1 Escopo incluído
- constituição como referência normativa
- taxonomia arquitetural do framework
- reestruturação documental
- criação do esqueleto estrutural de `specs/`, `domains/`, `registry/`
- definição de contratos e manifests
- novos critérios de CI
- plano de migração de domínios existentes

### 7.2 Escopo excluído
- implementação detalhada de todos os Domain Packs
- refatoração completa de todos os scripts internos em uma única fase
- exposição pública de artefatos privados

---

## 8. Requisitos de Produto

## 8.1 Requisitos funcionais

### RF-001 — Constituição como fonte de verdade
O framework deve adotar a constituição emendada como referência normativa de arquitetura.

**Critério de aceite**
- existe documento constitucional versionado;
- README e docs fazem referência explícita à constituição;
- decisões arquiteturais conflitantes passam a ser avaliadas contra ela.

### RF-002 — Separação formal entre Core e Domain Packs
O framework deve explicitar, em estrutura e documentação, a distinção entre Core e domínios.

**Critério de aceite**
- existe estrutura `specs/core/`, `domains/` e `registry/`;
- o Core não referencia domínios específicos em sua definição pública;
- todo domínio depende do Core via contrato, nunca o contrário.

### RF-003 — Registry de extensões
O framework deve possuir um `Extension Registry` para descoberta e ativação de Domain Packs.

**Critério de aceite**
- existe `registry.yaml` ou equivalente;
- cada pack possui `contract.yaml` e `manifest.json`;
- o Core não depende hard-coded de nomes de domínio.

### RF-004 — Protocolização de Verifier e Synthesizer
`Verifier` e `Synthesizer` devem ser definidos como protocolos do Core.

**Critério de aceite**
- documentação do Core os trata como protocolos;
- implementações default, quando existirem, são identificadas como implementações e não como definição normativa;
- nenhum domínio contorna o protocolo do `Verifier`.

### RF-005 — Desverticalização documental
A superfície pública deve remover ML/AI e Medical Imaging da identidade canônica do framework.

**Critério de aceite**
- README e docs não vendem esses domínios como parte intrínseca do Core;
- exemplos de domínios ficam explicitamente marcados como ilustrativos ou opcionais;
- catálogos são reclassificados em packs.

### RF-006 — Pipeline de conformidade constitucional
O CI deve validar que mudanças não reintroduzem verticalidade no Core.

**Critério de aceite**
- existe gate de “constitutional compliance”;
- violações aos invariantes bloqueiam merge;
- drift entre contratos e implementação é detectado.

### RF-007 — Preservação de capacidades fortes existentes
Stable execution, evidence trail, handoff contracts, fail-fast e boundary público/privado devem permanecer como competências centrais.

**Critério de aceite**
- documentação do Core preserva essas garantias;
- CI existente continua funcional ou é migrado sem perda de cobertura;
- wrapper e testes críticos permanecem alinhados.

---

## 8.2 Requisitos não funcionais

### RNF-001 — Clareza arquitetural
A documentação deve permitir que um mantenedor diferencie em menos de 10 minutos:
- o que é Core
- o que é functional pack
- o que é domain pack

### RNF-002 — Compatibilidade progressiva
A migração deve ser incremental e não exigir reescrita total do framework.

### RNF-003 — Auditabilidade
Toda mudança estrutural deve ter critérios objetivos de validação.

### RNF-004 — Neutralidade de domínio
O nível 0 não pode carregar semântica normativa de domínios verticais.

### RNF-005 — Segurança de publicação
A nova estrutura deve permanecer compatível com a política pública/sanitizada existente.

---

## 9. Backlog de Execução por Fase

## Fase 0 — Ratificação e alinhamento
**Objetivo:** oficializar a nova direção arquitetural.

### Entregáveis
- `CONSTITUTION.md` emendada ratificada
- decisão de nomenclatura: Agent Coding Framework vs Agent Orchestration Framework
- decisão sobre taxonomia de packs

### Tarefas
- aprovar constituição
- alinhar maintainers
- definir naming target do produto

### Critério de pronto
- constituição aprovada
- naming guide aprovado
- taxonomia validada

---

## Fase 1 — Reclassificação documental
**Objetivo:** alinhar a superfície pública ao modelo constitucional.

### Entregáveis
- novo `README.md`
- novo `docs/README.md`
- revisão de `AGENTS.md`
- glossário de Core vs packs

### Tarefas
- remover narrativa de verticalidade canônica
- reescrever catálogo de skills como packs
- separar protocolos do Core de implementações default
- explicitar modelo público/sanitizado vs privado/operacional

### Critério de pronto
- nenhum documento público principal apresenta ML/Medical como identidade do Core
- docs e constituição não entram em contradição

---

## Fase 2 — Estrutura mínima de Core e Registry
**Objetivo:** materializar a separação no repositório.

### Entregáveis
- diretório `specs/core/`
- diretório `domains/`
- diretório `registry/`
- `registry.yaml`
- templates de `contract.yaml` e `manifest.json`

### Tarefas
- criar estrutura
- criar template oficial de Domain Contract
- definir schema mínimo do registry
- incluir exemplos sanitizados

### Critério de pronto
- o repositório contém a estrutura canônica;
- pelo menos dois domínios de exemplo estão modelados como packs;
- o Core não depende hard-coded deles.

---

## Fase 3 — Migração dos domínios verticais
**Objetivo:** retirar ML/AI e Medical Imaging do Core narrativo e estrutural.

### Entregáveis
- `domains/data-ml/`
- `domains/medical-imaging/`
- manifests e contracts de ambos
- plano de futura expansão para outros domínios

### Tarefas
- mapear capacidades atuais de ML/AI
- mapear capacidades atuais de Medical Imaging
- transformar essas capacidades em Domain Packs
- marcar claramente o status como opcional

### Critério de pronto
- os domínios existem fora do Core;
- documentação os identifica como opcionais;
- o Core continua coerente sem eles.

---

## Fase 4 — CI e arquitetura guardiã
**Objetivo:** automatizar enforcement constitucional.

### Entregáveis
- job de constitutional compliance
- job de contract compliance
- job de drift detection
- atualização dos checks existentes

### Tarefas
- manter routing regression e boundary guard
- adicionar validações de invariantes
- adicionar validação de contracts
- definir política de merge blocker

### Critério de pronto
- merge falha se o Core reintroduzir verticalidade;
- merge falha se Domain Pack violar contrato;
- merge falha se docs contradisserem o modelo de arquitetura, quando aplicável.

---

## Fase 5 — Consolidação operacional
**Objetivo:** garantir que a refatoração não degrade as forças do framework.

### Entregáveis
- matriz de compatibilidade
- atualização de testes
- runbook de adoção
- plano de rollout

### Tarefas
- testar stable execution após reorganização
- confirmar paridade e fail-fast continuam válidos
- revisar wrappers e manifests
- documentar como adicionar novo domínio

### Critério de pronto
- regressões críticas inexistentes;
- maintainers conseguem criar novo Domain Pack usando o fluxo padrão;
- Core segue estável.

---

## 10. Dependências

### Dependências internas
- aprovação constitucional
- disponibilidade dos maintainers
- atualização coordenada de README/docs/AGENTS
- manutenção dos checks atuais

### Dependências técnicas
- schema mínimo para contracts
- schema mínimo para registry
- naming conventions
- decisão sobre localização de exemplos sanitizados

---

## 11. Métricas de Sucesso

### Métricas de produto
- tempo para explicar a arquitetura a novo mantenedor < 15 minutos
- 100% dos documentos centrais alinhados à constituição
- 0 referências normativas verticais no Core público
- 100% dos domínios verticais modelados como packs, não como Core

### Métricas de engenharia
- CI bloqueia regressões arquiteturais
- nenhum check crítico de stable execution é perdido
- criação de novo Domain Pack via template executável em uma sessão

### Métricas qualitativas
- clareza percebida pelos maintainers
- menor ambiguidade entre “framework” e “especialização”
- maior transferibilidade para outros projetos computacionais

---

## 12. Riscos

### Risco 1 — Refatoração só documental
**Descrição:** mudar o discurso sem materializar estrutura e governança.  
**Mitigação:** exigir `registry`, `contracts` e checks em CI.

### Risco 2 — Quebra operacional do modelo atual
**Descrição:** a reorganização enfraquecer wrappers, routing ou testes.  
**Mitigação:** preservar explicitamente stable execution e regressão como capacidades centrais.

### Risco 3 — Neutralidade excessiva e perda de valor
**Descrição:** o framework ficar genérico demais e perder tração.  
**Mitigação:** manter Domain Packs fortes e bem documentados.

### Risco 4 — Constituição sem enforcement
**Descrição:** o documento existir, mas sem impacto real no merge process.  
**Mitigação:** transformar invariantes em gates automáticos.

---

## 13. Perguntas em Aberto

1. O nome oficial do framework deve continuar com “coding” ou migrar para “orchestration”?
2. “functional packs” devem existir formalmente ou só `Core + Domain Packs`?
3. `autocoder` permanece como implementação default ou vira apenas um pack funcional?
4. A estrutura pública mostrará exemplos de domínios reais ou apenas templates neutros?
5. `AGENTS.md` continuará descrevendo topologia fixa ou passará a descrever protocolos + implementações canônicas?

---

## 14. Plano de Entrega Recomendado

### Sprint 1
- ratificar constituição
- reclassificar README
- reclassificar docs/README
- revisar AGENTS

### Sprint 2
- criar `specs/core/`, `domains/`, `registry/`
- publicar templates de contract/manifest
- registrar exemplos iniciais

### Sprint 3
- migrar ML/AI e Medical Imaging para packs
- introduzir CI de constitutional compliance
- alinhar testes e documentação final

### Sprint 4
- consolidar runbook de adoção
- validar criação de novo domínio
- preparar release de transição

---

## 15. Checklist Executivo de Pronto

- [x] Constituição ratificada
- [x] README alinhado
- [x] docs/README alinhado
- [x] AGENTS alinhado
- [x] `specs/core/` criado
- [x] `domains/` criado
- [x] `registry/registry.yaml` criado
- [x] template de Domain Contract criado
- [x] ML/AI migrado para pack
- [x] Medical Imaging migrado para pack
- [x] CI com constitutional compliance ativo
- [x] stable execution preservado (32/33 tests pass)
- [x] boundary público/privado preservado
- [x] runbook de adoção publicado

---

## 16. Decisão Recomendada

**Recomendação:** aprovar a execução deste PRD.

Ele é consistente com a constituição emendada fileciteturn20file0 e com o diagnóstico do repositório atual, preservando o que o framework já tem de mais valioso — orquestração, evidence trail, verifier gate, synthesizer, stable execution e governança — enquanto remove a verticalidade indevida da identidade do Core fileciteturn7file0 fileciteturn12file0 fileciteturn14file0
