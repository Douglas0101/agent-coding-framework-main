# Contracts

Contratos versionados que desacoplam web, api e origem dos artefatos de modelo.

## Pastas

- `artifact-manifest/`: schema do `manifest.json` do artefato de modelo
- `findings/`: representacao canonica de findings e confidence scores
- `report-schema/`: schema do laudo estruturado textual + JSON canonico
- `openapi/`: snapshots versionados da API publica do MVP

## Regra de uso

Qualquer mudanca de contrato deve anteceder a implementacao de rota, persistencia ou UI dependente.
