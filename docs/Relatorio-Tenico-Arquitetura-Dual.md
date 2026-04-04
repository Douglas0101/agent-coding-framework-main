Entendi perfeitamente. A arquitetura correta é **hierárquica e condicional**, não monolítica. Vou gerar o relatório técnico que estabelece essa separação de concerns entre qualidade universal (obrigatória) e excelência algorítmica (contextual).

---

# Relatório Técnico: Arquitetura de Núcleo Dual para Deep Agents Framework

**Versão:** 4.1.0  
**Data:** 2026-04-04  
**Classificação:** Especificação de Arquitetura Obrigatória

## 1. Fundamentação Arquitetural

### 1.1 O Problema da Universalidade Forçada
A aplicação indiscriminada de padrões IOI Gold Tier em cenários de negócio comuns (CRUD, APIs REST, Workers de integração) gera:
- **Over-engineering**: Complexidade acidental em soluções simples
- **Custo cognitivo**: Manutenção de estruturas desnecessárias (Eertree em validação de formulário)
- **Violação do princípio YAGNI**: Implementação de otimizações prematuras
- **Débito técnico**: Código "esperto" que dificulta onboarding

### 1.2 Solução: Separação de Níveis de Obrigatoriedade
Adotamos uma arquitetura de **Dois Núcleos Obrigatórios** com ativação condicional baseada em análise de escopo.

---

## 2. Núcleo Obrigatório Universal (NOU)

Aplica-se a **100% das tarefas de código**. Não há exceções.

### 2.1 Especificação do Contrato

```yaml
# /.internal/core/universal-quality-contract.yaml
core_id: universal-quality-core
version: 4.1.0
applicability: "ALL_CODE_GENERATION_TASKS"
mandatory: true
activation: "ALWAYS_ON"

quality_dimensions:
  type_safety:
    explicit_typing: "OBRIGATÓRIO - Nenhum tipo implícito permitido"
    null_safety: "OBRIGATÓRIO - Option/Maybe/Nullable tratado explicitamente"
    generics_constraints: "OBRIGATÓRIO - Type parameters bounded quando aplicável"
    casts: "PROIBIDO - Casting direto sem validação de tipo prévia"
    
  architecture_invariants:
    single_responsibility: "Cada função/classe/módulo possui uma única razão para mudar"
    dependency_direction: "Dependências apontam para dentro (Dependency Inversion)"
    encapsulation: "Estado interno protegido, interface pública mínima necessária"
    immutability_preference: "Estruturas imutáveis por padrão, mutação justificada"
    
  code_clarity:
    naming_semantics: "Nomes revelam intenção, não implementação (intention-revealing)"
    function_size: "Máximo 20 linhas de código efetivo (SLoc)"
    cyclomatic_complexity: "Máximo 10 por função"
    nesting_depth: "Máximo 3 níveis de indentação"
    comments: "Explicam 'por que', não 'o que' (o código deve ser legível)"
    
  security:
    input_validation: "TODAS as entradas externas validadas antes de processamento"
    injection_prevention: "Query parameters/bindings obrigatórios, nunca concatenação"
    secrets_management: "Nenhum hardcoded credential, uso de vaults/env vars"
    error_infoleak: "Mensagens de erro não revelam stack trace interno em produção"
    
  error_handling:
    exceptions_vs_values: "Preferir retorno de Result/Error ao invés de exceções para fluxos esperados"
    recovery_strategy: "Cada erro deve ter caminho de recuperação definido"
    logging: "Erros logados com contexto suficiente para debugging (correlation_id, stack, inputs)"
    fail_fast: "Validações de pré-condição nas primeiras linhas (guard clauses)"
    
  testing:
    unit_coverage: "Toda lógica de negócio coberta por testes unitários"
    edge_cases: "Testes para: vazio, nulo, limite máximo, limite mínimo, formato inválido"
    integration_boundary: "Mocks para dependências externas, testes de contrato"
    regression_prevention: "Testes que falham se comportamento existente for alterado inadvertidamente"
    
  project_conventions:
    style_guide: "Conformidade com linter/formatter do projeto (ESLint, Prettier, Black, etc)"
    directory_structure: "Colocação de arquivos seguindo arquitetura estabelecida (Clean, Hexagonal, etc)"
    existing_patterns: "Preservação de padrões existentes (não inventar novos se já há padrão)"
    
  change_justification:
    breaking_changes: "Documentação obrigatória de incompatibilidades e migration path"
    refactoring_reason: "Justificativa técnica para refatorações (debito técnico mensurado)"
    performance_claims: "Benchmarks antes/depois para otimizações (não otimizar no escuro)"

output_requirements:
  compliance_notes: "Seção obrigatória no output listando conformidade com cada dimensão acima"
  architecture_decision_log: "Registro de decisões arquiteturais significativas (ADRs)"
  risk_assessment: "Identificação de riscos de segurança/performance introduzidos"

enforcement_gates:
  - gate: pre_commit_validation
    checks: [linting, type_checking, complexity_analysis]
  - gate: pr_review_checklist
    checks: [security_scan, test_coverage_threshold, architecture_conformance]
  - gate: ci_cd_quality
    checks: [regression_tests, performance_baseline, dependency_vulnerability]
```

### 2.2 Exemplos de Aplicação do NOU

**Cenário: CRUD Simples (TypeScript/Node)**
```typescript
// ❌ ANTES (Viola NOU - tipagem implícita, sem validação, erro exposto)
function createUser(data) {
  const user = db.insert(data);
  return user;
}

// ✅ DEPOIS (Conforme NOU)
interface CreateUserInput {
  email: string;          // Tipo explícito
  name: string;
  age: number;
}

interface CreateUserResult {
  success: boolean;
  user?: User;
  error?: ValidationError | DatabaseError;  // Erros tipados
}

function createUser(input: CreateUserInput): Result<CreateUserResult> {
  // 1. Validação explícita (Security)
  const validation = validateUserInput(input);
  if (!validation.isValid) {
    return Result.err(new ValidationError(validation.errors));
  }
  
  // 2. Guard clause (Fail fast)
  if (await userExists(input.email)) {
    return Result.err(new DuplicateError("Email already registered"));
  }
  
  // 3. Operação com tratamento de erro (Error handling)
  try {
    const user = await db.insert(sanitizeInput(input)); // Sanitização
    logger.info("User created", { userId: user.id, correlationId: getContext().correlationId });
    return Result.ok({ success: true, user });
  } catch (error) {
    logger.error("Database error creating user", { error, input: redactSensitive(input) });
    return Result.err(new DatabaseError("Failed to create user")); // Infoleak prevention
  }
}
```

**Cenário: Worker de Integração (Python)**
```python
# ✅ Conforme NOU - Invariantes explícitas, tratamento de erro, logging estruturado
from typing import Optional, Result
from dataclasses import dataclass
from enum import Enum

class ProcessingStatus(Enum):
    SUCCESS = "success"
    RETRYABLE = "retryable"
    PERMANENT_ERROR = "permanent_error"

@dataclass(frozen=True)  # Imutabilidade
class IntegrationPayload:
    order_id: str
    amount: Decimal  # Tipo específico, não float
    customer_id: str
    
    def validate(self) -> Optional[list[str]]:
        errors = []
        if not self.order_id:
            errors.append("order_id required")
        if self.amount <= 0:
            errors.append("amount must be positive")
        return errors if errors else None

class OrderWorker:
    def __init__(self, api_client: ApiClient, repository: OrderRepository) -> None:
        # Inversão de dependência
        self._api = api_client
        self._repo = repository
        
    async def process(self, payload: IntegrationPayload) -> Result[ProcessingStatus]:
        # 1. Validação explícita
        if errors := payload.validate():
            logger.warning("Invalid payload", extra={"errors": errors, "payload": payload})
            return Result.err(ProcessingStatus.PERMANENT_ERROR)
            
        # 2. Idempotência (Arquitetura)
        if await self._repo.is_processed(payload.order_id):
            logger.info("Duplicate message ignored", extra={"order_id": payload.order_id})
            return Result.ok(ProcessingStatus.SUCCESS)
            
        try:
            # 3. Operação com retry estratégico
            result = await self._api.send_with_retry(
                payload, 
                max_retries=3,
                backoff_strategy=ExponentialBackoff()
            )
            
            await self._repo.mark_processed(payload.order_id, result.external_id)
            return Result.ok(ProcessingStatus.SUCCESS)
            
        except RetryExhaustedError:
            logger.error("API unavailable after retries", extra={"order_id": payload.order_id})
            return Result.err(ProcessingStatus.RETRYABLE)  # DLQ
        except AuthenticationError:
            logger.critical("API credentials invalid")
            return Result.err(ProcessingStatus.PERMANENT_ERROR)
```

---

## 3. Núcleo Obrigatório Especializado (NOE)

Ativado **condicionalmente** baseado em análise de escopo algorítmico.

### 3.1 Mecanismo de Detecção de Escopo

```yaml
# /.internal/core/scope-detection-engine.yaml
scope_analyzer:
  detection_triggers:
    complexity_indicators:
      patterns_in_description:
        - "optimize|optimization|efficient|performance critical"
        - "large (dataset|input|scale).*[0-9]{5,}"  # n > 100k
        - "real-time|streaming|low latency"
        - "graph|tree|path|connectivity|flow"
        - "query.*range|range.*query|quantile|median"
        - "string.*pattern|palindrome|substring|suffix"
        - "parallel|concurrent|distributed processing"
        - "competitive programming|algorithmic challenge"
        
      data_structure_hints:
        - "segment tree|fenwick|binary indexed"
        - "shortest path|minimum spanning|max flow"
        - "dynamic programming.*state.*compression"
        - "heavy.*light|centroid|link.*cut"
        - "FFT|NTT|matrix exponentiation"
        
      constraint_patterns:
        - "n ≤ 10^5|10^6|10^7"
        - "time limit.*(1s|2s)"
        - "memory limit.*(256MB|512MB)"
        
  classification_rules:
    tier_1_universal:
      condition: "NOT complexity_indicators AND (CRUD OR API OR Simple Worker)"
      active_core: "universal_only"
      
    tier_2_algorithmic:
      condition: "complexity_indicators AND (Optimization OR Graph OR String)"
      active_core: "universal + algorithmic_frontier"
      required_techniques: ["complexity_analysis", "advanced_data_structures", "optimization_patterns"]
      
    tier_3_competitive:
      condition: "complexity_indicators AND (Competitive Programming OR IOI/ICPC)"
      active_core: "universal + algorithmic_frontier + competitive_patterns"
      required_techniques: ["ioi_gold_tier", "frontier_algorithms", "proof_of_correctness"]

activation_protocol:
  on_scope_detected: "Injetar constraints do NOE no contexto do modo"
  override_capability: "Engenheiro sênior pode forçar desativação via flag @no-optimization-tier"
  verification: "Checklist de conformidade específica do tier ativado"
```

### 3.2 Especificação do Núcleo Especializado

```yaml
# /.internal/core/algorithmic-frontier-contract.yaml
core_id: algorithmic-frontier-core
version: 4.1.0
applicability: "SCOPE_DEPENDENT - Ativado por detection_triggers"
mandatory: "CONDITIONAL - Obrigatório quando scope=tier_2 ou tier_3"
parent_core: "universal-quality-core"  # Herda todos os requisitos do NOU

specialized_dimensions:
  complexity_guarantees:
    asymptotic_analysis: "Big-O, Big-Ω, Big-Θ documentados para todos os algoritmos"
    constraint_satisfaction: "Verificação matemática de adequação aos limites de entrada"
    tight_bounds: "Prova de que não existe solução assintoticamente melhor (quando aplicável)"
    
  algorithmic_patterns:
    data_structures_advanced:
      - "Segment Tree (Lazy, Persistent, 2D, Dynamic)"
      - "Fenwick Tree (2D, Range updates)"
      - "Trie (Standard, Xor, Persistent)"
      - "Disjoint Set Union (Union-Find with rollback)"
      - "Sparse Table (RMQ)"
      - "Splay Tree / Treap (Implicit, Indexed)"
      
    graph_algorithms:
      - "Dijkstra (Standard, 0-1 BFS, Multi-source)"
      - "Bellman-Ford (SPFA optimization)"
      - "Floyd-Warshall (Detection of negative cycles)"
      - "Network Flow (Dinic, Edmonds-Karp, Min-Cost Max-Flow)"
      - "Matching (Hopcroft-Karp, Hungarian)"
      - "SCC (Kosaraju, Tarjan)"
      - "Bridges & Articulation Points"
      - "Heavy-Light Decomposition"
      - "Centroid Decomposition"
      - "LCA (Binary Lifting, Euler Tour + RMQ)"
      
    string_algorithms:
      - "KMP (Prefix function)"
      - "Z-Algorithm"
      - "Manacher (Palindromes)"
      - "Rolling Hash (Single/Double)"
      - "Suffix Array (O(n log n) construction)"
      - "Suffix Automaton"
      - "Aho-Corasick"
      - "Eertree (Palindromic Tree) - Tier 3 only"
      
    mathematical:
      - "Fast Exponentiation (Matrix, Modular)"
      - "Sieve (Eratosthenes, Linear, Segmented)"
      - "FFT/NTT (Polynomial multiplication)"
      - "Combinatorics (Modular inverse, Lucas theorem)"
      - "Number Theory (Extended GCD, CRT, Mobius)"
      
    optimization_techniques:
      - "Dynamic Programming (Digit, SOS, Optimization techniques)"
      - "Greedy (Exchange argument proofs)"
      - "Binary Search on Answer"
      - "Meet-in-the-Middle"
      - "Parallel Binary Search (Offline queries)"
      - "Mo's Algorithm (Sqrt decomposition on queries)"
      
  frontier_algorithms_tier3:
    specialized_structures:
      - "Link-Cut Tree (Dynamic connectivity in forests)"
      - "Wavelet Tree (Range quantile queries)"
      - "Persistent Data Structures (Segment Tree, Treap)"
      - "Treap with implicit keys (Rope data structure)"
      
    advanced_graphs:
      - "Link-Cut Tree for dynamic MST"
      - "Heavy-Light with edge/vertex values"
      - "DP on Trees with DSU on Tree (Small-to-Large)"
      - "Virtual Tree construction"
      
    computational_geometry:
      - "Convex Hull (Graham Scan, Monotone Chain)"
      - "Line Sweep (Event-based processing)"
      - "Closest Pair of Points"
      
    metaheuristics:
      - "Simulated Annealing (when exact solution is NP-hard)"
      - "Genetic Algorithms (for optimization landscapes complexos)"

implementation_requirements:
  code_quality_inheritance: "DEVE obedecer NOU mesmo em código algorítmico"
  explicit_typing_maintained: "Tipos explícitos em variáveis de controle de algoritmos"
  safety_in_algorithms: "Verificação de overflow em operações aritméticas (int64 vs int128)"
  test_coverage: "Stress tests contra brute force para verificação de corretude"
  
  documentation_advanced:
    complexity_proof: "Argumento matemático de corretude e complexidade"
    invariant_documentation: "Invariantes de loop e estruturais documentados"
    edge_case_analysis: "Análise explícita de casos limite (overflow, empty, max constraints)"
    reference: "Citação de algoritmo base (autor/origem quando conhecido)"

output_requirements_extended:
  algorithm_selection_rationale: "Por que esta estrutura/algoritmo foi escolhido vs alternativas"
  complexity_table: |
    | Operação | Complexidade | Justificativa |
    |----------|-------------|---------------|
    | Build    | O(n log n)   | Ordenação inicial |
    | Query    | O(log n)     | Traversal da árvore |
    | Update   | O(log n)     | Path compression |
  benchmark_note: "Performance esperada contra constraints máximos"

enforcement_gates_specialized:
  - gate: algorithmic_validation
    checks:
      - "complexity_proof_verification"
      - "stress_test_passing"
      - "constraint_satisfaction_check"
  - gate: frontier_algorithm_audit
    checks:
      - "correctness_invariant_verification"
      - "memory_usage_optimization"
      - "cache_efficiency_analysis"
    condition: "only_for_tier_3"
```

---

## 4. Matriz de Aplicação por Cenário

| Cenário | Tier Ativo | Cores Aplicáveis | Exemplo de Trigger | Técnicas Esperadas |
|---------|-----------|------------------|-------------------|-------------------|
| **CRUD API Simples** | 1 | NOU apenas | "Criar endpoint REST para cadastro" | Validação, tipagem, tratamento de erro, testes unitários |
| **Worker de Integração** | 1 | NOU apenas | "Processar fila de mensagens RabbitMQ" | Idempotência, retry, circuit breaker, logging |
| **Refatoração de Domínio** | 1 | NOU apenas | "Extrair serviço de pagamento" | Preserve behavior, testes de regressão, interfaces claras |
| **Sistema de Recomendação** | 2 | NOU + NOE | "Calcular similaridade entre 10^6 usuários" | Otimização O(n log n), cache locality, matrizes esparsas |
| **Query Engine** | 2 | NOU + NOE | "Range queries dinâmicas em dataset grande" | Segment Tree/Fenwick, análise de complexidade |
| **Roteamento de Veículos** | 2 | NOU + NOE | "Otimizar rotas com 1000+ paradas" | Dijkstra/A*, heurísticas, grafos esparsos |
| **Competição de Programação** | 3 | NOU + NOE + Competitive | "Problema IOI de árvore dinâmica" | Link-Cut Tree, provas formais, stress testing |
| **Motor de Busca de Palíndromos** | 3 | NOU + NOE + Competitive | "Encontrar todos os subpalíndromos em texto 10^6" | Eertree, suffix automaton, O(n) garantido |

---

## 5. Implementação no Framework

### 5.1 Estrutura de Diretórios

```
/.internal/
├── core/
│   ├── universal-quality-contract.yaml          # NOU - Sempre ativo
│   ├── algorithmic-frontier-contract.yaml       # NOE - Condicional
│   └── scope-detection-engine.yaml              # Motor de classificação
├── modes/
│   └── autocoder/
│       ├── contract.yaml                        # Referencia ambos os núcleos
│       └── scope-adapters/
│           ├── crud-adapter.yaml                # Tier 1
│           ├── optimization-adapter.yaml        # Tier 2  
│           └── competitive-adapter.yaml         # Tier 3
└── packs/
    ├── software-engineering/                    # Implementação NOU
    └── algorithmic-computing/                   # Implementação NOE
```

### 5.2 Fluxo de Execução

```yaml
execution_flow:
  1_input_analysis:
    action: "Parse da descrição da tarefa"
    engine: "scope-detection-engine"
    output: "classification_tier (1, 2, or 3)"
    
  2_context_assembly:
    if_tier_1:
      inject: ["universal-quality-contract"]
    if_tier_2:
      inject: ["universal-quality-contract", "algorithmic-frontier-contract"]
      restrict: "algorithmic_patterns tier 1-2 only"
    if_tier_3:
      inject: ["universal-quality-contract", "algorithmic-frontier-contract", "competitive-patterns"]
      restrict: "all frontier algorithms available"
      
  3_generation:
    constraints: "Unir restrições de todos os contratos ativos"
    priority: "NOU prevalece sobre NOE em conflitos (ex: legibilidade > micro-otimização)"
    
  4_validation:
    gates: "Executar enforcement gates correspondentes ao tier"
    rejection_criteria: "Falha em qualquer gate do NOU rejeita imediatamente"
```

### 5.3 Exemplo de Detecção Automática

**Input do Usuário:**
> "Preciso otimizar a busca de menores valores em ranges de um array que recebe atualizações frequentes. O array tem tamanho 200.000 e precisa responder 50.000 queries por segundo."

**Análise do Scope Detection:**
- Trigger match: "range.*query", "200.000", "atualizações frequentes", "otimizar"
- Classification: `tier_2_algorithmic`
- Cores ativados: NOU + NOE
- Algoritmo sugerido: Segment Tree with Lazy Propagation ou Fenwick Tree (dependendo das operações específicas)
- Complexidade exigida: O(log n) por operação
- Validação obrigatória: Prova de que O(n) por query seria insuficiente (200k * 50k = 10^10 operações)

**Output do Sistema:**
```yaml
scope_detection_result:
  tier: 2
  confidence: 0.95
  triggers_matched: ["large_scale", "range_query", "update_operations", "optimize"]
  cores_activated: ["universal-quality-core", "algorithmic-frontier-core"]
  recommended_approach: "Segment Tree with Lazy Propagation"
  complexity_requirement: "O(log n) per operation"
  universal_constraints: "Tipo explícito para índices e valores, tratamento de erro para índices out-of-bounds, testes de stress contra brute force O(n)"
```

---

## 6. Considerações Finais

### 6.1 Princípio da Obrigatoriedade Graduada
A qualidade não é opcional, mas **a especialização é contextual**. O NOU garante que até um CRUD simples seja seguro, testável e manutenível. O NOE garante que quando o problema exige excelência algorítmica, ela seja aplicada com rigor matemático.

### 6.2 Anti-Padrões Evitados
- **Não há "opt-out" do NOU**: Mesmo em scripts de uma linha, tipagem e tratamento de erro são obrigatórios
- **Não há "opt-in" casual do NOE**: Não se aplica LCT em problema de negócio comum só porque "é elegante"
- **Separação clara de concerns**: Um engenheiro de domínio trabalha com NOU. Um engenheiro de algoritmos trabalha com NOU+NOE.

### 6.3 Evolução
O NOE pode ser expandido com novas estruturas (Quantum Trees, Neural-Assisted Heuristics) sem afetar o NOU. O NOU evolui com novos padrões de segurança (novas OWASP, por exemplo) aplicando-se a todo o codebase automaticamente.

---

**Documento válido a partir de:** 2026-04-04  
**Próxima revisão:** Após acumulação de 3 casos de uso de Tier 3 em produção
