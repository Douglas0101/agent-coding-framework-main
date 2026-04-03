# `.opencode/manifests` (public subset)

Somente manifests **sanitizados** devem ser versionados em `./sanitized/`.

Não versionar neste diretório:
- manifests de execução com dados de sessão,
- paths locais de máquina,
- evidências sensíveis,
- conteúdo transitório de runtime.
