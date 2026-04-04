# Análise Cruzada: Spec-Driven Architecture e Economia de Tokens em Sistemas Multi-Agente

**Data:** 03 de Abril de 2026  
**Fonte:** Diagnóstico do repositório OpenCode cruzado com pesquisas avançadas em SDD (Spec-Driven Development) e governança de tokens em arquiteturas multi-agente

---

## Resumo Executivo

Este documento apresenta uma análise cruzada entre a arquitetura documentada do repositório OpenCode (snapshot público) e os conceitos avançados de Spec-Driven Development (SDD) alinhados ao controle de custos de tokens em sistemas multi-agente. 

**Constatação principal:** O repositório já implementa uma **espinha dorsal constitucional madura** com protocolos robustos de handoff e invariantes de execução, mas ainda opera em nível de **configuração de routing** ao invés de **governança contratual completa**, especialmente no que tange ao orçamento cognitivo (token economics) e formalização semântica dos modos operacionais.

---

## 1. Convergência Arquitetural: Do Diagnóstico à Formalização

O repositório demonstra implementação dos **pilares fundamentais** da Spec-Driven Architecture:

- **Constituição como fonte de verdade:** Domínio-agnóstico, evidência imutável, backward compatibility
- **Separação Core/Domain Packs:** Camada gramatical (Core) vs. extensões contratuais (Domain Packs)
- **Fluxo com papéis separados:** `Explorer` → `Evidence` → `Reviewer` → `Gap` → `Verifier` → `Synthesizer`
- **Protocolos explícitos:** `Verifier`, `Synthesizer`, `Handoff` e `Evidence` formalizados

No entanto, cruzando com frameworks recentes de *Agent Contracts*, identifica-se que os **modos operacionais** (`autocoder`, `general`, `explore`, `reviewer`, `orchestrator`) ainda funcionam como *rótulos de routing* (`mode: "primary"` universal) ao invés de **contratos de execução completos** com orçamento, memória e escopo formalizados.

### Modelo Teórico vs. Implementação Atual

Sistemas multi-agente produtivos exigem formalização de contratos:

```
C = (I, O, S, R, T, Φ, Ψ)
```

Onde:
- **I/O:** Inputs/Outputs especificações (parcialmente implementado via `ExecutionContext`)
- **S:** Ferramentas e restrições de segurança
- **R:** Restrições de recursos multidimensionais (**ausente**)
- **T:** Limites temporais (**parcial** - apenas `maxSteps`)
- **Φ:** Critérios de sucesso (**implícito**)
- **Ψ:** Critérios de satisficing (**não implementado**)

---

## 2. O Gap Crítico: Budget Semântico vs. Controle de Steps

### Diagnóstico Atual
O sistema utiliza `maxSteps` como mecanismo principal de controle:
- `agent.autocoder.maxSteps`
- `agent.general.maxSteps`

Isso garante **estabilidade de roteamento** mas não constitui um **modelo de orçamento cognitivo**.

### Comparação: Abordagens de Controle de Recursos

| Dimensão | Abordagem `maxSteps` (Atual) | Abordagem Agent Contracts (Alvo) |
|----------|------------------------------|----------------------------------|
| **Redução de tokens** | Limitada (contagem de passos) | **Até 90% de redução** com 525× menor variância |
| **Governança** | Routing stability | Resource bounded execution |
| **Previsibilidade de custo** | Baixa | Alta (budgets硬编码) |
| **Violações de conservação** | Não detectadas | Zero violações em delegação hierárquica |

### Orçamento Multidimensional Necessário

A transição requer especificação de budgets por modo:

| Recurso | Descrição | Impacto no Custo |
|---------|-----------|------------------|
| **Tokens de LLM** ($r_{tok}$) | Limite absoluto de entrada/saída por modo | Redução de 35-40% |
| **Chamadas de API** ($r_{api}$) | Controle de ferramentas externas | Previsibilidade de custo |
| **Iterações** ($r_{iter}$) | Máximo de refinamentos permitidos | Limita loops de raciocínio |
| **Busca/Recuperação** ($r_{retrieval}$) | Chunks máximos de contexto | Evita context flooding |
| **Handoffs** ($r_{handoff}$) | Máximo de transições entre agentes | Reduz complexidade de orchestration |

---

## 3. Modos como Contratos Semânticos Completos

### Estado Atual
```yaml
agent:
  autocoder:
    mode: "primary"
    maxSteps: 10
  general:
    mode: "primary" 
    maxSteps: 15
```

**Problema:** Ausência de diferenciação semântica e estratégica entre modos.

### Modelo Alvo: Satisficing Strategies

Cada modo deve declarar explicitamente seu trade-off qualidade/custo:

| Modo | Característica | Trade-off | Caso de Uso |
|------|---------------|-----------|-------------|
| **URGENT** | Sem raciocínio estendido, timeout 30s | 70% sucesso, custo mínimo | Hotfixes, emergências |
| **ECONOMICAL** | Baixo esforço racional, 60s | 76% sucesso, custo moderado | Tarefas rotineiras |
| **BALANCED** | Esforço médio, 90s | 86% sucesso, investimento 75% maior | Features padrão |
| **DEEP** | Raciocínio exaustivo, 300s | 95%+ sucesso, custo elevado | Refactoring crítico |

### Estrutura de Contrato de Modo

```yaml
agent_mode_contract:
  metadata:
    name: "explore"
    version: "2.1.0"
    parent_contract: "core/agent-v1"

  mission:
    description: "Exploração de código e análise estática"
    success_criteria: ["evidence_collected", "scope_defined"]
    failure_modes: ["timeout", "max_tokens_exceeded"]

  scope:
    input_schema: "schemas/explore-input.json"
    output_schema: "schemas/evidence-bundle.json"
    tools_allowlist: ["read_file", "list_dir", "grep_search"]
    tools_denylist: ["write_file", "execute_command"]
    write_scope: "read-only"  # invariante constitucional

  resources:
    budget:
      max_input_tokens: 4000
      max_output_tokens: 2000
      max_context_tokens: 8000
      max_retrieval_chunks: 10
      max_iterations: 3
      max_handoffs: 2

    compression_policy:
      evidence_trail: "summary"  # full | summary | none
      context_window: "sliding"  # sliding | truncate | accumulate
      handoff_payload: "compressed"  # compressed | full

  temporal:
    timeout_seconds: 90
    timeout_strategy: "return_partial"  # return_partial | fail_hard

  satisficing:
    strategy: "ECONOMICAL"
    quality_threshold: 0.75
    early_exit_criteria:
      - "confidence > 0.9"
      - "evidence_count >= 5"

  handoff:
    allowed_targets: ["reviewer", "verifier"]
    evidence_retention: "full"
    context_budget_tokens: 2000
    required_gates: ["evidence_bundle_complete"]

  error_policy:
    retry_strategy: "exponential_backoff"
    max_retries: 2
    fallback_agent: "general"
    escalation_trigger: "budget_exceeded"
```

---

## 4. Protocolos de Handoff: Estabilidade vs. Eficiência

### Fortalezas Atuais (Confirmadas)
O repositório demonstra excelência em handoff estrutural:
- **12 campos obrigatórios** no contrato de `Handoff`
- **Regras de validação:** `write_scope_disjoint`, `verifier_gate_passed`
- **Invariantes:** `verifier` obrigatório antes de `synthesizer`, fluxo artifact-first
- **Prevenção:** Proibição de fallback silencioso

### Tensão Não Resolvida: Custo vs. Robustez

**Problema:** Handoffs ricos em contexto aumentam robustez mas consomem ~150k tokens em operações multi-ferramenta.

**Solução Arquitetural:** Implementar **Lazy Loading de Contexto** e **Compressão Seletiva**:

1. **Carregamento Sob Demanda:** Tool definitions carregadas apenas quando necessárias (redução de 98% no startup)
2. **Filtragem de Respostas:** Truncation/sumarização de outputs antes de retornar ao modelo
3. **Context Deduplication:** Eliminação de redundâncias em `evidence_trail` e `handoff_context`
4. **Prompt Caching:** Reuso de prefixes comuns (system instructions) entre chamadas sequenciais

### Fluxo de Handoff Otimizado

```
Agent A (completo)
    ↓ [handoff signal]
Context Compression (evidence_trail → summary)
    ↓
Budget Check (context_budget_tokens disponível?)
    ↓
Agent B (recebe apenas contexto essencial + referências)
```

---

## 5. Leis de Conservação em Hierarquias Multi-Agente

### Princípio Fundamental
Em delegação hierárquica, recursos alocados a subtarefas não podem exceder recursos do contrato pai:

```
Conservação de Tokens:    Σ(children r_tok) ≤ r_tok_parent
Conservação de Handoffs:  Σ(children h_count) ≤ h_max_parent
Conservação de Tempo:     Σ(children t_exec) ≤ T_parent
```

### Implementação Requerida

1. **Delegação Hierárquica de Contratos:**
   - Cada handoff gera um sub-contrato com orçamento derivado
   - Runtime enforcement: interrupção imediata ao exceder $c_i(t) \leq b_i$

2. **Verificação de Conservação:**
   - Validação em tempo de execução (zero tolerance)
   - Rollback automático em caso de violação
   - Auditoria de "budget drift"

3. **Estratégias de Mitigação:**
   - **Conservative Allocation:** Reserva de 10-15% de buffer no pai
   - **Dynamic Rebalancing:** Redistribuição de budget não utilizado entre siblings
   - **Early Termination:** Abortamento graceful ao atingir 95% do budget

---

## 6. Mapa de Gaps e Recomendações

| Pilar | Estado Atual | Evidência | Risco | Recomendação Prioritária |
|-------|--------------|-----------|-------|-------------------------|
| **Governança de Recursos** | `maxSteps` apenas | Testes de paridade de roteamento | Custo explosivo em produção ("$47K problem") | Implementar Agent Contracts com dimensões $R$ (tokens, API calls, tempo) |
| **Modos Operacionais** | Rótulos de routing (`mode: "primary"`) | Configuração uniforme | Semântica imprecisa, otimização de custo impossível | Taxonomia de modos com políticas de satisficing (URGENT/ECONOMICAL/BALANCED/DEEP) |
| **Handoff Eficiente** | Protocolo rico (12 campos) | Regras de `write_scope_disjoint` | Overhead de contexto (150k tokens por handoff) | Lazy loading + compressão seletiva de evidence_trail |
| **Memória Formal** | `session_state`, `handoff_context` implícitos | Estruturas previstas no Core | Context flooding, memória não auditável | Contrato explícito de memória (operacional vs. estrutural vs. episódica) |
| **Drift Semântico** | Validação de routing apenas | CI/wrapper valida campos críticos | Mudanças silenciosas de comportamento entre versões | Validação de schema de saída, mudança de papel, mudança de budget |
| **Planejamento Explícito** | Implícito no `orchestrator` | Comandos `autocode`, `analyze`, `ship` | Reconstrução de escopo a cada execução (waste de tokens) | Separar `planner` como modo contratual com budget próprio e output estruturado |
| **Conservação de Recursos** | Não implementada | Ausência de validação hierárquica | Violações de budget em cascata | Leis de conservação matemáticas com runtime enforcement |

---

## 7. Roadmap de Evolução: SDD Orientado a Contratos

### Fase 1: Formalização de Contratos (Imediato)
- [ ] Criar `.internal/specs/core/agent-mode-contract.yaml`
- [ ] Definir schemas JSON para inputs/outputs de cada modo
- [ ] Implementar validação de contratos no CI

### Fase 2: Governança de Recursos (Curto Prazo)
- [ ] Substituir `maxSteps` por budgets multidimensionais
- [ ] Implementar rastreamento de token usage por modo
- [ ] Adicionar políticas de compressão configuráveis

### Fase 3: Otimização de Handoffs (Médio Prazo)
- [ ] Lazy loading de tool definitions
- [ ] Compressão automática de evidence_trail
- [ ] Implementação de prompt caching entre chamadas

### Fase 4: Hierarquia e Conservação (Longo Prazo)
- [ ] Delegação hierárquica de budgets
- [ ] Runtime enforcement das Leis de Conservação
- [ ] Sistema de rebalancing dinâmico de recursos

### Fase 5: Autonomia Semântica (Futuro)
- [ ] Seleção automática de modo baseada em criticidade da tarefa
- [ ] Ajuste dinâmico de thresholds de satisficing
- [ ] Aprendizado de budget allocation por domínio

---

## 8. Conclusão

O diagnóstico revela que o repositório OpenCode já possui uma **arquitetura macro madura** alinhada aos princípios de SDD, com separação clara de responsabilidades, protocolos formais de handoff e invariantes constitucionais robustos. 

O **próximo estágio de maturidade** — e o diferenciador competitivo em sistemas multi-agente produtivos — está na transição da **configuração de agentes** para a **governança contratual completa**, especialmente:

1. **Economia de Tokens:** Implementação de budgets multidimensionais (não apenas steps) com redução potencial de 90% nos custos operacionais
2. **Autonomia Semântica:** Formalização de modos como contratos com estratégias de satisficing explícitas
3. **Conservação de Recursos:** Garantias matemáticas de orçamento em hierarquias de delegação
4. **Eficiência de Handoff:** Compressão inteligente de contexto mantendo a robustez validada

Esta evolução posiciona o sistema não apenas como "especificação-para-código", mas como **"especificação-para-orquestração-economica"**, onde a estabilidade de execução é garantida não apesar do controle de custos, mas **por meio dele**.

---

## Referências e Fontes

- Documentação interna do repositório OpenCode (snapshot público)
- Pesquisas recentes em Agent Contracts e Resource Bounded Execution (2024-2025)
- Frameworks de Cognitive Architectures para sistemas multi-agente
- Melhores práticas de Token Economics em LLM Orchestration
- Protocolos de Handoff e State Management em ambientes distribuídos

---

*Documento gerado para análise arquitetural e planejamento de evolução do sistema.*
*Manter sincronizado com a Constituição do Core e manifestos de Domain Packs.*
