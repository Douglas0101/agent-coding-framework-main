# Vitruviano V2 MVP Runtime

Scaffold interno do novo repositorio de runtime clinico, derivado de `PRD_SDD_Vitruviano_V2_Freeze_Candidate.md`.

## Decisoes refletidas nesta estrutura

- Apenas tres servicos de produto: `web`, `api` e `postgres`
- Runtime de inferencia PyTorch dentro da `api`
- `DICOM SR`, `FHIR`, `Redis`, `Triton`, filas assincronas e telemetria distribuida ficam fora do MVP
- Storage DICOM, artefatos de modelo, backup e proxy reverso sao dependencias de deploy, nao servicos centrais do produto
- A estrutura de dados e IA existe como dominio adjacente de suporte, sem virar servico central do MVP

## Mapa do repositorio

```text
vitruviano-v2-runtime/
  apps/
    web/         # Next.js: frontend clinico + portal do paciente
    api/         # FastAPI: API, regras clinicas e runtime de inferencia
  postgres/      # bootstrap e seed controlado do banco
  contracts/     # contratos canonicos: findings, report e artifact manifest
  data-platform/ # base para data engineering, data science, ML e AI
  deploy/        # compose canonico e arquivos de ambiente
  artifacts/     # montagem local de artefatos de modelo
  storage/       # pontos de montagem locais para DICOM e backups
  docs/          # arquitetura, rastreabilidade, validacao e runbooks
  scripts/       # automacao de desenvolvimento, CI e operacao
  tests/         # suites sistemicas, performance e seguranca
```

## Relacao com o PRD/SDD

- `apps/web` cobre worklist, viewer, editor de laudo, dashboard minimo e portal do paciente
- `apps/api` cobre autenticacao, RBAC, DICOM upload, analise, assinatura, release/withhold e publication
- `contracts/` materializa o versionamento explicito de schema de laudo, findings e artefato
- `data-platform/` organiza datasets, pipelines, governanca, ciencia de dados e trilhas de ML/AI
- `deploy/compose` fixa a topologia canonica do MVP com `web + api + postgres`
- `artifacts/` segue o contrato `model.pth + calibration_results.json + manifest.json`
- `tests/` espelha a estrategia minima de verificacao do documento

## Proximo passo recomendado

1. Inicializar `apps/api` com `pyproject.toml`, FastAPI e Alembic.
2. Inicializar `apps/web` com Next.js e o layout das features do MVP.
3. Definir os schemas em `contracts/` antes de expor rotas clinicas.
