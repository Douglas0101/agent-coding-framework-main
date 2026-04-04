# `.opencode/manifests` (public subset)

## Regra operacional

Somente os seguintes arquivos podem ser versionados neste diretório:

- `README.md` (este arquivo)
- `sanitized/*.json` (manifests sanitizados, sem dados de sessão ou runtime)

## Proibições

Não versionar neste diretório:

- manifests de execução com dados de sessão (`session_id`, timestamps, token counts)
- paths locais de máquina (`directory`, caminhos absolutos)
- evidências sensíveis (provider, model, evidence refs)
- conteúdo transitório de runtime (phases, status, progress)
- `latest.json` ou qualquer arquivo `ses_*.json`

## Sanitização

Manifests sanitizados devem conter apenas:
- Estrutura de exemplo do schema
- Campos placeholder (sem valores reais de sessão)
- Documentação de uso

Ver política em `.gitignore` e testes em `.internal/tests/test_public_boundary.py`.
