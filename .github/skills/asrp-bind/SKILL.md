---
name: asrp-bind
description: Bind an ASRP Structure record to the immutable fingerprint of an ADRP Intent record.
---

# Bind Structure to Intent

```bash
asrp bind-intent structure.json decision.json --output structure.bound.json
```

Treat the output as a new immutable artifact. The binding identifies which
Intent the Structure implements; it does not establish that Intent's standing.
