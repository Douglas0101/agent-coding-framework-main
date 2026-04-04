# Runbook de Adoção — Desverticalização do Framework

**Objetivo:** Guia para mantenedores adotarem o novo modelo Core + Domain Packs.

---

## Checklist de Pronto (PRD)

- [x] Constituição ratificada (`docs/CONSTITUTION_emendada.md`)
- [x] README alinhado
- [x] `specs/core/` criado
- [x] `domains/` criado
- [x] `registry/registry.yaml` criado
- [x] Template de Domain Contract criado
- [x] Domain Packs de exemplo criados (software-engineering, ml-ai, medical-imaging)
- [ ] CI com constitutional compliance ativo (pendente)
- [x] stable execution preservado
- [x] boundary público/privado preservado
- [ ] Runbook de adoção publicado

---

## Fluxo de Adoção para Mantenedores

### 1. Entenda a Arquitetura

```
specs/core/           → Gramática de orquestração (domain-agnostic)
domains/<domain>/     → Semântica de domínio (extensões contratuais)
registry/             → Catálogo de packs disponíveis
templates/            → Templates para novos packs
```

### 2. Para Adicionar Novo Domínio

```bash
# 1. Copie o template
cp -r templates/domain-pack domains/novo-dominio/

# 2. Edite contract.yaml com as definições do domínio
cd domains/novo-dominio/
vim contract.yaml

# 3. Edite manifest.json com metadados
vim manifest.json

# 4. Registre no registry
vim ../registry/registry.yaml

# 5. Valide conformidade
python -m pytest .internal/tests/ -v
```

### 3. Para Atualizar Domain Pack Existente

1. Edite `domains/<pack>/contract.yaml`
2. Atualize `domains/<pack>/manifest.json`
3. Execute testes de validação

### 4. Para Criar Novo Agente/ skill

1. Determine se é capability do Core ou do domínio
2. Se domínio: adicione ao contract.yaml do Domain Pack
3. Se funcional: adicione ao software-engineering pack
4. Registre no registry

---

## Perguntas em Aberto (PRD)

1. **Nome do framework**: "Agent Coding Framework" ou "Agent Orchestration Framework"?
2. **Functional Packs**: existem formalmente ou só `Core + Domain Packs`?
3. **autocoder**: permanece como default ou vira apenas um pack funcional?
4. **Exemplos públicos**: domínios reais ou apenas templates neutros?
5. **AGENTS.md**: topologia fixa ou protocolos + implementações?

---

## Política de Mantenção

### Domain Pack Status
- **Active**: Suportado, backward-compatible
- **Experimental**: Em desenvolvimento, pode ter breaking changes
- **Deprecated**: Legado, será removido

### Atualizações
- Dependências requerem compatibilidade reversa
-breaking changes precisam de RFC + aprovação unânime
- Nova capacidade = minor version bump

---

## Referências

- PRD: `docs/PRD_desverticalizacao_framework.md`
- Constituição: `docs/CONSTITUTION_emendada.md`
- Registry: `registry/registry.yaml`
- Templates: `templates/domain-pack/`