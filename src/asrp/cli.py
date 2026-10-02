#!/usr/bin/env python3
"""Validate, bind, resolve, and compile ISEE Structure records."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VERSION = "0.1.0"
RECORD_SCHEMA_VERSION = "ape-structure-record/v1"
MANIFEST_SCHEMA_VERSION = "isee-execution-manifest/v1"
ADRP_SCHEMA_VERSION = "ape-decision-record/v1"
STRUCTURE_ID = re.compile(r"^STR-[A-Z0-9][A-Z0-9-]{1,62}$")
DECISION_ID = re.compile(r"^[A-Z][A-Z0-9-]{2,63}$")
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
STATUSES = {"draft", "effective", "deprecated", "superseded", "revoked"}
ELEMENT_TYPES = {
    "component",
    "agent",
    "responsibility",
    "interface",
    "dependency",
    "control-gate",
    "workflow",
    "execution-entry-point",
    "evidence-obligation",
    "boundary",
}
ACTOR_TYPES = {"person", "team", "organisation", "agent", "system"}
GATE_MODES = {"blocking", "advisory"}
ARTIFACT_ROLES = {
    "architecture",
    "policy",
    "control",
    "workflow",
    "agent",
    "interface",
    "ownership",
    "implementation",
    "supporting",
}
EVIDENCE_TYPES = {"observation", "assessment", "approval", "execution", "outcome", "drift"}
EVIDENCE_RESULTS = {
    "observed",
    "passed",
    "failed",
    "warning",
    "inconclusive",
    "error",
    "succeeded",
    "not-applicable",
}
RECORD_KEYS = {
    "schema_version",
    "structure_id",
    "record_id",
    "record_version",
    "status",
    "title",
    "description",
    "scope",
    "intent_bindings",
    "actors",
    "elements",
    "gates",
    "entry_points",
    "evidence_requirements",
    "artifacts",
    "relationships",
    "lifecycle",
    "integrity",
}
MANIFEST_KEYS = {
    "schema_version",
    "manifest_id",
    "compiled_at",
    "scope",
    "intent_bindings",
    "structure_bindings",
    "entry_point",
    "elements",
    "gates",
    "evidence_requirements",
    "artifacts",
    "integrity",
}
ADRP_REQUIRED_KEYS = {
    "schema_version",
    "decision_id",
    "record_id",
    "record_version",
    "status",
    "title",
    "decision_statement",
    "context",
    "drivers",
    "alternatives",
    "selected_alternative",
    "rationale",
    "tradeoffs",
    "authority",
    "provenance",
    "lifecycle",
    "consequences",
    "implementation",
    "relationships",
    "autonomy",
    "gaps",
    "ratification",
}


class StructureError(RuntimeError):
    """Raised when an ASRP artifact violates the profile."""


def fail(condition: bool, message: str) -> None:
    if not condition:
        raise StructureError(message)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StructureError(f"file not found: {path}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StructureError(f"invalid UTF-8 JSON in {path}: {exc}") from exc
    fail(isinstance(value, dict), f"{path} must contain a JSON object")
    return value


def atomic_create(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError as exc:
        raise StructureError(f"refusing to overwrite immutable artifact: {path}") from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise


def exact_keys(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    fail(isinstance(value, dict), f"{label} must be an object")
    fail(set(value) == keys, f"{label} keys must be {sorted(keys)}")
    return value


def text(value: Any, label: str, *, nullable: bool = False) -> None:
    if nullable and value is None:
        return
    fail(isinstance(value, str) and bool(value.strip()), f"{label} must be non-empty text")


def text_list(value: Any, label: str) -> None:
    fail(isinstance(value, list), f"{label} must be an array")
    fail(all(isinstance(item, str) and item.strip() for item in value), f"{label} must contain text")
    fail(len(value) == len(set(value)), f"{label} must not contain duplicates")


def uuid_value(value: Any, label: str) -> None:
    try:
        uuid.UUID(value)
    except (ValueError, TypeError, AttributeError) as exc:
        raise StructureError(f"{label} must be a UUID") from exc


def timestamp(value: Any, label: str, *, nullable: bool = False) -> datetime | None:
    if nullable and value is None:
        return None
    text(value, label)
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise StructureError(f"{label} must be an ISO-8601 timestamp") from exc
    fail(moment.tzinfo is not None, f"{label} must include a timezone")
    return moment.astimezone(timezone.utc)


def digest_bytes(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def digest_file(path: Path) -> str:
    try:
        return digest_bytes(path.read_bytes())
    except FileNotFoundError as exc:
        raise StructureError(f"artifact not found: {path}") from exc


def canonical_payload(value: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(value)
    integrity = result.get("integrity")
    if isinstance(integrity, dict):
        if "record_fingerprint" in integrity:
            integrity["record_fingerprint"] = None
        if "manifest_fingerprint" in integrity:
            integrity["manifest_fingerprint"] = None
    return result


def canonical_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(
        canonical_payload(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def fingerprint(value: dict[str, Any]) -> str:
    return digest_bytes(canonical_bytes(value))


def adrp_payload(record: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(record)
    value.pop("ratification", None)
    return value


def adrp_fingerprint(record: dict[str, Any]) -> str:
    content = json.dumps(
        adrp_payload(record),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return digest_bytes(content)


def validate_intent_binding(value: Any, label: str) -> None:
    item = exact_keys(
        value,
        {"decision_id", "record_id", "record_version", "record_fingerprint"},
        label,
    )
    fail(isinstance(item["decision_id"], str) and DECISION_ID.fullmatch(item["decision_id"]), f"{label}.decision_id is invalid")
    uuid_value(item["record_id"], f"{label}.record_id")
    fail(isinstance(item["record_version"], int) and item["record_version"] >= 1, f"{label}.record_version is invalid")
    fail(isinstance(item["record_fingerprint"], str) and SHA256.fullmatch(item["record_fingerprint"]), f"{label}.record_fingerprint is invalid")


def intent_binding(path: Path) -> dict[str, Any]:
    record = read_json(path)
    fail(record.get("schema_version") == ADRP_SCHEMA_VERSION, f"{path} is not an ADRP v1 record")
    missing = ADRP_REQUIRED_KEYS - set(record)
    fail(not missing, f"{path} is missing ADRP fields: {sorted(missing)}")
    binding = {
        "decision_id": record["decision_id"],
        "record_id": record["record_id"],
        "record_version": record["record_version"],
        "record_fingerprint": adrp_fingerprint(record),
    }
    validate_intent_binding(binding, str(path))
    ratification = record.get("ratification")
    if isinstance(ratification, dict) and ratification.get("record_fingerprint"):
        fail(ratification["record_fingerprint"] == binding["record_fingerprint"], f"{path} ADRP fingerprint mismatch")
    return binding


def validate_artifact(value: Any, label: str) -> None:
    item = exact_keys(value, {"name", "path", "media_type", "digest", "role"}, label)
    text(item["name"], f"{label}.name")
    text(item["path"], f"{label}.path")
    artifact_path = Path(item["path"])
    fail(not artifact_path.is_absolute(), f"{label}.path must be relative")
    fail(".." not in artifact_path.parts, f"{label}.path must not escape the artifact root")
    text(item["media_type"], f"{label}.media_type")
    fail(isinstance(item["digest"], str) and SHA256.fullmatch(item["digest"]), f"{label}.digest is invalid")
    fail(item["role"] in ARTIFACT_ROLES, f"{label}.role is invalid")


def validate_record(record: dict[str, Any], *, check_fingerprint: bool = True) -> None:
    exact_keys(record, RECORD_KEYS, "record")
    fail(record["schema_version"] == RECORD_SCHEMA_VERSION, f"schema_version must be {RECORD_SCHEMA_VERSION}")
    fail(isinstance(record["structure_id"], str) and STRUCTURE_ID.fullmatch(record["structure_id"]), "structure_id is invalid")
    uuid_value(record["record_id"], "record_id")
    fail(isinstance(record["record_version"], int) and record["record_version"] >= 1, "record_version is invalid")
    fail(record["status"] in STATUSES, "status is invalid")
    text(record["title"], "title")
    text(record["description"], "description")
    text_list(record["scope"], "scope")

    fail(isinstance(record["intent_bindings"], list), "intent_bindings must be an array")
    for index, binding in enumerate(record["intent_bindings"]):
        validate_intent_binding(binding, f"intent_bindings[{index}]")
    intent_keys = [
        (item["decision_id"], item["record_id"], item["record_version"])
        for item in record["intent_bindings"]
    ]
    fail(len(intent_keys) == len(set(intent_keys)), "intent_bindings must not contain duplicates")

    fail(isinstance(record["actors"], list), "actors must be an array")
    actor_ids: set[str] = set()
    for index, actor in enumerate(record["actors"]):
        item = exact_keys(actor, {"actor_id", "actor_type", "name", "uri"}, f"actors[{index}]")
        text(item["actor_id"], f"actors[{index}].actor_id")
        fail(item["actor_id"] not in actor_ids, "actor_id values must be unique")
        actor_ids.add(item["actor_id"])
        fail(item["actor_type"] in ACTOR_TYPES, f"actors[{index}].actor_type is invalid")
        text(item["name"], f"actors[{index}].name")
        text(item["uri"], f"actors[{index}].uri", nullable=True)

    fail(isinstance(record["elements"], list), "elements must be an array")
    element_ids: set[str] = set()
    for index, element in enumerate(record["elements"]):
        item = exact_keys(
            element,
            {
                "element_id",
                "element_type",
                "name",
                "description",
                "owner_refs",
                "artifact_refs",
                "depends_on",
                "properties",
            },
            f"elements[{index}]",
        )
        text(item["element_id"], f"elements[{index}].element_id")
        fail(item["element_id"] not in element_ids, "element_id values must be unique")
        element_ids.add(item["element_id"])
        fail(item["element_type"] in ELEMENT_TYPES, f"elements[{index}].element_type is invalid")
        text(item["name"], f"elements[{index}].name")
        text(item["description"], f"elements[{index}].description")
        text_list(item["owner_refs"], f"elements[{index}].owner_refs")
        fail(set(item["owner_refs"]) <= actor_ids, f"elements[{index}] references unknown actor")
        text_list(item["artifact_refs"], f"elements[{index}].artifact_refs")
        text_list(item["depends_on"], f"elements[{index}].depends_on")
        fail(isinstance(item["properties"], dict), f"elements[{index}].properties must be an object")

    artifact_paths: set[str] = set()
    fail(isinstance(record["artifacts"], list), "artifacts must be an array")
    for index, artifact in enumerate(record["artifacts"]):
        validate_artifact(artifact, f"artifacts[{index}]")
        fail(artifact["path"] not in artifact_paths, "artifact paths must be unique")
        artifact_paths.add(artifact["path"])
    for index, element in enumerate(record["elements"]):
        fail(set(element["artifact_refs"]) <= artifact_paths, f"elements[{index}] references unknown artifact")
        fail(set(element["depends_on"]) <= element_ids, f"elements[{index}] references unknown element")

    fail(isinstance(record["gates"], list), "gates must be an array")
    gate_ids: set[str] = set()
    for index, gate in enumerate(record["gates"]):
        item = exact_keys(
            gate,
            {"gate_id", "name", "mode", "element_refs", "policy_refs"},
            f"gates[{index}]",
        )
        text(item["gate_id"], f"gates[{index}].gate_id")
        fail(item["gate_id"] not in gate_ids, "gate_id values must be unique")
        gate_ids.add(item["gate_id"])
        text(item["name"], f"gates[{index}].name")
        fail(item["mode"] in GATE_MODES, f"gates[{index}].mode is invalid")
        text_list(item["element_refs"], f"gates[{index}].element_refs")
        fail(set(item["element_refs"]) <= element_ids, f"gates[{index}] references unknown element")
        text_list(item["policy_refs"], f"gates[{index}].policy_refs")

    fail(isinstance(record["entry_points"], list), "entry_points must be an array")
    entry_ids: set[str] = set()
    for index, entry in enumerate(record["entry_points"]):
        item = exact_keys(
            entry,
            {"entry_point_id", "name", "runner", "command", "element_refs", "required_gates"},
            f"entry_points[{index}]",
        )
        text(item["entry_point_id"], f"entry_points[{index}].entry_point_id")
        fail(item["entry_point_id"] not in entry_ids, "entry_point_id values must be unique")
        entry_ids.add(item["entry_point_id"])
        text(item["name"], f"entry_points[{index}].name")
        text(item["runner"], f"entry_points[{index}].runner")
        text(item["command"], f"entry_points[{index}].command", nullable=True)
        text_list(item["element_refs"], f"entry_points[{index}].element_refs")
        fail(set(item["element_refs"]) <= element_ids, f"entry_points[{index}] references unknown element")
        text_list(item["required_gates"], f"entry_points[{index}].required_gates")
        fail(set(item["required_gates"]) <= gate_ids, f"entry_points[{index}] references unknown gate")

    fail(isinstance(record["evidence_requirements"], list), "evidence_requirements must be an array")
    requirement_ids: set[str] = set()
    for index, requirement in enumerate(record["evidence_requirements"]):
        item = exact_keys(
            requirement,
            {
                "requirement_id",
                "evidence_type",
                "subject",
                "required_results",
                "artifact_roles",
                "criteria_refs",
                "gate_refs",
            },
            f"evidence_requirements[{index}]",
        )
        text(item["requirement_id"], f"evidence_requirements[{index}].requirement_id")
        fail(item["requirement_id"] not in requirement_ids, "requirement_id values must be unique")
        requirement_ids.add(item["requirement_id"])
        fail(item["evidence_type"] in EVIDENCE_TYPES, f"evidence_requirements[{index}].evidence_type is invalid")
        text(item["subject"], f"evidence_requirements[{index}].subject")
        text_list(item["required_results"], f"evidence_requirements[{index}].required_results")
        fail(set(item["required_results"]) <= EVIDENCE_RESULTS, f"evidence_requirements[{index}] has invalid result")
        text_list(item["artifact_roles"], f"evidence_requirements[{index}].artifact_roles")
        text_list(item["criteria_refs"], f"evidence_requirements[{index}].criteria_refs")
        text_list(item["gate_refs"], f"evidence_requirements[{index}].gate_refs")
        fail(set(item["gate_refs"]) <= gate_ids, f"evidence_requirements[{index}] references unknown gate")

    relationships = exact_keys(record["relationships"], {"depends_on", "supersedes"}, "relationships")
    text_list(relationships["depends_on"], "relationships.depends_on")
    text_list(relationships["supersedes"], "relationships.supersedes")

    lifecycle = exact_keys(
        record["lifecycle"],
        {"effective_from", "review_by", "expires_at", "drift_triggers"},
        "lifecycle",
    )
    timestamp(lifecycle["effective_from"], "lifecycle.effective_from", nullable=True)
    timestamp(lifecycle["review_by"], "lifecycle.review_by", nullable=True)
    timestamp(lifecycle["expires_at"], "lifecycle.expires_at", nullable=True)
    text_list(lifecycle["drift_triggers"], "lifecycle.drift_triggers")

    integrity = exact_keys(record["integrity"], {"record_fingerprint"}, "integrity")
    stored = integrity["record_fingerprint"]
    fail(stored is None or (isinstance(stored, str) and SHA256.fullmatch(stored)), "integrity.record_fingerprint is invalid")
    if check_fingerprint and stored is not None:
        fail(stored == fingerprint(record), "record fingerprint mismatch")


def validate_manifest(manifest: dict[str, Any], *, check_fingerprint: bool = True) -> None:
    exact_keys(manifest, MANIFEST_KEYS, "manifest")
    fail(manifest["schema_version"] == MANIFEST_SCHEMA_VERSION, f"schema_version must be {MANIFEST_SCHEMA_VERSION}")
    uuid_value(manifest["manifest_id"], "manifest_id")
    timestamp(manifest["compiled_at"], "compiled_at")
    text(manifest["scope"], "scope")
    fail(isinstance(manifest["intent_bindings"], list), "intent_bindings must be an array")
    for index, item in enumerate(manifest["intent_bindings"]):
        validate_intent_binding(item, f"intent_bindings[{index}]")
    fail(isinstance(manifest["structure_bindings"], list) and manifest["structure_bindings"], "structure_bindings must be non-empty")
    for index, binding in enumerate(manifest["structure_bindings"]):
        item = exact_keys(binding, {"structure_id", "record_id", "record_version", "record_fingerprint"}, f"structure_bindings[{index}]")
        fail(isinstance(item["structure_id"], str) and STRUCTURE_ID.fullmatch(item["structure_id"]), f"structure_bindings[{index}].structure_id is invalid")
        uuid_value(item["record_id"], f"structure_bindings[{index}].record_id")
        fail(isinstance(item["record_version"], int) and item["record_version"] >= 1, f"structure_bindings[{index}].record_version is invalid")
        fail(isinstance(item["record_fingerprint"], str) and SHA256.fullmatch(item["record_fingerprint"]), f"structure_bindings[{index}].record_fingerprint is invalid")
    fail(isinstance(manifest["entry_point"], dict), "entry_point must be an object")
    fail(isinstance(manifest["elements"], list), "elements must be an array")
    fail(isinstance(manifest["gates"], list), "gates must be an array")
    fail(isinstance(manifest["evidence_requirements"], list), "evidence_requirements must be an array")
    fail(isinstance(manifest["artifacts"], list), "artifacts must be an array")
    integrity = exact_keys(manifest["integrity"], {"manifest_fingerprint"}, "integrity")
    stored = integrity["manifest_fingerprint"]
    fail(isinstance(stored, str) and SHA256.fullmatch(stored), "integrity.manifest_fingerprint is invalid")
    if check_fingerprint:
        fail(stored == fingerprint(manifest), "manifest fingerprint mismatch")


def discover(paths: list[str]) -> list[tuple[Path, dict[str, Any]]]:
    files: set[Path] = set()
    for raw in paths:
        path = Path(raw)
        if path.is_file():
            files.add(path.resolve())
        elif path.is_dir():
            files.update(item.resolve() for item in path.rglob("*.json"))
        else:
            raise StructureError(f"path not found: {path}")
    records: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(files):
        try:
            value = read_json(path)
        except StructureError:
            continue
        if value.get("schema_version") == RECORD_SCHEMA_VERSION:
            validate_record(value)
            records.append((path, value))
    return records


def normalise_scope(value: str) -> str:
    return " ".join(value.casefold().split())


def lifecycle_reasons(record: dict[str, Any], as_of: datetime) -> list[str]:
    reasons: list[str] = []
    if record["status"] != "effective":
        reasons.append(f"status is {record['status']}")
    effective = timestamp(record["lifecycle"]["effective_from"], "effective_from", nullable=True)
    expires = timestamp(record["lifecycle"]["expires_at"], "expires_at", nullable=True)
    if effective and as_of < effective:
        reasons.append("not yet effective")
    if expires and as_of >= expires:
        reasons.append("expired")
    return reasons


def resolve_records(paths: list[str], scope: str | None, as_of: datetime) -> dict[str, Any]:
    discovered = discover(paths)
    requested = normalise_scope(scope) if scope else None
    candidates: list[tuple[Path, dict[str, Any]]] = []
    excluded: list[dict[str, Any]] = []
    for path, record in discovered:
        reasons = lifecycle_reasons(record, as_of)
        scopes = {normalise_scope(item) for item in record["scope"]}
        if requested and requested not in scopes and "*" not in scopes:
            reasons.append("scope does not match")
        item = {
            "structure_id": record["structure_id"],
            "record_id": record["record_id"],
            "record_version": record["record_version"],
            "title": record["title"],
            "path": str(path),
            "record_fingerprint": fingerprint(record),
            "reasons": reasons,
        }
        if reasons:
            excluded.append(item)
        else:
            candidates.append((path, record))
    selected: dict[str, tuple[Path, dict[str, Any]]] = {}
    for path, record in candidates:
        current = selected.get(record["structure_id"])
        if current is None or record["record_version"] > current[1]["record_version"]:
            if current is not None:
                excluded.append(
                    {
                        "structure_id": current[1]["structure_id"],
                        "record_id": current[1]["record_id"],
                        "record_version": current[1]["record_version"],
                        "title": current[1]["title"],
                        "path": str(current[0]),
                        "record_fingerprint": fingerprint(current[1]),
                        "reasons": ["lower active version"],
                    }
                )
            selected[record["structure_id"]] = (path, record)
    superseded = {
        target: source["structure_id"]
        for _, source in selected.values()
        for target in source["relationships"]["supersedes"]
    }
    for target, source_id in superseded.items():
        if target in selected:
            path, record = selected.pop(target)
            excluded.append(
                {
                    "structure_id": record["structure_id"],
                    "record_id": record["record_id"],
                    "record_version": record["record_version"],
                    "title": record["title"],
                    "path": str(path),
                    "record_fingerprint": fingerprint(record),
                    "reasons": [f"superseded by {source_id}"],
                }
            )
    changed = True
    while changed:
        changed = False
        active_ids = set(selected)
        for structure_id, (path, record) in list(selected.items()):
            missing = sorted(set(record["relationships"]["depends_on"]) - active_ids)
            if missing:
                del selected[structure_id]
                excluded.append(
                    {
                        "structure_id": record["structure_id"],
                        "record_id": record["record_id"],
                        "record_version": record["record_version"],
                        "title": record["title"],
                        "path": str(path),
                        "record_fingerprint": fingerprint(record),
                        "reasons": [f"missing active dependency: {item}" for item in missing],
                    }
                )
                changed = True
    active = []
    for structure_id in sorted(selected):
        path, record = selected[structure_id]
        active.append(
            {
                "structure_id": record["structure_id"],
                "record_id": record["record_id"],
                "record_version": record["record_version"],
                "title": record["title"],
                "scope": record["scope"],
                "path": str(path),
                "record_fingerprint": fingerprint(record),
                "intent_bindings": record["intent_bindings"],
                "entry_points": record["entry_points"],
                "gates": record["gates"],
                "evidence_requirements": record["evidence_requirements"],
            }
        )
    return {
        "schema_version": "asrp-resolution/v1",
        "as_of": as_of.isoformat().replace("+00:00", "Z"),
        "requested_scope": scope,
        "active": active,
        "excluded": sorted(excluded, key=lambda item: (item["structure_id"], item["record_version"])),
        "summary": {"records": len(discovered), "active_records": len(active), "excluded_records": len(excluded)},
    }


def structure_binding(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "structure_id": record["structure_id"],
        "record_id": record["record_id"],
        "record_version": record["record_version"],
        "record_fingerprint": fingerprint(record),
    }


def command_bind_intent(args: argparse.Namespace) -> dict[str, Any]:
    record = read_json(Path(args.record))
    validate_record(record)
    binding = intent_binding(Path(args.decision))
    keys = {
        (item["decision_id"], item["record_id"], item["record_version"])
        for item in record["intent_bindings"]
    }
    key = (binding["decision_id"], binding["record_id"], binding["record_version"])
    fail(key not in keys, "record already contains this intent binding")
    record["intent_bindings"].append(binding)
    record["intent_bindings"].sort(key=lambda item: (item["decision_id"], item["record_version"], item["record_id"]))
    record["integrity"]["record_fingerprint"] = fingerprint(record)
    validate_record(record)
    atomic_create(Path(args.output), record)
    return {"created": args.output, "binding": binding, "fingerprint": fingerprint(record)}


def verify_artifacts(record: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for artifact in record["artifacts"]:
        candidate = root / artifact["path"]
        resolved = candidate.resolve(strict=False)
        within_root = resolved.is_relative_to(root)
        exists = within_root and resolved.is_file()
        actual = digest_file(resolved) if exists else None
        results.append(
            {
                "path": artifact["path"],
                "within_artifact_root": within_root,
                "exists": exists,
                "expected_digest": artifact["digest"],
                "actual_digest": actual,
                "valid": exists and actual == artifact["digest"],
            }
        )
    return results


def command_compile(args: argparse.Namespace) -> dict[str, Any]:
    as_of = timestamp(args.as_of, "as_of") if args.as_of else datetime.now(timezone.utc)
    assert as_of is not None
    resolution = resolve_records(args.paths, args.scope, as_of)
    fail(resolution["active"], "no active Structure records resolved")
    records = [read_json(Path(item["path"])) for item in resolution["active"]]
    entries = [
        (record, entry)
        for record in records
        for entry in record["entry_points"]
        if entry["entry_point_id"] == args.entry_point
    ]
    fail(entries, f"entry point not found: {args.entry_point}")
    fail(len(entries) == 1, f"entry point is ambiguous: {args.entry_point}")
    selected_record, entry = entries[0]
    element_ids = set(entry["element_refs"])
    pending = list(element_ids)
    element_map = {
        element["element_id"]: element
        for record in records
        for element in record["elements"]
    }
    while pending:
        current = pending.pop()
        fail(current in element_map, f"entry point references unresolved element: {current}")
        for dependency in element_map[current]["depends_on"]:
            if dependency not in element_ids:
                element_ids.add(dependency)
                pending.append(dependency)
    gate_ids = set(entry["required_gates"])
    gates = [
        gate
        for record in records
        for gate in record["gates"]
        if gate["gate_id"] in gate_ids
    ]
    fail(len(gates) == len(gate_ids), "entry point references unresolved gate")
    requirements = [
        requirement
        for record in records
        for requirement in record["evidence_requirements"]
        if not requirement["gate_refs"] or set(requirement["gate_refs"]) & gate_ids
    ]
    artifacts_by_path = {
        artifact["path"]: artifact
        for record in records
        for artifact in record["artifacts"]
    }
    selected_elements = [element_map[item] for item in sorted(element_ids)]
    selected_paths = {
        path
        for element in selected_elements
        for path in element["artifact_refs"]
    }
    selected_paths.update(
        policy
        for gate in gates
        for policy in gate["policy_refs"]
        if policy in artifacts_by_path
    )
    intent_bindings = {
        (item["decision_id"], item["record_id"], item["record_version"], item["record_fingerprint"]): item
        for record in records
        for item in record["intent_bindings"]
    }
    structure_bindings = [structure_binding(record) for record in records]
    base = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "manifest_id": str(uuid.UUID(int=0)),
        "compiled_at": as_of.isoformat().replace("+00:00", "Z"),
        "scope": args.scope,
        "intent_bindings": [intent_bindings[key] for key in sorted(intent_bindings)],
        "structure_bindings": sorted(structure_bindings, key=lambda item: item["structure_id"]),
        "entry_point": entry,
        "elements": selected_elements,
        "gates": sorted(gates, key=lambda item: item["gate_id"]),
        "evidence_requirements": sorted(requirements, key=lambda item: item["requirement_id"]),
        "artifacts": [artifacts_by_path[path] for path in sorted(selected_paths)],
        "integrity": {"manifest_fingerprint": "sha256:" + ("0" * 64)},
    }
    seed = fingerprint(base)
    base["manifest_id"] = str(uuid.uuid5(uuid.NAMESPACE_URL, seed))
    base["integrity"]["manifest_fingerprint"] = fingerprint(base)
    validate_manifest(base)
    atomic_create(Path(args.output), base)
    return {
        "created": args.output,
        "manifest_id": base["manifest_id"],
        "fingerprint": fingerprint(base),
        "structures": len(base["structure_bindings"]),
        "evidence_requirements": len(base["evidence_requirements"]),
    }


def command_graph(args: argparse.Namespace) -> dict[str, Any]:
    records = discover(args.paths)
    nodes = []
    edges = []
    for path, record in records:
        nodes.append(
            {
                "id": record["structure_id"],
                "type": "structure",
                "title": record["title"],
                "path": str(path),
                "fingerprint": fingerprint(record),
            }
        )
        for binding in record["intent_bindings"]:
            nodes.append({"id": binding["decision_id"], "type": "intent"})
            edges.append({"from": record["structure_id"], "to": binding["decision_id"], "type": "implements"})
        for dependency in record["relationships"]["depends_on"]:
            edges.append({"from": record["structure_id"], "to": dependency, "type": "depends_on"})
        for target in record["relationships"]["supersedes"]:
            edges.append({"from": record["structure_id"], "to": target, "type": "supersedes"})
    unique_nodes = {f"{item['type']}:{item['id']}": item for item in nodes}
    return {
        "schema_version": "asrp-graph/v1",
        "nodes": [unique_nodes[key] for key in sorted(unique_nodes)],
        "edges": sorted(edges, key=lambda item: (item["from"], item["type"], item["to"])),
    }


def inspect(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("schema_version") == RECORD_SCHEMA_VERSION:
        validate_record(value)
        return {
            "kind": "record",
            "structure_id": value["structure_id"],
            "record_id": value["record_id"],
            "record_version": value["record_version"],
            "status": value["status"],
            "scope": value["scope"],
            "intent_bindings": value["intent_bindings"],
            "elements": len(value["elements"]),
            "gates": value["gates"],
            "entry_points": value["entry_points"],
            "evidence_requirements": value["evidence_requirements"],
            "fingerprint": fingerprint(value),
        }
    if value.get("schema_version") == MANIFEST_SCHEMA_VERSION:
        validate_manifest(value)
        return {
            "kind": "manifest",
            "manifest_id": value["manifest_id"],
            "scope": value["scope"],
            "entry_point": value["entry_point"],
            "intent_bindings": value["intent_bindings"],
            "structure_bindings": value["structure_bindings"],
            "gates": value["gates"],
            "evidence_requirements": value["evidence_requirements"],
            "fingerprint": fingerprint(value),
        }
    raise StructureError(f"unsupported schema_version: {value.get('schema_version')!r}")


def emit(value: dict[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="asrp", description=__doc__)
    root.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    commands = root.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate")
    validate.add_argument("path")

    fingerprint_parser = commands.add_parser("fingerprint")
    fingerprint_parser.add_argument("path")

    inspect_parser = commands.add_parser("inspect")
    inspect_parser.add_argument("path")

    bind = commands.add_parser("bind-intent")
    bind.add_argument("record")
    bind.add_argument("decision")
    bind.add_argument("--output", required=True)

    verify = commands.add_parser("verify")
    verify.add_argument("record")
    verify.add_argument("--artifact-root", default=".")

    resolve = commands.add_parser("resolve")
    resolve.add_argument("paths", nargs="+")
    resolve.add_argument("--scope")
    resolve.add_argument("--as-of")

    graph = commands.add_parser("graph")
    graph.add_argument("paths", nargs="+")

    compile_parser = commands.add_parser("compile")
    compile_parser.add_argument("paths", nargs="+")
    compile_parser.add_argument("--scope", required=True)
    compile_parser.add_argument("--entry-point", required=True)
    compile_parser.add_argument("--as-of")
    compile_parser.add_argument("--output", required=True)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command in {"validate", "fingerprint", "inspect"}:
            value = read_json(Path(args.path))
            summary = inspect(value)
            if args.command == "validate":
                emit({"valid": True, "kind": summary["kind"], "fingerprint": fingerprint(value)})
            elif args.command == "fingerprint":
                print(fingerprint(value))
            else:
                emit(summary)
        elif args.command == "bind-intent":
            emit(command_bind_intent(args))
        elif args.command == "verify":
            record = read_json(Path(args.record))
            validate_record(record)
            results = verify_artifacts(record, Path(args.artifact_root).resolve())
            fail(all(item["valid"] for item in results), "artifact verification failed")
            emit({"valid": True, "artifacts": results})
        elif args.command == "resolve":
            as_of = timestamp(args.as_of, "as_of") if args.as_of else datetime.now(timezone.utc)
            assert as_of is not None
            emit(resolve_records(args.paths, args.scope, as_of))
        elif args.command == "graph":
            emit(command_graph(args))
        elif args.command == "compile":
            emit(command_compile(args))
        else:
            raise StructureError(f"unsupported command: {args.command}")
    except StructureError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
