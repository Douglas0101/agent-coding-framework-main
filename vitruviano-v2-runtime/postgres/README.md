# Postgres

Diretorio de suporte ao PostgreSQL 15+ do MVP.

## Estrutura

- `init/`: scripts SQL de bootstrap idempotente
- `seeds/`: seed controlado apenas para ambientes nao produtivos

## Observacoes

- Migracoes aplicacionais vivem em `apps/api/alembic/versions`
- O banco armazena catalogo clinico, workflow, auditoria e publication
- Dados PHI nao devem ser versionados neste repositorio
