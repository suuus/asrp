# ASRP — Ape Structure Record Profile

> The durable Structure record layer for the ISEE Framework.

**ASRP** binds ratified Intent to architecture, ownership, boundaries, policy,
controls, agents, workflows, execution entry points, and required Evidence.

```text
Intent → Structure → Execution → Evidence
 ADRP       ASRP                       AERP
```

ASRP is a binding profile, not a replacement for C4, ArchiMate, ISO/IEC/IEEE
42010, Backstage, OpenAPI, AsyncAPI, Terraform, Bicep, Kubernetes, OPA, Cedar,
DMN, OSCAL, or GitHub workflows. It fingerprints and connects those artifacts
so an execution system can consume a small, explicit contract.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
asrp --version
```

## Core commands

```bash
asrp validate structure.json
asrp fingerprint structure.json
asrp inspect structure.json
asrp bind-intent structure.json decision.json --output structure.bound.json
asrp verify structure.json --artifact-root .
asrp resolve .github/structures --scope "production deployments"
asrp graph .github/structures
asrp compile .github/structures \
  --scope "production deployments" \
  --entry-point production-deployment \
  --output .github/isee/execution-manifest.json
```

The execution manifest carries exact ADRP Intent and ASRP Structure
fingerprints, selected elements, gates, artifacts, and Evidence requirements.
It is the contract ordinary Copilot instructions and automated execution agents
consume.

## Documentation

- [Standard](docs/STANDARD.md)
- [Recording Structure](docs/RECORDING_STRUCTURE.md)
- [Agent integration](docs/AGENT_INTEGRATION.md)
- [ISEE integration](docs/ISEE_INTEGRATION.md)
- [Worked example](docs/examples/production-deployment.v1.json)

## Status

ASRP `0.1.0` is alpha. Fingerprints provide local integrity but do not prove
architecture fitness, policy correctness, ownership consent, or permission to
execute.

## License

[MIT](LICENSE)
