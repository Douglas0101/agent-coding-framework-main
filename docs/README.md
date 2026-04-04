# Documentação — Agent Orchestration Framework

**Referencia Normativa:** [CONSTITUTION_emendada.md](CONSTITUTION_emendada.md)  
**PRD Ativo:** [PRD_desverticalizacao_framework.md](PRD_desverticalizacao_framework.md)  
**Runbook:** [ADOPTION_RUNBOOK.md](ADOPTION_RUNBOOK.md)

---

## Documentos Principais

| Documento | Descricao | Status |
|-----------|-----------|--------|
| [CONSTITUTION_emendada.md](CONSTITUTION_emendada.md) | Fonte da verdade autoritaria — invariantes, contratos, governanca | ✅ Ratificada |
| [PRD_desverticalizacao_framework.md](PRD_desverticalizacao_framework.md) | Plano de transicao para Core domain-agnostic | ✅ Em execucao |
| [ADOPTION_RUNBOOK.md](ADOPTION_RUNBOOK.md) | Guia de adocao para mantenedores | ✅ Publicado |

---

## Arquitetura

### Core (Nivel 0)

- `specs/core/orchestration-contract.yaml` — Interfaces e protocolos do Core
- O Core define a gramatica de orquestracao, nao a semantica de dominio
- Protocolos: Verifier, Synthesizer, Handoff, Evidence
- Invariantes: INV-001 a INV-007 (ver Constituicao)

### Domain Packs

- `domains/software-engineering/` — Pack funcional default (ativo)
- `domains/ml-ai/` — Pack ML/AI (experimental, opcional)
- `domains/medical-imaging/` — Pack Medical Imaging (experimental, opcional)

### Extension Registry

- `registry/registry.yaml` — Catalogo de todos os Domain Packs registrados

### Templates

- `templates/domain-pack/` — Templates oficiais para criacao de novos packs

---

## CI/CD

| Workflow | Descricao | Gatilho |
|----------|-----------|---------|
| `constitutional-compliance.yml` | Validacao de invariantes constitucionais, contract compliance, drift detection | Push/PR em specs, domains, registry |
| `routing-regression.yml` | Regressao de routing + paridade de config | Push/PR em config/spec |
| `public-artifacts-guard.yml` | Verificacao de boundary publico | Push/PR em main/master |
| `public-repo-guard.yml` | Scanner de padroes sensiveis + allowlist | Push/PR em main/master/develop |

---

## Glossario

| Termo | Definicao |
|-------|-----------|
| **Core** | Camada de orquestracao domain-agnostic (nivel 0) |
| **Domain Pack** | Extensao contratual que fornece capacidades de dominio |
| **Functional Pack** | Pack que fornece capacidades transversais (ex: software engineering) |
| **Vertical Pack** | Pack que fornece capacidades de dominio especifico (ex: ML, Medical) |
| **Extension Registry** | Catalogo de packs disponiveis para ativacao |
| **DomainPackContract** | Contrato formal que todo pack deve implementar |
| **Verifier** | Protocolo do Core — gate obrigatoria pre-sintese |
| **Synthesizer** | Protocolo do Core — escritor final de artefatos |
| **Handoff** | Transferencia formal de controle entre agentes |
| **Evidence Trail** | Dados imutaveis e auditaveis produzidos por agentes |

---

## Referencias Externas

- [OpenCode Documentation](https://opencode.ai)
- [Spec-Driven Architecture](https://github.com/spec-driven)
- [Conventional Commits](https://www.conventionalcommits.org/)
