# ADR-001: Taxonomia — Core vs Skill vs Domain Pack

**Status:** aceito  
**Data:** 2026-04-04  
**Decisor:** core-team  
**Contexto:** PRD Framework 2.0, §4 Princípios, §13 Riscos

## Problema

O framework possui três camadas de extensão que podem gerar confusão taxonômica:
- **Core:** protocolos domain-agnostic (Verifier, Synthesizer, Handoff, Evidence)
- **Skills:** capacidades incrementais vinculadas a modos específicos
- **Domain Packs:** extensões contratuais para domínios verticais

Sem taxonomia clara, há risco de:
1. Duplicação de funcionalidades entre camadas
2. Skills que deveriam estar no Core ou em Domain Packs
3. Domain Packs que redefinem protocolos do Core (violação de invariante)

## Decisão

### Regras de classificação

| Camada | O que pertence | O que NÃO pertence |
|--------|---------------|-------------------|
| **Core** | Protocolos, interfaces, invariantes, schemas de contrato | Lógica de domínio, ferramentas específicas, análises especializadas |
| **Skill** | Capacidade incremental ativada por trigger contextual, com budget próprio e contrato de entrada/saída | Funcionalidade indispensável ao modo, protocolo transversal, lógica de domínio |
| **Domain Pack** | Conjunto de capacidades para um domínio vertical (ex: medical-imaging, ml-ai) | Funcionalidade domain-agnostic, skill isolada sem contexto de domínio |

### Critérios obrigatórios para nova Skill

Toda skill nova deve responder:
1. **Modo-alvo:** qual dos 4 modos a ativa?
2. **Por que não Core?** não é protocolo, interface ou invariante
3. **Por que não Domain Pack?** não é específica de um domínio vertical
4. **Trigger:** quando ativa (automático, manual, condicional)?
5. **Budget:** qual fração do budget do modo consome?
6. **Contrato I/O:** quais são os contratos de entrada e saída?
7. **Evidência:** qual política de evidence produz?
8. **Regressão:** quais testes garantem que não quebra o modo?

### Invariantes taxonômicos

| ID | Invariante | Enforcement |
|----|-----------|-------------|
| TAX-001 | Core não pode depender de Skill | Import analysis |
| TAX-002 | Core não pode depender de Domain Pack | Import analysis |
| TAX-003 | Skill não pode redefinir protocolo Core | Schema validation |
| TAX-004 | Domain Pack não pode redefinir protocolo Core | CI validation |
| TAX-005 | Skill deve declarar modo-alvo explícito | Schema validation |
| TAX-006 | Skill budget_share deve somar ≤ 1.0 por modo | Static analysis |

## Consequências

### Positivas
- Clareza na classificação de novas capacidades
- Prevenção de duplicação entre camadas
- Core permanece magro e domain-agnostic

### Negativas
- Overhead de documentação para novas skills
- Necessidade de revisão taxonômica em code reviews

## Alternativas rejeitadas

1. **Unificar Skill e Domain Pack:** rejeitado porque skills são incrementais/modais e packs são verticais/domínio
2. **Permitir Core estensível por plugins:** rejeitado porque viola invariante de Core domain-agnostic
