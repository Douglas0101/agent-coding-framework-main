# 🚀 Vitruviano: Ideias Futuras & Roadmap V3

Este documento registra estratégias avançadas para a próxima geração do Vitruviano, focadas em superar os limites da arquitetura atual (classificação multi-label global).

---

## 1. 🧬 Grupo "Pleural Complex" (Segmentação Implícita)
**Conceito:** Doenças pleurais (Effusion, Pleural_Thickening, Pneumothorax) ocorrem em regiões anatômicas específicas (bordas pulmonares, seios costofrênicos).
**Estratégia:**
- Treinar um modelo focado **apenas em crops das bordas pulmonares**.
- Ignorar o centro da imagem (coração/mediastino) para reduzir ruído.
- **Goal:** Melhorar a distinção entre "linha fina preta" (pneumotórax) e "linha grossa branca" (espessamento), eliminando a confusão com estruturas centrais.

## 2. 🕵️‍♂️ "Anomaly Detector" para Doenças Raras (Hérnia, Nódulo)
**Conceito:** Hérnia (0.2%) e Nódulo (5%) são eventos raros e localizados. Modelos supervisionados tendem a ignorá-los devido ao desbalanceamento extremo.
**Estratégia:**
- Treinar um **Autoencoder** ou **One-Class SVM** apenas com imagens NORMAIS.
- Na inferência, qualquer desvio significativo na reconstrução indica uma anomalia.
- **Goal:** Detectar qualquer padrão não-normal, garantindo alta sensibilidade para Hérnias e Nódulos sem precisar de milhares de exemplos positivos.

## 3. ⚖️ Hierarchical Classification (Árvore de Decisão Neural)
**Conceito:** A decisão clínica é hierárquica, não "tudo ao mesmo tempo".
**Estratégia:** Cascata de modelos em árvore:
1.  **Triagem (Binário):** Normal vs Anormal (Alta Sensibilidade).
2.  **Grupo (Multiclasse):** Opacidade vs Estrutural vs Pleural.
3.  **Específico (Expert):** (Se Opacidade) -> Pneumonia vs Infiltração vs Atelectasia.
- **Goal:** Reduzir a confusão entre categorias distantes e permitir que especialistas foquem apenas nas distinções sutis do seu ramo.

## 4. 🖼️ Patch-Based Learning (Alta Resolução Real)
**Conceito:** Doenças texturais (Fibrose, Enfisema, Infiltração) exigem resolução de ~1024px, mas B4@380px é o limite de VRAM atual. Resize destrói a textura.
**Estratégia:**
- Dividir a imagem (1024x1024) em **16 patches de 256x256**.
- Passar cada patch por uma CNN leve (MobileNet/EfficientNet-B0).
- Agregar as features com um Transformer ou LSTM (MIL - Multiple Instance Learning).
- **Goal:** O modelo "vê" a resolução total e a textura fina da Fibrose sem estourar a memória, detectando padrões invisíveis em downsampling.

## 5. 🔄 "Contrastive Refinement" (Hard Pair Mining)
**Conceito:** O modelo confunde pares específicos (ex: Infiltração vs Pneumonia, Edema vs Infiltração).
**Estratégia:**
- Identificar os pares de confusão mais frequentes na matriz de confusão.
- Criar datasets balanceados apenas com esses pares.
- Treinar classificadores binários "Tira-Teima" usando **Contrastive Loss** (forçar a separação no espaço latente).
- **Goal:** Aumentar a especificidade em diagnósticos diferenciais difíceis.

---
**Status Atual (Fev 2026):**
- Focando na consolidação da Golden Fleet (V1/V2) e reestruturação clínica (Planos C e D).
- As ideias acima ficam como backlog para a **Versão 3.0**.
