---
name: investigate-execution-conflict
description: Investiga profundamente conflitos de execução no OpenCode, incluindo routing de commands, precedência de configuração, sessões, permissões, fallback de edit/write e causas-raiz do desvio entre agente esperado e agente observado.
---

# Objetivo

Você é uma skill de investigação de engenharia para OpenCode.

Sua missão é investigar profundamente por que um command customizado não está sendo executado pelo agente esperado e por que o runtime observado diverge do comportamento documentado.

Você deve produzir uma análise de causa-raiz, com evidências, hipóteses, testes de confirmação e próximos passos acionáveis.

Seu foco principal é:
- routing de command para agente
- precedência de configuração
- colisões entre camadas de config
- efeitos de sessão/attach/serve
- permissões que impactam validação
- fallback de `edit` para `write`
- riscos operacionais decorrentes

---

# Contexto assumido

Presuma que existe um command `autocode.md` com `agent: autocoder`.

Presuma também que o comportamento observado foi:
- `/autocode` executou com `general` (maxSteps=50), não com `autocoder` (maxSteps=6)
- `/ops-report` (também `agent: autocoder`) executou com `general` (maxSteps=5)
- Outros commands com `agent:` funcionam corretamente (`/ship`→orchestrator, `/review`→reviewer, `/analyze`→explore)
- Bug persiste com `--pure` (sem plugins) → causa é do runtime, não de plugins
- Runtime tenta carregar `.opencode/opencode.json` e `.opencode/opencode.jsonc` que não existem
- Criar `.opencode/opencode.json` vazio (`{}`) causa hang do runtime

**Causa-raiz confirmada (2026-04-03):** Bug de routing seletivo no OpenCode v1.3.13.
Commands com `agent: autocoder` no frontmatter são ignorados pelo runtime, caindo em `general`.
Workaround: usar `--agent autocoder` flag explicitamente.

**Evidência:** `.opencode/skills/self-bootstrap-opencode/debug_autocode.log`
**Issue report:** `.opencode/skills/self-bootstrap-opencode/issue-report/BUG-autocode-routing.md`

Trate isso como um conflito entre:
1. comportamento documentado
2. comportamento observado
3. expectativa de autonomia operacional

---

# Hipóteses iniciais obrigatórias

Você deve investigar, no mínimo, estas hipóteses:

## H1. Sessão stale / command não recarregado
O TUI ou backend pode estar usando uma sessão iniciada antes da criação/alteração do command.

## H2. Colisão entre commands com o mesmo nome
Pode existir outro `autocode` em:
- `.opencode/commands/`
- `~/.config/opencode/commands/`
- `OPENCODE_CONFIG_DIR`
- config JSON/JSONC via `command`

## H3. Override de config por precedência
Pode haver override vindo de:
- config global
- config do projeto
- `OPENCODE_CONFIG`
- `OPENCODE_CONFIG_DIR`
- conteúdo inline

## H4. Bug de routing do OpenCode
O `agent` do command pode não estar sendo respeitado apesar de documentado.

## H5. Erro de interpretação do ambiente
O command pode estar correto, mas a execução real pode estar vindo de:
- outro command
- outra sessão
- outro backend anexado
- outro diretório/projeto

## H6. Gap entre autonomia e guardrails
O agente pode estar correto, mas incapaz de validar a mudança porque as permissões de shell estão apertadas demais para a verificação necessária.

---

# Princípios da investigação

## 1. Não assumir bug cedo demais
Só classifique como bug depois de eliminar:
- duplicidade de command
- sessão stale
- override de config
- projeto errado
- backend errado
- attach incorreto

## 2. Priorizar evidência verificável
Toda conclusão precisa estar apoiada em:
- leitura de arquivo
- listagem/config
- comando de inspeção permitido
- teste controlado reproduzível

## 3. Fazer testes mínimos
Evite alterações amplas.
Prefira tarefas triviais, reversíveis e de baixo risco.

## 4. Não relaxar guardrails sem prova de necessidade
Não transforme `bash` genérico em `allow` como primeira reação.
Avalie primeiro se a inspeção poderia ser feita com tools nativas.

---

# Escopo da investigação

Você deve investigar estes blocos:

## A. Command routing
- o `agent` do command está correto?
- o command carregado em runtime é realmente o arquivo esperado?
- existe duplicata do command?
- o runtime está usando outro agent/current agent por falha de load?

## B. Config precedence
- qual config global existe?
- qual config de projeto existe?
- `OPENCODE_CONFIG` está setado?
- `OPENCODE_CONFIG_DIR` está setado?
- há command definido por JSON que conflita com o Markdown?
- há agent definido por JSON que conflita com o Markdown?

## C. Session/runtime state
- a sessão atual foi aberta antes do command existir?
- há uso de `attach` a backend antigo?
- há `serve` rodando em outro diretório/projeto?
- o teste foi feito no projeto correto?

## D. Tools and permissions
- `read` é suficiente para a validação?
- o uso de `bash` foi realmente necessário?
- quais comandos de inspeção faltam?
- falta de `bash` de verificação impede autonomia ou só reduz conveniência?

## E. Edit vs Write behavior
- o `edit` falhou por mismatch exato de string?
- o fallback para `write` foi local e seguro ou arriscado?
- o prompt do agente precisa instrução mais forte contra sobrescrita total?
- a operação exigia linha/offset/contexto mais preciso?

---

# Procedimento obrigatório

## Fase 1 — Coleta de evidências

Colete e compare:

1. o conteúdo atual de:
   - `.opencode/commands/autocode.md`
   - `opencode.json`
   - `.opencode/agents/autocoder.md`
   - `.opencode/agents/orchestrator.md`

2. os resultados de:
   - `opencode agent list`
   - `opencode --agent autocoder` ou `opencode run --agent autocoder "<tarefa trivial>"`
   - execução de `/autocode` em sessão nova
   - qualquer indício de `attach`/`serve` em uso

3. a presença de possíveis duplicatas:
   - `~/.config/opencode/commands/autocode.md`
   - `command.autocode` em configs JSON/JSONC
   - `OPENCODE_CONFIG_DIR`

## Fase 2 — Testes controlados

Execute testes mínimos e compare comportamento:

### Teste T1 — Controle por CLI explícita
Execute uma tarefa trivial com `--agent autocoder`.

Objetivo:
- provar se o agente `autocoder` funciona corretamente quando selecionado explicitamente.

### Teste T2 — Command em sessão nova
Abra uma sessão totalmente nova e rode `/autocode`.

Objetivo:
- eliminar hipótese de sessão stale.

### Teste T3 — Comparação de agente observado
Compare:
- agente usado com `--agent autocoder`
- agente usado por `/autocode`

Objetivo:
- isolar se o problema é do command routing ou do próprio agente.

### Teste T4 — Duplicidade de command
Verifique se existe outro `autocode` em camadas superiores.

Objetivo:
- eliminar colisão de command.

### Teste T5 — Necessidade real de shell de validação
Verifique se a validação que falhou por `bash` poderia ser feita com `read`.

Objetivo:
- decidir se a solução é:
  - ajuste de prompt
  - ajuste de permissão
  - custom tool read-only
  - ou nenhuma mudança

## Fase 3 — Análise causal

Para cada finding, classifique:
- `confirmed`
- `likely`
- `possible`
- `rejected`

E associe:
- evidência
- impacto
- correção proposta
- risco da correção

---

# Critérios para declarar causa-raiz

Você só pode declarar causa-raiz se houver evidência suficiente para apontar um destes cenários:

## Cenário 1 — Stale session
A sessão não recarregou o command novo e uma sessão nova resolve o problema.

## Cenário 2 — Config collision
Há outro `autocode` ou config de `command`/`agent` sobrescrevendo o comportamento esperado.

## Cenário 3 — Runtime/attach mismatch
O TUI estava anexado a outro backend ou outro diretório/projeto.

## Cenário 4 — Documented behavior mismatch
Mesmo em sessão nova, sem duplicatas, com config correta, o command com `agent: autocoder` continua rodando em `orchestrator`.

Se chegar ao Cenário 4, trate como:
- provável bug
- com reprodução mínima
- pronto para issue report

---

# Política para permissões de validação

Você deve ser conservador.

Se a investigação concluir que o problema principal é só a falta de validação de arquivo alterado, siga esta ordem de solução:

1. usar `read` e line ranges, se suficiente
2. ajustar prompt do agente para preferir tools nativas
3. criar custom tool read-only de verificação
4. só então considerar `bash allow` para um conjunto mínimo e explícito

Não recomende `cat *` amplo como primeira opção.

Se for realmente necessário liberar shell de inspeção, proponha apenas padrões mínimos como:
- `cat <arquivo específico>`
- `tail -n <N> <arquivo específico>`
- `wc -l <arquivo específico>`

E nunca como wildcard amplo sem justificativa.

---

# Política para fallback edit -> write

Se a investigação mostrar que `edit` falha repetidamente e o agente recua para `write`, avalie:

- o arquivo é pequeno ou grande?
- o rewrite total é de baixo risco?
- há instrução suficiente para preferir `edit` com contexto melhorado?
- vale ajustar o prompt do agente para:
  - reler o arquivo
  - usar trecho exato
  - só usar `write` quando a sobrescrita integral for segura

Você deve distinguir:
- comportamento esperado da tool
- risco operacional da estratégia do agente

---

# Saída final obrigatória

Ao terminar, entregue um relatório com exatamente estas seções:

# Conflict Investigation Report

## 1. Problem Statement
- qual era o comportamento esperado
- qual foi o comportamento observado
- por que isso é relevante

## 2. Evidence Collected
- arquivos lidos
- configs inspecionadas
- sessões/commands testados
- permissões observadas

## 3. Hypothesis Matrix
Tabela ou lista estruturada com:
- hipótese
- status
- evidência
- confiança

## 4. Root Cause Assessment
- causa-raiz confirmada ou mais provável
- causas descartadas
- ambiguidade restante

## 5. Runtime Behavior Analysis
- command routing
- session behavior
- config precedence
- edit/write fallback
- validação shell vs tools nativas

## 6. Engineering Risks
- riscos atuais
- severidade
- impacto prático

## 7. Recommended Fixes
- correção imediata
- correção recomendada
- correção opcional
- o que não fazer

## 8. Reproduction Protocol
- passos mínimos para reproduzir
- ambiente
- sessão nova ou não
- comandos exatos

## 9. Final Verdict
- setup correto com uso incorreto
- config em conflito
- sessão stale
- bug provável
- combinação dos fatores

---

# Critérios de aceitação

Considere a investigação concluída apenas se:

1. houver comparação entre comportamento documentado e observado
2. a hipótese de sessão stale tiver sido testada
3. a hipótese de duplicidade/override tiver sido testada
4. houver teste de controle com `--agent autocoder`
5. houver posição explícita sobre necessidade ou não de ampliar `bash`
6. o relatório final diferenciar claramente:
   - fato
   - inferência
   - hipótese
   - recomendação

---

# Política de honestidade

Se a investigação não conseguir confirmar a causa-raiz com alta confiança:
- diga isso explicitamente
- liste as ambiguidades restantes
- proponha o próximo experimento mínimo

Nunca feche a investigação com certeza artificial.
