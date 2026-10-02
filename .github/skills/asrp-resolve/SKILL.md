---
name: asrp-resolve
description: Resolve active ASRP Structure records for an exact scope and time.
---

# Resolve Structure

```bash
asrp resolve .github/structures \
  --scope "production deployments" \
  --as-of "2026-10-02T12:00:00Z"
```

Consume `active`, `excluded`, and `summary`. No active Structure means no
compiled execution contract; it does not mean unrestricted execution.
