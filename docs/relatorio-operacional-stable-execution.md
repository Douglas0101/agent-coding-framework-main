# Relatório Operacional — Stable Execution / Autocode Routing

**Run ID:** `run-stable-execution`
**Data:** 2026-04-03
**Escopo:** correção da causa-raiz do desvio de roteamento de `/autocode`

---

## 1. Diagnóstico consolidado

| Campo | Valor |
|-------|-------|
| **Sintoma observado** | O repositório não conseguia validar nem executar `opencode` de forma coerente para `/autocode`, e a narrativa histórica atribuía o problema a bug upstream. |
| **Causa-raiz confirmada** | `opencode.json` e `.opencode/opencode.json` usavam um schema inválido/obsoleto para OpenCode v1.3.13. As chaves antigas (`routing`, `maxSteps` top-level, `instructions` como string e comandos sem `template`) não correspondiam ao schema real aceito pelo runtime. |
| **Conclusão principal** | Neste snapshot, o problema governante era de configuração do repositório, não um defeito inevitável do runtime. |
| **Evidência decisiva** | `opencode debug config --print-logs` falhava com `ConfigInvalidError` antes da migração e passou a aceitar o projeto após a migração para top-level `default_agent`, `agent` e `command`. |

---

## 2. Correção aplicada

### 2.1 Migração de schema

Os arquivos abaixo foram migrados para o schema suportado pelo OpenCode 1.3.13:

- `opencode.json`
- `.opencode/opencode.json`
- `.opencode.example/opencode.json.example`

### 2.2 Ajustes estruturais

- comandos agora usam `command.<name>.template` + `command.<name>.agent`
- agentes agora usam `agent.<name>.maxSteps`
- `instructions` passou a ser array, não string
- o wrapper `.internal/scripts/run-autocode.sh` deixou de forçar `--agent autocoder`
- o wrapper passou a validar:
  - presença dos arquivos de config
  - presença dos campos críticos
  - paridade dos campos críticos
  - aceitação do schema pelo runtime real via `opencode debug config`

### 2.3 Mudança de interpretação operacional

A antiga hipótese de “bug upstream inevitável” foi substituída por um diagnóstico mais preciso:

- **antes:** problema atribuído ao runtime do OpenCode
- **agora:** causa-raiz principal = schema inválido/stale no repositório

---

## 3. Campos críticos de roteamento

Os campos tratados como críticos para paridade e roteamento são:

- `default_agent`
- `command.autocode.agent`
- `agent.autocoder.maxSteps`
- `agent.general.maxSteps`

Esses campos são validados no wrapper, nos testes e no workflow de CI.

---

## 4. Validações executadas

### 4.1 Validação de schema pelo runtime

Comando executado:

```bash
opencode debug config --print-logs
```

Resultado:

- **aprovado** no repositório após a migração
- o runtime passou a resolver `default_agent`, `agent.*` e `command.*` corretamente

### 4.2 Testes automatizados do repositório

Comando executado:

```bash
python -m pytest .internal/tests/ -vv
```

Resultado:

- **30 passed, 1 skipped**

Detalhe da suíte `test_stable_execution.py`:

- **15 passed, 1 skipped**
- inclui validação real de `opencode debug config`
- o smoke test completo de runtime ficou como opt-in via `RUN_OPENCODE_RUNTIME_SMOKE=1`

### 4.3 Smoke test nativo de roteamento

Comando executado manualmente:

```bash
timeout 20s opencode run --command autocode --format json --print-logs "ping"
```

Evidência sanitizada registrada em:

- `.internal/artifacts/codex-swarm/run-stable-execution/native-routing-smoke.log`

Sinais confirmados no log:

- `command=autocode`
- `agent=autocoder`

Conclusão do smoke test:

- o roteamento nativo de `/autocode` para `autocoder` funciona sem `--agent`

---

## 5. Resultado operacional

| Aspecto | Status |
|---------|--------|
| Schema de config aceito pelo runtime | ✅ |
| Paridade root ↔ `.opencode` nos campos críticos | ✅ |
| Wrapper com fail-fast e validação real | ✅ |
| Roteamento nativo `/autocode` → `autocoder` | ✅ |
| Narrativa documental alinhada com a causa-raiz real | ✅ |

---

## 6. Riscos remanescentes

| Risco | Severidade | Mitigação |
|-------|------------|-----------|
| Reintrodução do schema antigo em configs/templates | Medium | testes + CI + `opencode debug config` no wrapper |
| Divergência futura entre root e `.opencode` | Low | checagem explícita de campos críticos |
| Smoke test completo depender de ambiente com provider configurado | Low | teste opt-in + artefato manual sanitizado |

---

## 7. Arquivos-chave afetados

- `opencode.json`
- `.opencode/opencode.json`
- `.opencode.example/opencode.json.example`
- `.internal/scripts/run-autocode.sh`
- `.internal/tests/test_stable_execution.py`
- `.github/workflows/routing-regression.yml`
- `AGENTS.md`
- `README.md`
- `.internal/artifacts/codex-swarm/run-stable-execution/native-routing-smoke.log`

---

## 8. Veredito final

O problema foi corrigido no contexto deste repositório por meio da migração para o schema suportado pelo OpenCode 1.3.13 e da validação com o runtime real.

**Veredito:** `fixed_in_repository`

O que permanece importante não é um workaround de agente forçado, e sim prevenir regressão para schema inválido no futuro.
