---
description: Sessão guiada de refatoração com análise de code smells
---

# Refactor Session Workflow

Este workflow guia uma sessão de refatoração identificando code smells e sugerindo melhorias.

## ExecPara o desenvolvimento de sistemas de visão computacional (CV) enterprise escaláveis entre 2025 e 2026, a refatoração de algoritmos em Python deixou de ser apenas uma questão de "limpeza de código" para se tornar uma disciplina de **engenharia de sistemas de alta performance**.

As técnicas mais avançadas para refatoração em larga escala, integrando padrões PEP (Python Enhancement Proposals), segurança e escalabilidade, são detalhadas abaixo:

### 1. Engenharia de Refatoração: Do Monolítico ao Modular
O maior gargalo em projetos de IA enterprise é o envio de protótipos experimentais diretamente para produção.
*   **Decomposição de "Wall of Text" (WoT):** Refatorar scripts lineares e densos para estruturas **Orientadas a Objetos (OO)** ou **Programação Funcional (FP)** é essencial para isolar responsabilidades e facilitar testes unitários.
*   **Substituição de Unpacking de Tuplas por Estruturas Nomeadas:** Em algoritmos de CV que retornam múltiplos valores (ex: bounding boxes, scores, labels), o uso de tuplas posicionais é frágil; a técnica avançada exige o uso de **Named Tuples** ou **Dataclasses**, que garantem legibilidade e evitam erros de refatoração quando a assinatura da função muda.
*   **Encapsulamento para Prevenir Efeitos Colaterais:** Em Python, onde quase tudo é mutável, a refatoração deve focar em inicializar estados de forma controlada (usando `None` como default em vez de listas vazias) para evitar mutações não intencionais em chamadas subsequentes.

### 2. Performance e Escalabilidade (Otimização "Pythonic")
Em sistemas enterprise, a eficiência computacional dita o ROI do projeto.
*   **Vetorização sobre Loops:** A substituição de loops `for` por operações vetorizadas usando **NumPy** ou **PyTorch** utiliza instruções SIMD (Single Instruction, Multiple Data), processando dados em paralelo no nível da CPU/GPU.
*   **Transição de Pandas para Polars:** Para processamento de metadados de imagem em larga escala, a técnica atual é migrar de Pandas para **Polars**. O Polars utiliza um backend em Rust, execução multi-threaded nativa e uma **engine de avaliação preguiçosa (lazy evaluation)**, que otimiza o plano de consulta (column pruning e predicate pushdown) antes da execução, sendo até 10x mais rápido que o Pandas.
*   **Horizontal Scaling com Spark e `pandas_udf`:** Para lidar com bilhões de registros, utiliza-se o Apache Spark para distribuir tarefas em clusters, onde funções Python são aplicadas de forma distribuída via serialização do Apache Arrow.

### 3. Padrões Específicos para Visão Computacional Enterprise
Sistemas de CV escaláveis exigem arquiteturas que suportem invariância espacial e resoluções variadas.
*   **Compound Scaling (EfficientNet):** Em vez de escalar apenas a profundidade da rede, utiliza-se o escalonamento composto de **profundidade, largura e resolução** da imagem de forma conjunta e equilibrada.
*   **Spatial Pyramid Pooling (SPP):** Refatorar camadas de pooling tradicionais para SPP permite que a rede aceite imagens de tamanhos e escalas variados, gerando saídas de tamanho fixo para as camadas totalmente conectadas sem a necessidade de cropping destrutivo.
*   **Pipelines Multimodais e Layout Detection:** A refatoração moderna integra modelos como **YOLO-X** para detecção de layout em documentos complexos, seguida de OCR e chunking semântico para alimentar sistemas de RAG.

### 4. Parâmetros de Segurança e Governança ("Shift Left")
A segurança é tratada como um requisito de design de primeira classe (Security by Design).
*   **Estratégia "Shift Left":** Integrar ferramentas de **análise estática** (como Flake8 para PEP 8 e Bandit para segurança) no workflow de CI/CD para detectar vulnerabilidades e antipadrões antes do commit.
*   **Guardrails de Entrada e Saída:** Implementar camadas de validação que detectam **injeção de prompt** e **data poisoning**. Em sistemas de agentes (Agentic AI), utiliza-se o protocolo **MCP (Model Context Protocol)** para padronizar conexões seguras via OAuth 2.0 e isolar execuções de código em **sandboxes**.
*   **Observabilidade e Drift Detection:** O uso de métricas como o **PSI (Population Stability Index)** e testes de **Kolmogorov-Smirnov** monitoram se a distribuição dos dados de produção desviou significativamente dos dados de treino, disparando alertas de segurança ou retreino automático.

### 5. Padrões PEP e Conformidade
*   **PEP 8 e Além:** Embora o PEP 8 seja a base, em sistemas enterprise escaláveis, prioriza-se a legibilidade para o revisor sobre a conveniência do autor. Isso inclui o uso rigoroso de **f-strings** para interpolação otimizada e a exigência de **type hinting** para facilitar a manutenção por grandes equipes.
*   **Conformidade com o EU AI Act:** Refatorar sistemas para garantir a **explicabilidade (XAI)** e a capacidade de intervenção humana (Human-in-the-loop), classificando sistemas por nível de risco conforme as exigências regulatórias.Para o desenvolvimento de sistemas de visão computacional (CV) enterprise escaláveis entre 2025 e 2026, a refatoração de algoritmos em Python deixou de ser apenas uma questão de "limpeza de código" para se tornar uma disciplina de **engenharia de sistemas de alta performance**.

As técnicas mais avançadas para refatoração em larga escala, integrando padrões PEP (Python Enhancement Proposals), segurança e escalabilidade, são detalhadas abaixo:

### 1. Engenharia de Refatoração: Do Monolítico ao Modular
O maior gargalo em projetos de IA enterprise é o envio de protótipos experimentais diretamente para produção.
*   **Decomposição de "Wall of Text" (WoT):** Refatorar scripts lineares e densos para estruturas **Orientadas a Objetos (OO)** ou **Programação Funcional (FP)** é essencial para isolar responsabilidades e facilitar testes unitários.
*   **Substituição de Unpacking de Tuplas por Estruturas Nomeadas:** Em algoritmos de CV que retornam múltiplos valores (ex: bounding boxes, scores, labels), o uso de tuplas posicionais é frágil; a técnica avançada exige o uso de **Named Tuples** ou **Dataclasses**, que garantem legibilidade e evitam erros de refatoração quando a assinatura da função muda.
*   **Encapsulamento para Prevenir Efeitos Colaterais:** Em Python, onde quase tudo é mutável, a refatoração deve focar em inicializar estados de forma controlada (usando `None` como default em vez de listas vazias) para evitar mutações não intencionais em chamadas subsequentes.

### 2. Performance e Escalabilidade (Otimização "Pythonic")
Em sistemas enterprise, a eficiência computacional dita o ROI do projeto.
*   **Vetorização sobre Loops:** A substituição de loops `for` por operações vetorizadas usando **NumPy** ou **PyTorch** utiliza instruções SIMD (Single Instruction, Multiple Data), processando dados em paralelo no nível da CPU/GPU.
*   **Transição de Pandas para Polars:** Para processamento de metadados de imagem em larga escala, a técnica atual é migrar de Pandas para **Polars**. O Polars utiliza um backend em Rust, execução multi-threaded nativa e uma **engine de avaliação preguiçosa (lazy evaluation)**, que otimiza o plano de consulta (column pruning e predicate pushdown) antes da execução, sendo até 10x mais rápido que o Pandas.
*   **Horizontal Scaling com Spark e `pandas_udf`:** Para lidar com bilhões de registros, utiliza-se o Apache Spark para distribuir tarefas em clusters, onde funções Python são aplicadas de forma distribuída via serialização do Apache Arrow.

### 3. Padrões Específicos para Visão Computacional Enterprise
Sistemas de CV escaláveis exigem arquiteturas que suportem invariância espacial e resoluções variadas.
*   **Compound Scaling (EfficientNet):** Em vez de escalar apenas a profundidade da rede, utiliza-se o escalonamento composto de **profundidade, largura e resolução** da imagem de forma conjunta e equilibrada.
*   **Spatial Pyramid Pooling (SPP):** Refatorar camadas de pooling tradicionais para SPP permite que a rede aceite imagens de tamanhos e escalas variados, gerando saídas de tamanho fixo para as camadas totalmente conectadas sem a necessidade de cropping destrutivo.
*   **Pipelines Multimodais e Layout Detection:** A refatoração moderna integra modelos como **YOLO-X** para detecção de layout em documentos complexos, seguida de OCR e chunking semântico para alimentar sistemas de RAG.

### 4. Parâmetros de Segurança e Governança ("Shift Left")
A segurança é tratada como um requisito de design de primeira classe (Security by Design).
*   **Estratégia "Shift Left":** Integrar ferramentas de **análise estática** (como Flake8 para PEP 8 e Bandit para segurança) no workflow de CI/CD para detectar vulnerabilidades e antipadrões antes do commit.
*   **Guardrails de Entrada e Saída:** Implementar camadas de validação que detectam **injeção de prompt** e **data poisoning**. Em sistemas de agentes (Agentic AI), utiliza-se o protocolo **MCP (Model Context Protocol)** para padronizar conexões seguras via OAuth 2.0 e isolar execuções de código em **sandboxeução

### Fase 1: Análise de Complexidade

// turbo
1. **Identificar Funções Complexas (McCabe > 10)**
```bash
ruff check --select C901 src/ 2>/dev/null | head -15 || echo "No complexity issues"
```

// turbo
2. **Verificar Linhas por Arquivo**
```bash
find src/ -name "*.py" -exec wc -l {} + | sort -rn | head -10
```

### Fase 2: Code Smells

// turbo
3. **Imports Não Usados**
```bash
ruff check --select F401 src/ --output-format=text | head -10
```

// turbo
4. **Variáveis Não Usadas**
```bash
ruff check --select F841 src/ --output-format=text | head -10
```

// turbo
5. **Código Duplicado** (verificar manualmente)
```bash
echo "Verificar duplicação com: jscpd src/ --min-lines 10"
```

### Fase 3: Análise de Dependências

// turbo
6. **Dependências Circulares**
```bash
python -c "
import sys
sys.setrecursionlimit(50)
try:
    from src import training
    print('No circular imports detected')
except RecursionError:
    print('CIRCULAR IMPORT DETECTED!')
"
```

### Fase 4: Dead Code

// turbo
7. **Código Morto (vulture)**
```bash
vulture src/ --min-confidence 80 2>/dev/null | head -15 || echo "Install: pip install vulture"
```

### Fase 5: Refatoração Guiada

8. **Priorizar Refatorações**

   Com base nas análises anteriores:

   | Prioridade | Tipo | Ação |
   |------------|------|------|
   | Alta | Complexidade > 15 | Extract Method |
   | Alta | Arquivos > 500 linhas | Extract Class |
   | Média | Dead code | Remover |
   | Baixa | Imports não usados | Fix automático |

9. **Aplicar Fixes Automáticos**
```bash
ruff check --fix .
```

### Fase 6: Validação

// turbo
10. **Testes Continuam Passando**
```bash
pytest --benchmark-skip -q 2>&1 | tail -5
```

## Técnicas de Refatoração

### Extract Method
Para funções > 50 linhas, identifique blocos lógicos e extraia.

### Replace Conditional with Polymorphism
Para switch/if-else extensos, use Strategy Pattern.

### Introduce Parameter Object
Para funções com > 4 parâmetros, crie dataclass.

### Guard Clauses
Substitua nesting profundo por early returns.

## Critérios de Sucesso

- ✅ Complexidade máxima < 15
- ✅ Arquivos < 500 linhas
- ✅ Zero dead code (confidence > 80%)
- ✅ Testes passando
- ✅ Cobertura mantida

## Comando Único

```bash
make skill-refactor
```

## Próximos Passos

Após completar refatoração:
1. Commitar mudanças
2. Executar `/full-quality-check`
3. Atualizar documentação se necessário

## Skills Relacionadas

Consulte as skills avançadas para técnicas detalhadas:

| Skill | Descrição |
|-------|-----------|
| `enterprise-cv-refactoring` | Refatoração em larga escala para CV |
| `complexity-reduction` | Redução de complexidade ciclomática |
| `refactor-patterns` | Padrões de design e code smells |
| `dead-code-removal` | Eliminação de código morto |
| `training-circuit-quality` | Invariantes de circuitos de treinamento |

Para consultar: `view_file .agent/skills/<skill>/SKILL.md`
