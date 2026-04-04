# PRD — Correções obrigatórias na branch `develop` antes da promoção para `main`

## 1. Contexto

A branch `develop` evoluiu o repositório para um modelo de framework com execução estável, contratos sanitizados, governança de boundary público e regressão de routing. O README reposiciona o projeto como **Agent Coding Framework** com OpenCode, Codex, skills, e um subsistema de **Stable Execution** com paridade de configuração, guardrails de execução e CI dedicada. fileciteturn6file0

Ao mesmo tempo, há inconsistências entre a política declarada e o estado efetivo do repositório:

- a política de manifests públicos permite **somente** arquivos sanitizados em `.opencode/manifests/sanitized/` e proíbe dados de sessão, caminhos locais e conteúdo transitório de runtime. fileciteturn12file0
- o `.gitignore` e os testes de boundary reforçam exatamente essa allowlist restrita. fileciteturn10file0 fileciteturn11file0
- porém a branch versiona `.opencode/manifests/latest.json` com `session_id`, caminho absoluto local, timestamps de sessão e metadados de provider/model. fileciteturn13file0

Além disso, o workflow crítico `Routing Regression (Required)` executa apenas em `main`/`master`, embora o Git Flow do projeto defina `develop` como branch de integração da próxima release. fileciteturn9file0 fileciteturn14file0

## 2. Problema

A `develop` não deve ser promovida para `main` enquanto persistirem:

1. **violação da superfície pública sanitizada**, com manifests live versionados;
2. **desalinhamento entre branch policy e CI obrigatória**, deixando `develop` sem o gate crítico de regressão;
3. **drift documental/test coverage**, com contagens divergentes entre README, AGENTS e relatórios operacionais. fileciteturn6file0 fileciteturn7file0

## 3. Objetivo

Corrigir a branch `develop` para que ela fique apta a mergear em `main` sem contradição entre:

- documentação,
- testes,
- `.gitignore`,
- workflows obrigatórios,
- e conteúdo efetivamente versionado.

## 4. Escopo

### Incluído
- saneamento de `.opencode/manifests/`;
- reforço de testes e guardrails de governança pública;
- ampliação de CI/required checks para cobrir `develop`;
- sincronização documental mínima para refletir o estado real da suíte.

### Excluído
- mudanças de arquitetura do runtime OpenCode/Codex;
- redesign do fluxo multiagente;
- expansão de features de produto fora das correções de governança e promoção.

## 5. Requisitos funcionais

### RF-01 — Remover manifests live da superfície pública
O agent coding deve remover do versionamento todos os arquivos em `.opencode/manifests/` que não pertençam ao subconjunto sanitizado permitido.

**Critério obrigatório:** permanecerem versionados somente:
- `.opencode/manifests/README.md`
- `.opencode/manifests/sanitized/*.json`

Base normativa: `.gitignore` e testes de boundary. fileciteturn10file0 fileciteturn11file0

### RF-02 — Eliminar artefatos com dados operacionais live
O agent coding deve apagar da branch os manifests contendo campos proibidos para a superfície pública, incluindo `session_id`, `directory`, timestamps de sessão e metadados de runtime/provider/model. O caso já confirmado é `.opencode/manifests/latest.json`. fileciteturn13file0

### RF-03 — Blindar a governança por teste
Os testes de governança pública devem falhar explicitamente quando qualquer arquivo sob `.opencode/manifests/` fora de `sanitized/` for rastreado pelo Git.

Além disso, criar ou ajustar teste para validar que manifests públicos não contenham campos live/sensíveis como:
- `session_id`
- `directory`
- `provider`
- `model`
- `created_at`
- `updated_at`
- `phases`

### RF-04 — Alinhar CI crítica ao modelo Git Flow
O workflow `.github/workflows/routing-regression.yml` deve executar também para `develop`, não apenas `main`/`master`, pois `develop` é a branch de integração da próxima release. fileciteturn9file0 fileciteturn14file0

### RF-05 — Revisar documentação de required checks
Atualizar `.github/required-status-checks.md` para refletir que os checks mandatórios também precisam cobrir `develop`, ou documentar claramente a diferença caso exista decisão deliberada. Hoje o texto fala só em `main`/`master`. fileciteturn15file0

### RF-06 — Reduzir drift documental sobre cobertura de testes
A documentação deve deixar de afirmar contagens contraditórias da suíte de stable execution. Hoje há divergência entre:
- README: 8 testes em `test_stable_execution.py`; fileciteturn6file0
- AGENTS: 12 testes em 3 suítes. fileciteturn7file0

O agent coding deve escolher uma das opções:
- corrigir as contagens para o estado real; ou
- remover números absolutos e substituir por descrição qualitativa estável.

## 6. Requisitos não funcionais

### RNF-01 — Não quebrar os guardrails existentes
As correções não podem remover:
- paridade de campos críticos entre `opencode.json` e `.opencode/opencode.json`;
- fail-fast do wrapper `run-autocode.sh`;
- gate obrigatório do `verifier`;
- política de deny-by-default para `.opencode/`. fileciteturn8file0 fileciteturn10file0 fileciteturn7file0

### RNF-02 — Mudanças minimamente invasivas
A implementação deve preferir correções de governança e documentação, evitando retrabalho em design ou semântica do runtime.

### RNF-03 — Evidência auditável
A branch corrigida deve deixar prova clara via testes e CI de que a superfície pública está sanitizada.

## 7. Tarefas de implementação

### Workstream A — Higienização de manifests
1. remover de Git:
   - `.opencode/manifests/latest.json`
   - demais arquivos `.opencode/manifests/ses_*.json`
2. manter somente:
   - `README.md`
   - `sanitized/run-manifest.example.json`
3. revisar `.opencode/manifests/README.md` para confirmar a regra operacional. fileciteturn12file0

### Workstream B — Testes
1. ajustar `test_public_boundary.py` para cobrir explicitamente qualquer arquivo sob `.opencode/manifests/` fora de `sanitized/`; fileciteturn11file0
2. adicionar teste novo para schema sanitizado de manifests públicos;
3. garantir que a suíte falhe com campos live proibidos.

### Workstream C — CI e branch protection
1. atualizar `routing-regression.yml` para incluir `develop` em `push` e `pull_request`; fileciteturn9file0
2. revisar se `public-repo-guard.yml` e demais checks críticos também precisam cobrir `develop`;
3. atualizar documentação de checks obrigatórios. fileciteturn15file0

### Workstream D — Documentação
1. corrigir README na seção de cobertura/testes; fileciteturn6file0
2. corrigir AGENTS se necessário; fileciteturn7file0
3. manter consistência com o relatório operacional somente se o relatório continuar sendo tratado como evidência histórica, e não como fonte normativa.

## 8. Critérios de aceitação

A correção será considerada pronta quando:

1. `git ls-files` não listar arquivos `.opencode/manifests/*.json` fora de `sanitized/`, exceto documentação permitida. fileciteturn11file0
2. a suíte `.internal/tests/test_public_boundary.py` passar;
3. a suíte `.internal/tests/test_stable_execution.py` continuar passando;
4. o workflow `Routing Regression (Required)` estiver configurado para `develop`;
5. documentação e testes não estiverem mais em contradição material sobre a política pública;
6. a branch estiver pronta para PR `develop` → `main`.

## 9. Comandos de validação esperados

```bash
git ls-files .opencode/manifests
python -m pytest .internal/tests/test_public_boundary.py -v
python -m pytest .internal/tests/test_stable_execution.py -v
git diff -- .github/workflows/routing-regression.yml README.md AGENTS.md .internal/tests/
```

## 10. Riscos

- remover manifests pode quebrar exemplos implícitos se algum fluxo depender indevidamente de artefato live;
- ampliar CI para `develop` pode revelar falhas já existentes e aumentar o rigor de merge;
- documentação pode continuar driftando se mantiver contagens hardcoded de testes.

## 11. Definition of Done

- superfície pública higienizada;
- testes reforçados;
- CI crítica cobrindo `develop`;
- documentação coerente;
- branch `develop` apta para PR contra `main`.
