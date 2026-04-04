# Domain Packs

This directory contains domain-specific extensions for the Agent Orchestration Framework.

## Structure

```
domains/
├── software-engineering/    # Default functional pack
├── ml-ai/                   # ML/AI domain pack (experimental)
├── medical-imaging/         # Medical imaging domain pack (experimental)
└── README.md                # This file
```

## What are Domain Packs?

Domain Packs are contractual extensions that provide domain-specific capabilities without coupling to the Core. They implement the `DomainPackContract` interface and register via the Extension Registry.

## Pack Types

### Functional Packs
Provide general-purpose capabilities (e.g., software engineering workflows). These are typically active and serve as the foundation for the framework.

### Vertical Packs
Provide domain-specific capabilities for specialized fields (e.g., ML/AI, Medical Imaging). These are typically experimental and optional.

## Available Packs

| Pack | Type | Status | Description |
|------|------|--------|-------------|
| software-engineering | functional | active | Default development workflow capabilities |
| ml-ai | vertical | experimental | ML/AI training, optimization, experiment tracking |
| medical-imaging | vertical | experimental | Medical image analysis and reporting |

## Creating a New Domain Pack

1. Create directory: `domains/<domain-name>/`
2. Add `contract.yaml` following the template in `templates/domain-pack/`
3. Add `manifest.json` with pack metadata
4. Register in `registry/registry.yaml`

## Dependencies

- ML/AI pack requires Software Engineering pack
- Medical Imaging pack requires both Software Engineering and ML/AI packs

## Compliance

All Domain Packs must:
1. Implement the DomainPackContract
2. Pass constitutional invariant validation
3. Register in the Extension Registry
4. Be versioned semantically

See `templates/domain-pack/` for the official contract template.