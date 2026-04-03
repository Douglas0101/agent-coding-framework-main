# Git Flow - Guia de Workflow para Equipe

## Visão Geral

Este projeto utiliza **Git Flow** para gestão de branches, garantindo:
- Desenvolvimento paralelo sem conflitos
- Código estável sempre em produção
- Rastreabilidade de todas as alterações
- Colaboração eficiente entre membros

---

## Estrutura de Branches

```
main (produção)
    ↑
    │    ← merge via PR (aprovação obrigatória)
    │
release/v1.0.0
    ↑
    │    ← merge via PR
    │
develop (integração)
    ↑
    │    ← merge via PR
    │
feature/nova-funcionalidade  ← cada membro cria o seu
hotfix/correcao-urgente      ← se necessário, a partir de main
```

| Branch | Origen | Destino | Quando usar |
|--------|--------|---------|-------------|
| `main` | — | — | Código em produção (protegido) |
| `develop` | `main` | `main` via PR | Integração da próxima release |
| `feature/*` | `develop` | `develop` via PR | Nova funcionalidade |
| `release/*` | `develop` | `main` + `develop` | Preparação de versão |
| `hotfix/*` | `main` | `main` + `develop` | Correção urgente em produção |

---

## Regras de Ouro

1. **NUNCA** fazer push direto para `main` ou `develop`
2. **SEMPRE** criar branch de feature a partir de `develop` atualizado
3. **OBRIGATÓRIO** PR (Pull Request) para todo merge
4. **SEMPRE** fazer `git pull --rebase` antes de push
5. **APENAS** administradores podem fazer merge em `main` e `develop`

---

## Configuração Inicial (Primeira vez)

### 1. Clonar o repositório
```bash
git clone https://github.com/Douglas0101/agent-coding-framework-main.git
cd agent-coding-framework-main
```

### 2. Configurar rebase como padrão (já feito globalmente)
```bash
git config --global pull.rebase true
git config --global rebase.autoStash true
```

### 3. Criar branch local de desenvolvimento
```bash
git checkout develop
git pull --rebase origin develop
```

---

## Fluxo de Trabalho Diário

### Cenário 1: Desenvolver uma nova funcionalidade

```bash
# 1. Garantir que está em develop atualizado
git checkout develop
git pull --rebase

# 2. Criar branch de feature
git checkout -b feature/minha-nova-funcionalidade

# 3. Trabalhar normalmente
# (editar, adicionar, commitar)
git add .
git commit -m "feat: adicionar nova funcionalidade"

# 4. Manter atualizado com origin/develop (se necessário)
git fetch origin
git rebase origin/develop

# 5. Enviar para o remoto (primeira vez)
git push -u origin feature/minha-nova-funcionalidade

# 6. Criar Pull Request via GitHub UI
# https://github.com/Douglas0101/agent-coding-framework-main/pull/new/feature/minha-nova-funcionalidade
```

### Cenário 2: Sincronizar com o trabalho do colega

```bash
# Atualizar seu branch com as últimas alterações
git checkout feature/minha-funcionalidade
git fetch origin
git rebase origin/develop
```

### Cenário 3: Correção urgente (hotfix)

```bash
# hotfix sempre parte de main
git checkout main
git pull --rebase

git checkout -b hotfix/correcao-urgente

# corrigir, commitar
git add .
git commit -m "hotfix: correção de bug crítico"

# Push e PR direto para main
git push -u origin hotfix/correcao-urgente
# Criar PR com base em main, comparando com hotfix
```

### Cenário 4: Preparar uma release

```bash
# ensure develop está atualizado
git checkout develop
git pull --rebase

# Criar branch de release
git checkout -b release/v1.0.0

# Testar, ajustar versão, commitar últimas correções
git add .
git commit -m "release: preparação para v1.0.0"

# Merge em main
git checkout main
git merge release/v1.0.0
git push origin main

# Merge em develop
git checkout develop
git merge release/v1.0.0
git push origin develop

# Deletar branch de release
git branch -d release/v1.0.0
```

---

## Commands Rápidos de Referência

```bash
# Verificar status
git status
git branch -vv

# Atualizar branches
git fetch origin
git pull

# Listar branches
git branch -a

# Deletar branch local
git branch -d feature/minha-feature

# Deletar branch remoto
git push origin --delete feature/minha-feature

# Ver histórico
git log --oneline -10

# Ver diferença
git diff origin/develop..HEAD
```

---

## Configuração de Proteção de Branch (GitHub)

Para configurar, siga estes passos na interface do GitHub:

1. Acesse **Settings → Branches → Branch protection rules**
2. Clique em **Add rule**
3. Configure para `main`:
   - ✅ Require a pull request before merging
   - ✅ Require approvals (1)
   - ✅ Dismiss stale approvals when new commits pushed
   - ✅ Require branches to be up to date before merging
   - ✅ Include administrators
4. Repita para `develop` com as mesmas configurações

---

## Conflitos? Veja Como Resolver

### Durante rebase
```bash
# Git vai indicar os arquivos com conflito
git status

# Editar os arquivos (marcados como "both modified")
# Resolver manualmente

git add arquivo-com-conflito.py
git rebase --continue
```

### Dicas para evitar conflitos
- Sempre faça `git fetch && git rebase` antes de começar a trabalhar
- Communicate com o colega sobre o que está desenvolvendo
- Commite frequentemente para manter o histórico limpo
- Use branches pequenos e com foco único

---

## Dúvidas?

Em caso de dúvidas ou problemas:
1. Consulte este guia
2. Verifique o estado atual: `git status && git branch -vv`
3. Peça ajuda ao responsável pelo projeto

---

**Última atualização:** 2026-04-03
**Versão:** 1.0
