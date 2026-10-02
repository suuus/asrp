# ASRP in ISEE

ISEE is the operating framework documented at
[agentile.org](https://agentile.org).

## Install

```bash
copilot plugin marketplace add suuus/isee-plugins
copilot plugin install isee-suite@isee
```

This loads the complete ADRP → ASRP → Execution → AERP workflow. Install only
ASRP with `copilot plugin install asrp@isee`.

## Regular Copilot

Compile active Structure:

```bash
asrp compile .github/structures \
  --scope "this repository" \
  --entry-point repository-development \
  --output .github/isee/execution-manifest.json
```

An ISEE projection tool can turn that manifest into
`.github/instructions/isee.instructions.md`, which Copilot loads automatically.
For one session, explicitly attach it:

```text
@.github/isee/execution-manifest.json implement the requested change
```

## Agentic flow

```text
ADRP resolve and autonomy
    ↓
ASRP resolve and compile
    ↓
human or policy approval
    ↓
execution agent or platform
    ↓
AERP capture and verify
    ↓
ADRP/ASRP review on material drift
```

The execution system receives the manifest rather than every rich source
document. Evidence should bind to both ADRP and ASRP fingerprints.
