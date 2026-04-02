# Decision Trees para o AI Research Advisor

## Árvore 1: "Meu AUC está baixo, o que faço?"

```
AUC baixo (<0.80)?
│
├─ Em TODAS as classes?
│  ├─ SIM → Underfitting geral
│  │  ├─ Aumentar epochs
│  │  ├─ Aumentar LR
│  │  └─ Reduzir regularização (dropout, WD)
│  │
│  └─ NÃO → Problema localizado
│     ├─ É uma classe RARA (< 5% do dataset)?
│     │  ├─ SIM → Focal Loss (γ=2.0-3.0) + Class Weights
│     │  └─ NÃO → Confusão visual com outra classe
│     │     ├─ Treinar junto com classes que dão CONTEXTO
│     │     └─ CLAHE + augmentations específicas
│     │
│     └─ O AUC dessa classe é MAIOR no treino que na val?
│        ├─ SIM → Overfitting nessa classe
│        │  ├─ MixUp + CutMix
│        │  ├─ Mais dropout
│        │  └─ Label smoothing
│        └─ NÃO → O modelo não consegue aprender
│           ├─ Verificar qualidade dos labels (noise?)
│           └─ Verificar se a classe é detectável visualmente
```

## Árvore 2: "Devo trocar o backbone?"

```
Devo trocar o backbone?
│
├─ O backbone atual funciona bem em OUTROS grupos?
│  ├─ SIM → NÃO TROQUE. O problema é hiperparâmetro/dados
│  └─ NÃO → Considere trocar
│
├─ A resolução que preciso EXCEDE a nativa do backbone?
│  ├─ SIM e >50% acima → Considere backbone com resolução nativa maior
│  └─ NÃO ou <20% acima → Mantenha o backbone
│
├─ Já tentei TODAS as variações de hiperparâmetros?
│  ├─ NÃO → Faça ablation study primeiro
│  └─ SIM → Considere trocar backbone
│
└─ O dataset tem > 200k imagens?
   ├─ SIM → Modelos maiores podem funcionar (B4, ConvNeXt)
   └─ NÃO → Mantenha modelos menores (B2, B3)
```

## Árvore 3: "Qual estratégia de transfer learning usar?"

```
Transfer Learning Strategy
│
├─ Tenho um modelo generalista treinado NO MESMO dataset?
│  ├─ SIM → Progressive Fine-Tuning (backbone do generalista)
│  │  └─ LR = 1e-4 a 5e-5 (menor que o normal)
│  └─ NÃO → ImageNet pretrained (padrão)
│
├─ Tenho muitas imagens NÃO rotuladas do mesmo domínio?
│  ├─ SIM e > 200k → Self-supervised pre-training (SwAV/DINO)
│  └─ NÃO → ImageNet é suficiente
│
└─ Meu domínio é muito diferente do ImageNet?
   ├─ SIM (ex: microscopia, ultrassom) → Domain pre-training essencial
   └─ NÃO (ex: raio-X, natural images) → ImageNet funciona bem
```

## Mapa de Resolução por Patologia (Raio-X Torácico)

| Patologia | Res. Mínima | Res. Ideal | Justificativa |
|---|---|---|---|
| Cardiomegaly | 128px | 224px | Sinal global (tamanho do coração) |
| Effusion | 128px | 224px | Sinal global (opacificação basal) |
| Edema | 128px | 224px | Sinal difuso (borramento bilateral) |
| Atelectasis | 224px | 224px | Colapso de segmentos |
| Infiltration | 224px | 224px | Opacidade difusa |
| Consolidation | 224px | 224px | Opacidade lobar densa |
| Pneumonia | 224px | 260px | Opacidade com contexto |
| Emphysema | 224px | 260px+ | Hiperinsuflação sutil |
| Fibrosis | 224px | 260px+ | Textura reticular fina |
| Pleural_Thick | 224px | 320px | Espessamento pleural |
| Hernia | 224px | 320px | Interface diafragmática |
| Mass | 320px | 384px+ | Detecção de objeto (tamanho variável) |
| Nodule | 384px | 512px | Objeto pequeno (<3cm) |
| Pneumothorax | 384px | 512px | Linha pleural fina |

## Histórico de Experimentos Vitruviano (Resumo)

### Lição 1: Backbone Size vs Dataset Size
```
~100k imagens (NIH ChestX-ray14)

EfficientNet-B2 (9.2M) → VENCEU ✅
EfficientNet-B3 (12M)  → Perdeu
EfficientNet-B4 (19M)  → Perdeu (overfitting)
ConvNeXt-Tiny (28M)    → Perdeu (convergência lenta)
EfficientNet-V2-S (21M)→ Não testado na Golden Fleet

Conclusão: Para ~100k imagens, B2 é o sweet spot.
```

### Lição 2: Configuração Golden Fleet (a que funciona)
```
backbone: efficientnet_b2
resolution: 224px
focal_gamma: 3.0
label_smoothing: 0.1
dropout: 0.3
augmentations: [CLAHE, GridMask, MixUp]
batch_size: 32
learning_rate: 3e-4
weight_decay: 1e-4
```

### Lição 3: O que NÃO funcionou
```
- Class weights manuais: Instabilizam o treino
- Gamma > 4.0: Suprime demais gradientes
- Resolução >> nativa do backbone: Degradação
- Trocar backbone entre generalista e especialista: Piora
- Treinar sem MixUp: Overfitting
```
