---
name: ai-research-advisor
description: Skill de pesquisador de IA para diagnóstico de problemas de treinamento,
  recomendação de hiperparâmetros, e estratégias de melhoria para classificação multi-label
  de imagens médicas.
metadata:
  version: 1.0
---

# 🔬 AI Research Advisor

Skill para atuar como um **pesquisador de IA sênior**, fornecendo análise baseada em evidências para:
- Diagnosticar problemas de treinamento em modelos de classificação
- Recomendar hiperparâmetros com justificativa científica
- Propor experimentos controlados (ablation studies)
- Avaliar resultados e propor próximos passos

---

## 1. Metodologia Científica para Experimentos

### 1.1 Regra de Ouro: Uma Variável por Vez

**NUNCA mude múltiplas variáveis simultaneamente.** Se o AUC melhorou, você não saberá qual mudança causou a melhora.

```
❌ ERRADO: Mudar backbone + resolução + gamma + augmentations de uma vez
✅ CERTO:  Treinar controle, depois variar UMA coisa
```

### 1.2 Estrutura de Ablation Study

```
Experimento 0: CONTROLE (baseline exata do modelo que funciona)
Experimento 1: CONTROLE + Variação A
Experimento 2: CONTROLE + Variação B
Experimento 3: CONTROLE + Variação C
Experimento N: MELHOR resultado anterior + técnica avançada
```

### 1.3 Documentação Obrigatória

Para cada experimento, registrar:
- **Hipótese:** O que esperamos e por quê
- **Variável alterada:** Exatamente o que mudou vs. controle
- **Resultado:** Métricas obtidas (AUC por classe + macro)
- **Conclusão:** A hipótese foi confirmada ou refutada?
- **Próximo passo:** O que fazer com essa informação?

---

## 2. Diagnóstico de Problemas Comuns

### 2.1 AUC Baixo em Classes Específicas

**Checklist de Diagnóstico:**

| Sintoma | Causa Provável | Solução |
|---|---|---|
| AUC < 0.75 em TODAS as classes | Underfitting geral | Aumentar capacidade (mais epochs, LR maior, menos regularização) |
| AUC < 0.75 em ALGUMAS classes | Desbalanceamento ou confusão visual | Focal Loss com gamma adequado, ou especializar |
| AUC alto no treino, baixo na val | Overfitting | MixUp, CutMix, mais dropout, weight decay |
| AUC cai após epoch X | Overfitting tardio | Early stopping com patience adequado |
| AUC oscila muito entre epochs | Instabilidade de gradiente | Reduzir LR, aumentar batch, warmup mais longo |

### 2.2 Confusão Visual entre Patologias

Algumas patologias em raio-X torácico são visualmente similares:

| Par Confuso | Por que confunde | Estratégia |
|---|---|---|
| Edema ↔ Infiltração | Ambos são "mancha branca difusa" | Treinar junto com Cardiomegalia (contexto cardíaco) |
| Enfisema ↔ Normal | Hiperinsuflação sutil | Resolução mais alta, CLAHE |
| Fibrose ↔ Infiltração | Ambos são opacidades | CLAHE + foco em textura reticular vs. alveolar |
| Nódulo ↔ Massa | Diferença de tamanho | Resolução alta (≥ 384px), RandomCrop |
| Pneumotórax ↔ Normal | Linha pleural fina | Resolução ≥ 512px, Sharpen |

### 2.3 Quando a Resolução Importa (e Quando Não)

**Resolução AJUDA quando:**
- A doença tem **sinais pequenos** (nódulos, linha de pneumotórax)
- A doença depende de **textura fina** (enfisema = hiperinsuflação, fibrose = reticulação)

**Resolução NÃO AJUDA quando:**
- A doença tem **sinais globais** (cardiomegalia = coração grande)
- A doença é **difusa** (edema = borramento bilateral)
- O backbone NÃO foi projetado para essa resolução

**⚠️ Armadilha Comum:** Usar resolução acima da nativa do backbone.
- EfficientNet-B2: nativa = 260px. Usar 384px desperdiça capacidade.
- EfficientNet-B4: nativa = 380px.
- EfficientNet-V2-S: nativa = 384px.

---

## 3. Guia de Hiperparâmetros

### 3.1 Focal Loss - Gamma

O gamma controla o quanto o modelo ignora exemplos "fáceis" para focar nos "difíceis".

| Gamma | Efeito | Quando Usar |
|---|---|---|
| **0.0** | = BCE padrão (sem focal) | Baseline, classes balanceadas |
| **1.0** | Leve foco em difíceis | Classes levemente desbalanceadas |
| **2.0** | Foco moderado (**recomendado como ponto de partida**) | Desbalanceamento moderado, paper original |
| **3.0** | Foco forte | Desbalanceamento severo, classes raras |
| **4.0+** | Extremo (⚠️ perigoso) | Apenas se necessário após testar 2-3, pode instabilizar |

**Regra prática:** Se gamma > 3.0 e o AUC não melhora, o problema provavelmente NÃO é o gamma.

### 3.2 Learning Rate

| Cenário | LR Recomendado | Justificativa |
|---|---|---|
| Fine-tuning de ImageNet (1ª vez) | 1e-4 a 3e-4 | Exploração ampla |
| Fine-tuning de modelo próprio | 5e-5 a 1e-4 | Refinamento (pesos já bons) |
| Progressive (generalista → especialista) | 1e-4 a 5e-5 | Pesos muito próximos do ótimo |
| Backbone grande (B4, V2-S, ConvNeXt) | 2e-5 a 5e-5 | Mais parâmetros = precisa LR menor |
| Após mudar batch size | Linear scaling | `LR_novo = LR_base × (batch_novo / batch_base)` |

### 3.3 Batch Size

| Batch | Efeito | Trade-off |
|---|---|---|
| 8-12 | Mais ruído no gradiente | Pior convergência, permite resolução alta |
| 16-24 | Equilíbrio | Bom para maioria dos cenários |
| 32-48 | Gradiente estável | Melhor convergência, precisa mais LR e VRAM |
| 64+ | Muito estável | Pode perder capacidade de generalização |

**⚠️ Se forçado a usar batch pequeno (< 16) por VRAM:** usar `grad_accum_steps` para simular batch maior.

### 3.4 Regularização

| Técnica | Quando Usar | Config Típica |
|---|---|---|
| **MixUp** | Sempre (baseline de regularização) | alpha = 0.2 a 0.4 |
| **CutMix** | Classes com dependência espacial | alpha = 1.0 |
| **Label Smoothing** | Sempre | 0.05 a 0.1 |
| **Dropout** | Modelos com head customizado | 0.3 a 0.5 |
| **Weight Decay** | Sempre com AdamW | 1e-4 a 0.02 |
| **Early Stopping** | Sempre | patience = 7 a 15 |

---

## 4. Estratégias Avançadas

### 4.1 Progressive Fine-Tuning (Transfer do Generalista)

**Conceito:** Em vez de iniciar do ImageNet, iniciar dos pesos de um modelo que JÁ aprendeu features de raio-X.

```
ImageNet → Generalista Gold (14 classes) → Especialista (3 classes)
```

**Implementação:**
1. Carregar checkpoint do generalista
2. Transferir apenas pesos do BACKBONE (ignorar head/classificador, pois num_classes difere)
3. Criar novo head aleatório para N classes do especialista
4. Treinar com LR menor (1e-4 a 5e-5) pois os pesos já estão próximos do ótimo
5. Opcional: Congelar backbone por 2-5 epochs (warmup do head) antes de liberar

**Quando funciona melhor:**
- Dataset de treino é o MESMO (mesma distribuição de imagens)
- O especialista trata um SUBCONJUNTO das classes do generalista
- A qualidade do generalista é ALTA (AUC > 0.80)

### 4.2 Knowledge Distillation (do Ensemble)

**Conceito:** Usar as probabilidades (soft labels) do ensemble como alvo de treino de um modelo único.

```
Ensemble (5 modelos) → Soft labels → Modelo único (student)
```

**Implementação:**
```python
# Teacher (Ensemble) produz soft predictions
with torch.no_grad():
    teacher_logits = ensemble(images)
    teacher_probs = torch.sigmoid(teacher_logits)

# Student loss = alpha * hard_loss + (1-alpha) * soft_loss
hard_loss = focal_loss(student_logits, targets)
soft_loss = F.binary_cross_entropy_with_logits(student_logits, teacher_probs)
total_loss = 0.3 * hard_loss + 0.7 * soft_loss
```

### 4.3 Test-Time Augmentation (TTA)

**Conceito:** Ao fazer inferência, aplicar N augmentações e calcular a média das predições.

```python
def predict_with_tta(model, image, n_augments=5):
    preds = []
    for _ in range(n_augments):
        aug_image = apply_random_augmentation(image)
        with torch.no_grad():
            pred = torch.sigmoid(model(aug_image))
        preds.append(pred)
    return torch.mean(torch.stack(preds), dim=0)
```

**Ganho típico:** +0.5% a +2% AUC, SEM retreinar.

### 4.4 Self-Supervised Pre-training (SwAV/DINO)

Para datasets com muitas imagens não rotuladas, pré-treinar com self-supervised learning antes do fine-tuning supervisionado.

**Quando vale a pena:**
- Tem > 200k imagens (rotuladas + não rotuladas)
- O domínio é muito diferente do ImageNet (médico)
- Custo computacional é aceitável (dias de GPU)

---

## 5. Análise de Resultados

### 5.1 Interpretação de AUC

| AUC | Interpretação | Ação |
|---|---|---|
| > 0.95 | Excelente (quase perfeito) | Verificar se não há data leakage |
| 0.85-0.95 | Muito bom (clinicamente útil) | Calibrar probabilidades |
| 0.75-0.85 | Bom (útil com supervisão) | Buscar melhorias focadas |
| 0.65-0.75 | Fraco (limitações do dataset/doença) | Investigar causa raiz |
| < 0.65 | Inútil | Bug no código ou label noise |

### 5.2 Quando Trocar a Arquitetura

**NÃO TROQUE se:**
- O modelo atual tem AUC > 0.75 e você ainda não testou variações de hiperparâmetros
- Você mudou múltiplas variáveis e não sabe qual ajudou
- O mesmo backbone funciona bem em outros grupos

**TROQUE se:**
- Você fez ablation study exaustivo e o AUC não melhora
- A resolução necessária excede MUITO a resolução nativa do backbone
- Outro backbone mostrou resultado superior no MESMO dataset

### 5.3 Lição Vitruviano: A Supremacia do Generalista

**Aprendizado empírico deste projeto:**
> "Toda vez que tentamos backbones maiores ou mais complexos (B3, B4, ConvNeXt, V2-S), os resultados foram PIORES que o EfficientNet-B2 treinado na mesma configuração do generalista."

**Hipótese explicativa:**
- Com ~100k imagens do NIH, B2 (9.2M params) tem a razão ideal de parâmetros/dados
- Modelos maiores overfittam mais rápido neste volume de dados
- A melhor arquitetura para o especialista é a MESMA do generalista que funcionou

---

## 6. Checklist de Pesquisador

Antes de propor qualquer mudança:

- [ ] Verifiquei os resultados atuais e identifiquei o gap exato
- [ ] Consultei o histórico de experimentos para evitar repetir erros
- [ ] A proposta muda UMA variável por vez (ou justifica por quê não)
- [ ] A hipótese é testável e falsificável
- [ ] O controle (baseline) está claramente definido
- [ ] O critério de sucesso/falha está definido ANTES do treino
- [ ] Considerei se a solução é hi-parâmetro, dados, ou arquitetura
- [ ] Verifiquei VRAM disponível para a config proposta
- [ ] O tempo de treino é aceitável para o gain esperado

---

## 7. Referências e Estado da Arte (2024-2025)

### Focal Loss
- **Paper original (Lin et al., 2017):** γ=2.0 como default. α=0.25 para classes raras.
- **Prática médica:** γ=2.0 a 3.0 é o range mais efetivo. γ>4.0 raramente ajuda.

### Transfer Learning em Raio-X
- **SwAV/DINO self-supervised:** Pré-treinar no próprio dataset sem labels antes do supervised.
- **Progressive fine-tuning:** Múltiplos estágios (ImageNet → CheXpert → NIH → Especialista).
- **Domain-specific pre-training:** Modelos pré-treinados em CheXpert superam ImageNet.

### Ensemble Strategies
- **Weighted average:** Simples e efetivo para a maioria dos casos.
- **Priority/sovereignty:** Atribuir classe ao modelo que a detecta melhor.
- **Stacking:** Meta-learner que aprende a combinar os outputs.
- **Knowledge distillation:** Comprimir ensemble em modelo único para deploy.

### Data Augmentation Médica
- **CLAHE:** Essencial para contraste em raio-X (melhora detecção de textura).
- **MixUp (α=0.2):** Regularização mais efetiva e barata.
- **RandomCrop (224→196, depois resize):** Força foco em regiões locais.
- **ElasticTransform:** Simula variações anatômicas.
- **GridMask:** Drop aleatório de patches (similar a dropout espacial).

### Métricas
- **AUC-ROC:** Melhor métrica para desbalanceamento (invariante ao threshold).
- **AUC-PR (Precision-Recall):** Mais informativa para classes muito raras.
- **ECE (Expected Calibration Error):** Importante para confiabilidade clínica.
