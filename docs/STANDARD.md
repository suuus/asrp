# Ape Structure Record Profile v1

## Purpose

ASRP is the durable Structure record layer of:

```text
Intent → Structure → Execution → Evidence
 ADRP       ASRP                       AERP
```

It answers how active Intent is materialised into components, agents,
responsibilities, interfaces, dependencies, boundaries, controls, workflows,
entry points, executable artifacts, and Evidence obligations.

## Trust boundaries

- ADRP establishes Intent standing and applicability.
- ASRP records Structure and compiles execution contracts.
- Execution systems perform actions.
- AERP records resulting Evidence.
- ASRP validation does not approve an execution.
- A matching artifact digest does not prove architectural correctness.

## Canonical record

The canonical JSON schema is
`schemas/ape-structure-record-v1.schema.json` with
`schema_version: ape-structure-record/v1`.

A record has stable logical `structure_id`, version-specific `record_id`,
positive `record_version`, lifecycle `status`, and canonical SHA-256
fingerprint.

## Intent binding

Every binding identifies an exact ADRP record by:

- `decision_id`;
- `record_id`;
- `record_version`;
- canonical `record_fingerprint`.

An Intent binding means the Structure claims to implement that record. It does
not independently prove the record is active or authoritative.

## Structural model

Actors identify people, teams, organisations, agents, or systems. Elements
represent components, agents, responsibilities, interfaces, dependencies,
control gates, workflows, entry points, Evidence obligations, or boundaries.

ASRP references established source artifacts rather than embedding every
architecture or policy language. Each referenced artifact has a portable
relative path, media type, role, and SHA-256 digest.

## Gates and entry points

Gates are blocking or advisory. Entry points identify a runner, optional
command, required elements, and required gates. A command is descriptive input
to orchestration; ASRP itself never executes it.

## Evidence requirements

An Evidence requirement states:

- requirement identity;
- expected AERP evidence type;
- subject;
- acceptable results;
- required artifact roles;
- criteria references;
- related gates.

Passing one requirement does not establish general compliance.

## Resolution

`asrp resolve` filters by exact normalised scope, effective lifecycle, highest
active record version, supersession, and active dependencies. An empty active
set is unresolved Structure, not unrestricted permission.

## Execution manifest

`asrp compile` produces `isee-execution-manifest/v1`. Compilation selects one
named entry point, expands its element dependencies, includes required gates and
Evidence obligations, and preserves exact ADRP and ASRP fingerprints.

The same inputs and explicit `--as-of` timestamp produce the same manifest,
identifier, and fingerprint.

## Integrity

The record fingerprint is SHA-256 over canonical UTF-8 JSON with
`integrity.record_fingerprint` set to null. The manifest uses the same rule with
`integrity.manifest_fingerprint` set to null.

Fingerprints are not signatures.
