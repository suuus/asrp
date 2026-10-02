# Agent integration

```text
ASRP Agent → ASRP Skills → asrp CLI → Structure records and manifests
```

The agent interprets architecture and asks humans about ownership, boundaries,
gates, and entry points. The CLI validates, fingerprints, resolves, verifies,
and compiles.

## Agent workflow

```text
Resolve Intent → Discover Structure → Confirm → Bind → Verify → Compile
```

Agents must not infer owners, approval, blocking semantics, or executable
commands from weak evidence. Existing artifacts should be referenced rather
than rewritten into a proprietary architecture language.

Before execution, show:

- Intent and Structure fingerprints;
- entry point and runner;
- blocking gates;
- required elements;
- expected Evidence;
- unresolved or missing Structure.

The compiled manifest is an execution contract, not approval. Apply ADRP
autonomy and user confirmation separately.
