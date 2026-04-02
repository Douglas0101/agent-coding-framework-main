---
name: rpa-engineer
description: Pipeline RPA de governanca com AST, code-quality avancado, foundation, enterprise e security gate
---

# RPA Engineer Skill

## Objetivo

Orquestrar validacoes de engenharia com trilha de auditoria e policy gate
determinístico, priorizando execução swarm para CI/release.

## Fluxo recomendado

- Primário: `scripts/rpa_swarm.py` (orquestrador por agentes).
- Secundário/legado: `scripts/rpa_engineer.py` (pipeline linear).

## Comandos Principais

```bash
# Swarm padrão para CI robusto
python scripts/rpa_swarm.py --goal ci-stabilize --profile ci --fail-fast

# Release gate estrito (recomendado em pipeline de release)
python scripts/rpa_swarm.py --goal release-gate --profile release --quality-profile strict --replay-verify-strict

# Planejamento sem execução
python scripts/rpa_swarm.py --goal release-gate --plan-only
```

```bash
# Pipeline linear legado (quando necessário)
python scripts/rpa_engineer.py

# Enforcement completo (enterprise + seguranca + code-quality bloqueantes)
python scripts/rpa_engineer.py --strict-enterprise --security-profile ci

# Waiver temporario e explicito para CVEs conhecidos (time-boxed)
python scripts/rpa_engineer.py --strict-enterprise --security-profile ci --security-max-high 3

# Ajustar escopo do gate de code-quality
python scripts/rpa_engineer.py --code-quality-path src --code-quality-path scripts

# Ajustar profundidade maxima de loops no gate algoritmico
python scripts/rpa_engineer.py --code-quality-max-loop-depth 4

# Pular fases opcionais (pipeline linear)
python scripts/rpa_engineer.py --skip-code-quality
python scripts/rpa_engineer.py --skip-enterprise
python scripts/rpa_engineer.py --skip-security
```

### Wrapper da Skill

```bash
.agent/skills/rpa-engineer/scripts/run_rpa.sh .
.agent/skills/rpa-engineer/scripts/run_rpa.sh . --strict-enterprise --security-profile ci
```

## Política de Bloqueio (Swarm)

Baseline obrigatório:

- `ast`
- `foundation`
- `design_patterns`

Regras atuais relevantes:

- `design_patterns` é bloqueante no registry.
- `design_patterns` também é forçado como bloqueante por rulebook em
  `config/swarm_policy_rulebook.json`.
- Em `release`, outros agentes podem ser forçados como bloqueantes
  (`code_quality`, `enterprise`, `security`, `test_coverage`, `foundation`).

Anti-bypass obrigatório:

- Se `include/exclude/skip` remover agente mandatório, a execução falha com erro
  `mandatory agents removed by include/exclude/skip: ...`.
- Isso inclui tentativas indiretas por filtros de input.

Exemplos de comandos inválidos sob policy mandatória:

```bash
# Invalido: remove agente mandatorio
python scripts/rpa_swarm.py --goal ci-stabilize --exclude-agent design_patterns

# Pode ser invalido se policy resolver code_quality como mandatorio
python scripts/rpa_swarm.py --goal release-gate --profile release --skip-code-quality
```

## Política de Bloqueio (Pipeline linear)

- Padrao: `AST` e `Foundation` sao bloqueantes.
- `CodeQuality`, `Enterprise` e `Security` sao advisory por padrao.
- `--strict-enterprise`: torna `CodeQuality`, `Enterprise` e `Security` bloqueantes.
- Overrides de policy de seguranca: `--security-max-*` (uso temporario com ticket).

## Artefatos

- Swarm JSON canônico: `artifacts/rpa/swarm_report.json`
- Policy + trilha de execução: `artifacts/rpa/swarm/`
- Design patterns: `artifacts/design_patterns/design_patterns_summary.json` e
  `artifacts/design_patterns/design_patterns_report.txt`
- Pipeline linear: `artifacts/rpa/rpa_report.json`
- Segurança: `artifacts/security/vulnerability_report.txt` e
  `artifacts/security/vulnerability_summary.json`

## Interpretacao Rapida

- Retorno `0`: fases bloqueantes aprovadas.
- Retorno `1`: falha em pelo menos uma fase bloqueante.
- Em swarm, trate qualquer violação de agente mandatório como bloqueante.
- Use `--strict-enterprise` no pipeline linear quando precisar enforcement total.

## Baseline de Seguranca Aplicada

- OWASP ASVS 5.0.0 para controles de verificacao de aplicacao.
- NIST SSDF (SP 800-218/218A) para praticas seguras no SDLC e IA generativa.
- CWE Top 25 para priorizacao das fraquezas mais impactantes.

## Runbook de Dependencias Criticas

- Plano para CVEs de Torch: `docs/torch_security_remediation_plan.md`
