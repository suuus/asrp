# Recording Structure

## What belongs in ASRP

Use ASRP when Intent has been materialised into stable operating Structure:

- component and service boundaries;
- agent capabilities and tool boundaries;
- ownership and escalation;
- interfaces and dependencies;
- blocking and advisory gates;
- policy and control artifacts;
- execution workflows and entry points;
- Evidence obligations.

Do not use ASRP for aspirations, unapproved options, runtime results, or a copy
of every architecture document. ADRP owns decision-bearing Intent; AERP owns
observed Evidence.

## Workflow

1. Resolve active ADRP records.
2. Identify the Structure that implements them.
3. Preserve existing architecture and policy artifacts.
4. Hash and reference those artifacts.
5. Record actors, elements, gates, and entry points.
6. Define Evidence obligations.
7. Bind exact ADRP records using `asrp bind-intent`.
8. Validate and verify artifacts.
9. Compile the execution manifest.
10. Review Structure when Evidence or architecture drift invalidates it.

## Safety questions

- Is every owner confirmed?
- Does every entry point identify its required gates?
- Are blocking and advisory semantics explicit?
- Are artifact paths portable and hashes current?
- Are dependencies complete?
- Is every Evidence obligation measurable?
- Are ADRP bindings exact?
- Would a new operator understand where execution begins and where it must stop?
