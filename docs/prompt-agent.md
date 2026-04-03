# Prompt — Fechamento de Lacunas Antes de Commit e Push

Você está atuando no repositório `agent-coding-framework-main`.

## Objetivo

Fechar todas as lacunas remanescentes **antes de commit e push** do fix de stable execution, garantindo que a mudança esteja pronta para promoção sem drift de configuração, drift documental ou falta de evidência operacional.

## Contexto

Considere como base o trabalho já realizado localmente para `run-stable-execution`, incluindo:

- correção do roteamento incorreto do `/autocode`
- criação de `.opencode/opencode.json`
- criação das specs de `stable-execution`
- suíte local `.internal/tests/test_stable_execution.py`
- conformance report com aceite local

Seu trabalho agora **não é reabrir o diagnóstico**, e sim **fechar as lacunas finais de promoção**.

---

## Escopo obrigatório

### 1. Paridade de configuração

Valide e corrija, se necessário:

- existência de `opencode.json` na raiz
- existência de `.opencode/opencode.json`
- equivalência estrutural e semântica entre ambos
- ausência de drift entre config de runtime e config versionada
- teste automatizado de paridade entre os dois arquivos

Critério de aceite:

- os dois arquivos existem
- não há divergência material entre eles
- existe teste automatizado falhando se houver drift futuro

---

### 2. Sincronização da documentação

Atualize a documentação para refletir o estado real do fix atual.

Verifique e ajuste:

- `README.md`
- `AGENTS.md`
- referências de spec antiga vs spec nova
- referências de DAG antigo vs DAG atual
- contagem e nome das suítes de teste
- workaround atual para `/autocode`
- riscos remanescentes e dependência upstream

Critério de aceite:

- não há contradição entre código, specs, testes e documentação
- a documentação descreve o estado atual de `stable-execution`
- known issues e workaround estão coerentes com a realidade do runtime

---

### 3. Evidência operacional real

Promova o estado de “validado localmente” para “evidenciado para promoção”.

Execute e registre evidências para:

- verificação de conformidade da spec
- compilação da spec em DAG executável
- replay ou golden trace de fluxo crítico
- prova de que `/autocode` não faz fallback silencioso no caminho suportado
- prova de que `verifier` continua sendo gate obrigatório
- prova de que `write_scope` não colide em execução paralela relevante

Critério de aceite:

- artefatos de evidência são gerados e referenciáveis
- existe pelo menos um golden trace ou replay crítico
- o conformance report final está atualizado

---

### 4. Integração no CI

Garanta que o que passou localmente também seja bloqueio de promoção no pipeline.

Verifique e implemente, se faltar:

- execução da suíte `.internal/tests/test_stable_execution.py` no CI
- execução do teste de paridade `root ↔ .opencode`
- execução dos gates mínimos de conformance
- falha explícita do pipeline em caso de drift, fallback silencioso ou regressão de routing

Critério de aceite:

- o CI cobre o fix de stable execution
- não depende apenas de validação local manual
- a promoção é bloqueada automaticamente em caso de regressão

---

### 5. Guardrails para o bug upstream

O bug upstream do runtime ainda deve ser tratado como risco real.

Garanta que:

- `.internal/scripts/run-autocode.sh` continue funcional
- o pre-flight probe detecte agente inesperado
- fallback silencioso seja proibido
- haja logging e evidência em caso de desvio
- o fluxo suportado force `--agent autocoder` quando necessário
- a dependência upstream fique documentada sem ambiguidade

Critério de aceite:

- o workaround continua operacional
- erro de roteamento não passa despercebido
- há fail-fast com evidência, não “best effort” silencioso

---

### 6. Pacote de release pronto para push

Prepare a mudança para promoção com rastreabilidade completa.

Entregue:

- diff limpo e coerente
- lista de arquivos alterados
- resumo técnico por arquivo
- evidências produzidas
- critérios de rollback
- nota de risco residual
- mensagem sugerida de commit
- resumo sugerido para PR

Critério de aceite:

- o pacote é auditável
- reviewer entende o que mudou, por que mudou e como validar
- rollback está definido de forma objetiva

---

## Modo de execução

Siga a ordem abaixo:

1. auditar estado atual do working tree
2. validar paridade de configuração
3. sincronizar documentação
4. gerar evidências operacionais
5. integrar ou ajustar CI
6. reforçar guardrails do workaround
7. consolidar release package
8. só então preparar commit e push

---

## Restrições

- Não faça mudanças ad hoc sem conectá-las às lacunas acima.
- Não considere “passou localmente” como evidência suficiente.
- Não aceite drift entre config, spec, teste e documentação.
- Não aceite fallback silencioso de agente.
- Não faça síntese final sem conformance report atualizado.
- Não proponha commit/push antes de todos os critérios de aceite estarem verdes.

---

## Formato obrigatório da resposta

Responda exatamente com esta estrutura:

# 1. Auditoria do estado atual
- arquivos presentes
- divergências encontradas
- lacunas confirmadas

# 2. Correções aplicadas
- configuração
- documentação
- CI
- guardrails
- evidências

# 3. Evidências geradas
- conformance
- DAG compilado
- golden traces / replay
- testes executados
- resultados

# 4. Validação final pré-push
- checklist de aceite
- itens verdes
- itens bloqueados
- risco residual

# 5. Pacote de promoção
- arquivos alterados
- commit message sugerida
- resumo de PR sugerido
- rollback plan

Se algum item não puder ser fechado, declare explicitamente:
- o que faltou
- o impacto
- o bloqueio para push
- a ação exata necessária para desbloquear