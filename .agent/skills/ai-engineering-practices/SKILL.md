---
name: ai-engineering-practices
description: Strict guidelines for software engineering safety, project organization,
  and code quality in AI development.
metadata:
  version: 1.0
---

# 🏗️ AI Engineering Best Practices

This skill outlines the mandatory protocols for organizing files, structuring code, and performing refactoring operations within the Vitruviano project. Its primary goal is to ensure stability and prevent data loss.

## 1. Safety & Refactoring Protocol (Priority #1) 🛡️

### The Golden Rule of Deletion
**NEVER delete a file or directory without explicit, confirmation-checked approval.**
- If a file seems unused, move it to `scripts/archive/` or `_deprecated/`.
- If a deletion is absolutely necessary, verify it is not imported anywhere using `grep` or `vulture`.
- Always prefer renaming (e.g., `old_script.py`) over deleting.

### The Dry Run Principle
Before executing any structural change (move, rename, delete):
1.  **List Impact:** Identify which files will be affected.
2.  **Verify Imports:** Check if moving a file breaks imports in other files.
3.  **Plan Rollback:** Know exactly how to undo the change if it fails.

---

## 2. Project Organization (Folder Structure) 📂

Strictly adhere to this layout to maintain separation of concerns:

- **`src/` (Source Code):** content that is imported.
    - `data/`: Data loading pipelines, transformations, dataset classes.
    - `models/`: Neural network architectures (`nn.Module`).
    - `training/`: Training loops, loss functions, optimizers.
    - `serving/`: API and inference logic (FastAPI, Flask).
    - `utils/`: Helper functions (logging, visualization).
    - `config/`: Configuration schemas (Pydantic).

- **`scripts/` (Executables):** Entry points for running tasks.
    - `train_*.py`: Training launchers.
    - `eval_*.py`: Evaluation scripts.
    - `archive/`: Old scripts, one-off analyses, and deprecated code. **(Safe Haven)**

- **`experiments/` or `notebooks/`:**
    - Exploratory analysis and prototyping. Code here is not production-ready.

- **`tests/`:**
    - Unit tests mirroring the `src/` structure.

---

## 3. Class Design & Modularity (SOLID for AI) 🧩

### Single Responsibility Principle
- **Dataset Class:** Responsible ONLY for loading and transforming data items.
- **Model Class:** Responsible ONLY for the forward pass. Does not handle training logic.
- **Trainer Class:** Responsible for the training loop, checkpointing, and logging. It orchestrates the Model and Dataset.

### Dependency Injection
- Do not instantiate heavy objects (databases, models) inside a class constructor. Pass them as arguments.
- Example: Pass the `optimizer` to the `Trainer`, don't create it inside. This allows swapping optimizers easily.

### Configuration Objects
- Avoid passing 20 arguments to a function. Use a `Config` object (dataclass/Pydantic).
- Example: `Trainer(config: TrainingConfig)` instead of `Trainer(lr, batch_size, epochs, ...)`

---

## 4. Experiment Tracking & Reproducibility 🧪

- **Unique IDs:** Every training run must have a unique identifier (UUID or timestamp).
- **Artifacts:** Save model weights, logs, and configuration snapshots in `outputs/<run_id>/`.
- **determinism:** Set seeds for random number generators (`torch`, `numpy`, `python`) to ensure reproducible runs.

## 5. Development Workflow 🔄

1.  **Prototype:** Write a script in `notebooks/` or `scripts/` to test an idea.
2.  **Refactor:** Once working, move core logic to functions/classes in `src/`.
3.  **Integrate:** Update the script to import from `src/`.
4.  **Test:** Verify the refactored code works as expected.
5.  **Clean Up:** Move the original prototype script to `scripts/archive/` (optional).
