# API App

Backend FastAPI unico do MVP. Contem API clinica, regras de negocio, persistencia e runtime de inferencia PyTorch.

## Estrutura

- `app/api/v2/routes/`: endpoints canonicos do MVP
- `app/core/config/`: configuracao, settings e feature flags controladas
- `app/core/security/`: JWT, MFA, hashing, autorizacao e hardening
- `app/core/logging/`: logs estruturados, correlacao e observabilidade minima
- `app/domain/`: entidades e regras centrais do dominio clinico
- `app/services/dicom/`: ingestao, checksum e validacao DICOM
- `app/services/inference/`: carregamento de artefato, preprocessamento e analise
- `app/services/reporting/`: draft, versionamento, assinatura e PDF
- `app/services/publication/`: release, withhold e patient publication
- `app/services/audit/`: trilha auditavel append-only e hash chain
- `app/infra/db/`: sessao, models ORM e acesso ao PostgreSQL
- `app/infra/repositories/`: adaptadores de persistencia
- `app/infra/storage/`: acesso ao storage DICOM
- `app/infra/artifacts/`: validacao de `MODEL_PATH`, `CALIBRATION_PATH` e `manifest.json`
- `app/infra/observability/`: health, ready e runtime diagnostics
- `app/schemas/`: Pydantic DTOs e schemas OpenAPI
- `app/tests/`: suites unitarias e de integracao
- `alembic/versions/`: historico de migracoes

## Endpoints esperados

- `/health`
- `/ready`
- `/ops/runtime`
- `/auth/*`
- `/patients/*`
- `/studies/*`
- `/reports/*`
- `/patient/publications/*`

## Limites importantes

- O runtime de inferencia nao roda como servico separado
- Sem Redis, Triton ou fila de jobs
- `ready` falha quando banco, storage ou artefato obrigatorio nao estiverem validos
