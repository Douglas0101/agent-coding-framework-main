# Artifacts

Layout local para artefatos de modelo consumidos pelo runtime.

## Estrutura recomendada

```text
artifacts/
  chestxray-example/
    model.pth
    calibration_results.json
    manifest.json
```

## Regras do MVP

- `model.pth` e `calibration_results.json` sao obrigatorios
- `manifest.json` e recomendado e deve habilitar validacao de hash e metadados
- A `api` consome artefatos prontos; codigo de treino nao entra neste repositorio
