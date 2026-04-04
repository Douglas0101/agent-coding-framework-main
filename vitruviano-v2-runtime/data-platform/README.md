# Data Platform

Camada de dados adjacente ao runtime clinico. Existe para suportar ciencia de dados, engenharia de dados, ML e AI sem quebrar a topologia oficial do MVP.

## Principio de fronteira

- `web`, `api` e `postgres` continuam sendo os unicos servicos centrais do produto
- `data-platform/` organiza ativos e pipelines de dados, mas nao introduz dependencia operacional obrigatoria no runtime clinico
- Treino, experimentacao e analise exploratoria devem consumir contratos formais vindos de `contracts/` e `artifacts/`

## Estrutura

- `governance/`: politicas, lineage, acesso, de-identification e compliance de dados
- `contracts/`: contratos de dados para DICOM, dados clinicos, labels e features
- `datasets/`: zonas de dados `raw`, `staging`, `curated`, `synthetic` e `external`
- `engineering/`: ingestao, validacao, transformacoes, qualidade e orquestracao
- `science/`: notebooks, cohort definition, EDA e estatistica aplicada
- `ml/`: treino, avaliacao, experimentos, registry e monitoramento de modelo
- `ai/`: fluxos de AI aplicada, prompts, avaliacao e safety
- `shared/`: schemas, metadata, dicionarios e utilitarios comuns

## Uso recomendado

1. Dados sensiveis reais ficam fora do versionamento e entram apenas por volumes seguros.
2. Datasets sinteticos e manifests podem ser versionados quando nao houver risco regulatorio ou de privacidade.
3. Toda entrega de modelo para o runtime deve sair de `ml/` para `artifacts/` via contrato formal.
