# **PRD Operacional**

## **Evolução da Arquitetura Multiagente Orientada a Contratos**

## ***Status:** Aprovado para especificação formal* ***Data-base:** 03 de abril de 2026* ***Escopo analisado:** anexo técnico \+ snapshot público acessível do repositório agent-coding-framework-main*

| Decisão arquitetural central: migrar da governança baseada em routing e maxSteps para uma governança baseada em contratos operacionais por modo, preservando a Constituição, o Core domain-agnostic e os protocolos já estáveis. |
| :---- |

| Leitura executiva | Síntese |
| :---: | ----- |
| O que já existe | Foundation spec-driven, contratos centrais, handoff formal e regressão de stable execution. |
| Gap real | Modos ainda não estão formalizados como contratos completos com budget, memória e critérios de satisficing. |
| Decisão do PRD | Criar Agent Mode Contracts como camada operacional primária do runtime. |
| Resultado esperado | Previsibilidade de custo, semântica clara por modo, handoffs econômicos e evolução segura do framework. |

# **1\. Resumo executivo**

O framework já possui uma base sólida de Spec-Driven Architecture: Constituição como fonte de verdade, Core de orquestração domain-agnostic, Domain Packs como extensões contratuais e protocolos formais para Verifier, Synthesizer, Handoff e Evidence. O problema atual não é ausência de espinha dorsal; é a falta de governança contratual completa no nível de modo operacional.

O estado público acessível comprova stable execution com fail-fast de configuração, verifier gate, write scope disjoint, regressão estrutural e regras de handoff; porém a configuração pública ainda diferencia agentes principalmente por binding de comandos e maxSteps. Isso caracteriza controle de fluxo, não contrato operacional completo.

Este PRD formaliza a próxima evolução: Agent Mode Contracts como unidade primária de execução. Cada modo deverá declarar missão, escopo, esquemas de entrada e saída, ferramentas permitidas, política de erro, memória, orçamento multidimensional e critérios de handoff.

# **2\. Contexto e evidência-base**

A Constituição do framework define invariantes não negociáveis, entre eles: Core domain-agnostic, Evidence Trail imutável, Handoff backward-compatible e separação entre superfície pública e implementação operacional privada. O README reforça que somente docs/ é superfície pública, enquanto specs, domains, registry, scripts, testes e artefatos residem em .internal/.

O relatório técnico v4 posiciona corretamente o estado atual como foundation operacional com enforcement parcial: spec-driven foundation implementada, governed execution parcial e lacunas ainda relevantes em observability, memory/knowledge e release intelligence.

O anexo técnico fornecido pelo solicitante acrescenta a camada decisiva para o próximo estágio: governança de tokens, autonomia semântica por modo, leis de conservação de orçamento e compressão econômica de contexto em handoffs.

| Fonte revisada | O que comprova |
| :---: | ----- |
| Constituição | Invariantes arquiteturais, hierarquia de verdade, protocolos centrais e boundary público/privado. |
| README público | Modelo arquitetural, fluxo operacional e política de superfície pública. |
| Relatório técnico v4 | Maturidade real: foundation alta, governed execution média, observability/knowledge baixas. |
| Anexo técnico | Gap entre routing e governança contratual; proposta de budgets, memória formal e handoff economics. |

# **3\. Problema operacional**

Hoje o runtime já evita vários modos de falha estrutural, mas ainda carece de previsibilidade econômica e semântica por modo. Em termos práticos, isso produz quatro limitações centrais:

* maxSteps controla iteração, mas não governa input tokens, output tokens, retrieval, handoffs ou expansão de contexto.  
* Os agentes públicos aparecem como rótulos de routing com descrições curtas, sem missão, escopo e memória formalizados.  
* Planejamento continua implícito no orquestrador, o que favorece reconstrução repetitiva de escopo e consumo desnecessário de contexto.  
* O protocolo de handoff é forte, mas o payload transferido ainda não é gerido por orçamento, compressão seletiva e reidratação sob demanda.

# **4\. Objetivo do produto**

Transformar a atual camada de agentes configurados em uma camada de modos operacionais contratualizados, capazes de executar com previsibilidade de custo, isolamento semântico, observabilidade e enforcement compatível com a Constituição do Core.

| Objetivo | Definição operacional |
| :---: | ----- |
| Previsibilidade | Cada modo expõe budget explícito e auditável de recursos. |
| Semântica | Cada modo define missão, escopo, IO, ferramentas e critérios de sucesso. |
| Eficiência | Handoffs usam compressão seletiva e budget de contexto. |
| Segurança evolutiva | Mudanças são validadas em CI contra drift de schema, budget e papel operacional. |

# **5\. Escopo do PRD**

Incluído neste PRD: especificação de contratos de modo, budget multidimensional, política formal de memória, handoff econômico, planner explícito, métricas e expansão da suíte de conformidade.

Fora de escopo neste ciclo: reescrever a Constituição, publicar runtime privado, substituir o modelo Core \+ Domain Packs ou declarar maturidade completa em observability e release intelligence.

# **6\. Estado atual versus estado-alvo**

| Dimensão | Estado atual | Estado-alvo |
| :---: | ----- | ----- |
| Governança | Routing \+ maxSteps \+ guardrails | Contratos operacionais por modo |
| Memória | ExecutionContext previsto, política implícita | Modelo formal: operacional, sessão e estrutural |
| Handoff | Contrato estrutural forte | Contrato estrutural \+ economics de contexto |
| Planejamento | Implícito no orquestrador | Planner explícito ou subcontrato formal |
| Observabilidade | Baseline parcial | Métricas por modo e budget drift auditável |

# **7\. Requisitos funcionais**

## **RF-01 — Agent Mode Contract**

* Cada modo deve possuir nome, versão, missão, escopo, input schema, output schema e critérios de sucesso.  
* Cada modo deve declarar allowlist e denylist de ferramentas.  
* Cada modo deve declarar política de erro, retry, timeout e destinos permitidos de handoff.

## **RF-02 — Budget multidimensional**

* max\_input\_tokens  
* max\_output\_tokens  
* max\_context\_tokens  
* max\_retrieval\_chunks  
* max\_iterations  
* max\_handoffs  
* timeout\_seconds

## **RF-03 — Política de memória**

* Separar operational\_context, session\_state e structural\_memory.  
* Declarar política de compressão, retenção e payload máximo por handoff.  
* Definir quais elementos podem ser resumidos e quais devem permanecer íntegros.

## **RF-04 — Estratégia de satisficing**

* Cada modo deve declarar perfil de operação: URGENT, ECONOMICAL, BALANCED ou DEEP.  
* Cada perfil deve explicitar o trade-off qualidade/custo e critérios de saída antecipada.

## **RF-05 — Planejamento formal**

O papel de planejamento deve tornar-se um modo explícito ou subcontrato formal do orquestrador, com plano estruturado, pré-condições, pós-condições e output padronizado.

## **RF-06 — Handoff econômico**

O runtime deve suportar summary+refs, compressão seletiva, reidratação sob demanda e limite de tokens por payload transferido.

# **8\. Requisitos não funcionais**

* Compatibilidade constitucional: nenhuma mudança pode violar os invariantes INV-001 a INV-007.  
* Backward compatibility em contratos públicos, especialmente handoff.  
* Fail-fast para excesso de budget, schema inválido ou drift crítico.  
* Auditabilidade total de decisões de budget, compressão, retries e handoffs.  
* Superfície pública sanitizada, sem forçar publicação do runtime privado.

# **9\. Proposta de arquitetura**

A camada operacional passa a girar em torno de um novo artefato: .internal/specs/core/agent-mode-contract.yaml. O binding leve continua em opencode.json, mas a fonte de verdade comportamental passa a ser o contrato de modo.

## **Estrutura mínima do contrato**

| agent\_mode\_contract:   metadata: {name, version, parent\_contract}   mission: {description, success\_criteria}   scope: {input\_schema, output\_schema, tools\_allowlist, tools\_denylist}   resources: {max\_input\_tokens, max\_output\_tokens, max\_context\_tokens, max\_retrieval\_chunks, max\_iterations, max\_handoffs}   memory: {operational\_context, session\_state, structural\_memory, handoff\_payload\_budget}   satisficing: {mode, quality\_threshold, early\_exit}   handoff: {allowed\_targets, compression, verifier\_required}   error\_policy: {retry\_max, timeout\_seconds, on\_budget\_exceeded} |
| :---- |

# **10\. Mudanças por componente**

| Componente | Mudança requerida |
| :---: | ----- |
| Core | Permanece domain-agnostic; recebe apenas a nova gramática de contratos de modo. |
| opencode.json | Continua enxuto como binding de comandos, apontando para contratos ricos. |
| Tests/CI | Passam a validar schema, drift de missão, drift de budget, output schema e conservação de recursos. |
| Handoff runtime | Adiciona compressão summary+refs, context budget e reidratação sob demanda. |

# **11\. KPIs de acompanhamento**

| Eixo | Métrica |
| :---: | ----- |
| Custo | tokens médios por run, custo por modo, custo por handoff, taxa de compressão de contexto |
| Confiabilidade | taxa de verifier pass, taxa de budget exceeded, taxa de partial success |
| Arquitetura | percentual de modos com contrato formal e percentual de comandos mapeados |
| Qualidade | drift detectado antes de merge e cobertura de testes de conformidade |

# **12\. Roadmap recomendado**

| Fase | Entregas |
| ----- | ----- |
| 1\. Fundação contratual | Criar agent-mode-contract, schemas e mapear explore, reviewer e orchestrator. |
| 2\. Resource governance | Adicionar budgets multidimensionais e instrumentar consumo por modo. |
| 3\. Memory model | Separar operacional, sessão e estrutural; limitar payload por handoff. |
| 4\. Planner explícito | Extrair planner ou formalizar subcontrato do orquestrador. |
| 5\. Conservação hierárquica | Aplicar sum(children) \<= parent com enforcement de runtime. |

# **13\. Riscos e mitigação**

| Risco | Mitigação |
| ----- | ----- |
| Sobreengenharia contratual | Iniciar com três modos críticos e expandir gradualmente. |
| Duplicação config vs contrato | Definir opencode.json como binding leve e o contrato de modo como fonte da verdade. |
| Lacuna entre público e privado | Executar em duas trilhas: documentação sanitizada e runtime operacional interno. |

# **14\. Critérios de aceite**

* Existe um schema versionado para Agent Mode Contracts.  
* Pelo menos três modos críticos estão formalizados e validados no CI.  
* O runtime mede consumo por modo e bloqueia excesso de budget configurado.  
* Handoffs operam com summary+refs e budget de contexto.  
* Os testes detectam drift de missão, IO e orçamento antes do merge.

# **15\. Decisão aprovada**

**Aprovar a evolução do framework para Agent Mode Contracts como camada operacional primária, preservando a Constituição e os protocolos do Core, mas substituindo a governança baseada apenas em routing e maxSteps por governança contratual de execução, memória e economia de tokens.**

# **Apêndice A. Base documental revisada**

| ID | Documento | Uso no PRD |
| :---: | ----- | ----- |
| R1 | Constituição emendada | Invariantes e hierarquia de verdade. |
| R2 | READMEs públicos | Modelo, boundary e fluxo. |
| R3 | Relatório técnico v4 | Maturidade real e lacunas. |
| R4 | Config pública \+ suíte stable execution | Config pública e enforcement. |
| A1 | Anexo técnico do solicitante | Gap map para budgets e memória. |

# **Apêndice B. Nota de interpretação**

Este documento descreve o estado atual comprovado do snapshot público acessível e a decisão de arquitetura recomendada para o próximo estágio operacional. Onde a superfície pública não prova a totalidade do runtime interno, o texto diferencia explicitamente entre implementação comprovada, lacuna confirmada e evolução proposta.