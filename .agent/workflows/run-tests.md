---
description: Run the ITCH pipeline test suite with verbose output
---

# Run Tests

// turbo-all

1. Run full test suite with verbose output:
```bash
python -m pytest tests/ -v --tb=short
```

2. Run only protocol tests:
```bash
python -m pytest tests/test_data/test_itch_protocol.py -v --tb=short
```

3. Run only order book tests:
```bash
python -m pytest tests/test_data/test_itch_order_book.py -v --tb=short
```

4. Run only pipeline integration tests:
```bash
python -m pytest tests/test_data/test_itch_pipeline.py -v --tb=short
```

5. Run only feature engineering tests:
```bash
python -m pytest tests/test_features/test_microstructure.py -v --tb=short
```

6. Run with coverage report (if pytest-cov is installed):
```bash
python -m pytest tests/ -v --tb=short --cov=src --cov-report=term-missing 2>/dev/null || python -m pytest tests/ -v --tb=short
```
