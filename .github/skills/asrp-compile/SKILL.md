---
name: asrp-compile
description: Compile active ASRP Structure into a deterministic ISEE execution manifest for a named entry point.
---

# Compile an execution manifest

```bash
asrp compile .github/structures \
  --scope "production deployments" \
  --entry-point production-deployment \
  --as-of "2026-10-02T12:00:00Z" \
  --output .github/isee/execution-manifest.json
```

Show the user blocking gates, runner, command, Intent and Structure
fingerprints, and required Evidence before execution.
