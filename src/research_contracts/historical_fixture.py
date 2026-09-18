"""Small, local-only historical fixture pipeline.

This module deliberately handles a fixture manifest and one write-once
assessment file.  It is not an acquisition system, outcome join, or store.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any

from .top30 import (
    AssessmentPayload,
    HistoricalIdentityBundle,
    IdentityEvidence,
    IdentityResolution,
    IdentityStatus,
    InformationBoundary,
    Top30Observation,
    Provenance,
)


MANIFEST_SCHEMA_VERSION = "historical-fixture-manifest-1"
FROZEN_ASSESSMENT_SCHEMA_VERSION = "frozen-assessment-1"
FIXTURE_PARSER_VERSION = "job-0007-delimited-top30-1"


def _utc(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return _utc(value, "datetime").isoformat(timespec="microseconds").replace("+00:00", "Z")


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


class AvailabilityState(StrEnum):
    KNOWN = "known"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class FixtureManifestEntry:
    fixture_id: str
    raw_path: str
    byte_length: int
    content_sha256: str
    provenance: str
    source_timestamp: datetime | None
    ingested_at: datetime
    availability_state: AvailabilityState
    available_at: datetime | None
    artifact_type: str
    parser_version: str

    def __post_init__(self) -> None:
        if not self.fixture_id or not self.raw_path or not self.provenance or not self.artifact_type:
            raise ValueError("fixture identity, path, provenance, and artifact type are required")
        if self.byte_length < 0 or len(self.content_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.content_sha256):
            raise ValueError("fixture byte length and lowercase SHA-256 digest are required")
        if not isinstance(self.availability_state, AvailabilityState):
            object.__setattr__(self, "availability_state", AvailabilityState(self.availability_state))
        if self.source_timestamp is not None:
            object.__setattr__(self, "source_timestamp", _utc(self.source_timestamp, "source_timestamp"))
        object.__setattr__(self, "ingested_at", _utc(self.ingested_at, "ingested_at"))
        if self.availability_state is AvailabilityState.KNOWN:
            if self.available_at is None:
                raise ValueError("known availability requires available_at")
            object.__setattr__(self, "available_at", _utc(self.available_at, "available_at"))
        elif self.available_at is not None:
            raise ValueError("unknown availability must not invent available_at")

    def to_dict(self) -> dict[str, Any]:
        return {
            "fixture_id": self.fixture_id, "raw_path": self.raw_path,
            "byte_length": self.byte_length, "content_sha256": self.content_sha256,
            "provenance": self.provenance,
            "source_timestamp": _iso(self.source_timestamp) if self.source_timestamp else None,
            "ingested_at": _iso(self.ingested_at),
            "availability_state": self.availability_state.value,
            "available_at": _iso(self.available_at) if self.available_at else None,
            "artifact_type": self.artifact_type, "parser_version": self.parser_version,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "FixtureManifestEntry":
        return cls(value["fixture_id"], value["raw_path"], value["byte_length"],
                   value["content_sha256"], value["provenance"],
                   _parse_datetime(value["source_timestamp"]) if value.get("source_timestamp") else None,
                   _parse_datetime(value["ingested_at"]), value["availability_state"],
                   _parse_datetime(value["available_at"]) if value.get("available_at") else None,
                   value["artifact_type"], value["parser_version"])


@dataclass(frozen=True)
class FixtureManifest:
    fixtures: tuple[FixtureManifestEntry, ...]
    schema_version: str = MANIFEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != MANIFEST_SCHEMA_VERSION or not self.fixtures:
            raise ValueError("unsupported or empty fixture manifest")
        if len({item.fixture_id for item in self.fixtures}) != len(self.fixtures):
            raise ValueError("fixture IDs must be unique")

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": self.schema_version,
                "fixtures": [item.to_dict() for item in sorted(self.fixtures, key=lambda item: item.fixture_id)]}

    def to_json(self) -> str:
        return _canonical_json(self.to_dict())

    @property
    def content_digest(self) -> str:
        return _digest(self.to_dict())

    @classmethod
    def from_json(cls, value: str) -> "FixtureManifest":
        data = json.loads(value)
        return cls(tuple(FixtureManifestEntry.from_dict(item) for item in data["fixtures"]), data["schema_version"])

    def validate_bytes(self, root: Path) -> None:
        root = root.resolve()
        for item in self.fixtures:
            path = (root / item.raw_path).resolve()
            if root not in path.parents:
                raise ValueError("fixture raw_path escapes manifest root")
            raw = path.read_bytes()
            if len(raw) != item.byte_length or hashlib.sha256(raw).hexdigest() != item.content_sha256:
                raise ValueError(f"fixture bytes do not match manifest: {item.fixture_id}")

    def entry(self, fixture_id: str) -> FixtureManifestEntry:
        for item in self.fixtures:
            if item.fixture_id == fixture_id:
                return item
        raise KeyError(fixture_id)


def parse_top30_fixture(manifest: FixtureManifest, root: Path, fixture_id: str) -> tuple[Top30Observation, ...]:
    """Parse the deliberately narrow ``rank|name|code-or-empty|detail`` format."""
    manifest.validate_bytes(root)
    entry = manifest.entry(fixture_id)
    if entry.parser_version != FIXTURE_PARSER_VERSION:
        raise ValueError("unsupported fixture parser version")
    if entry.availability_state is not AvailabilityState.KNOWN or entry.available_at is None:
        raise ValueError("fixture availability is unknown; it cannot enter an assessment")
    lines = (root / entry.raw_path).read_text(encoding="utf-8").splitlines()
    if not lines or not lines[0].startswith("observation_date="):
        raise ValueError("fixture header must state observation_date")
    observation_date = date.fromisoformat(lines[0].split("=", 1)[1])
    source = Provenance("local_historical_fixture", entry.fixture_id, entry.raw_path,
                        entry.content_sha256, entry.available_at, InformationBoundary.POINT_IN_TIME)
    observations: list[Top30Observation] = []
    for line in lines[1:]:
        if not line:
            continue
        parts = line.split("|", 3)
        if len(parts) != 4:
            raise ValueError("fixture row must have four pipe-delimited fields")
        rank_text, name, code, detail = parts
        if not name:
            raise ValueError("fixture row name is required")
        if code:
            evidence = IdentityEvidence(source, entry.source_timestamp, observation_date,
                                        "code embedded in immutable fixture row")
            resolution = IdentityResolution(IdentityStatus.POINT_IN_TIME_VERIFIED, code, evidence,
                                            "fixture_embedded_code")
        else:
            resolution = IdentityResolution(IdentityStatus.UNRESOLVED,
                                            resolution_method="no_cutoff_visible_identity_evidence")
        bundle = HistoricalIdentityBundle(name, resolution)
        mapping = bundle.assessment_mapping(entry.available_at)
        observations.append(Top30Observation(observation_date, entry.available_at, int(rank_text), name,
                                              source, entry.parser_version, entry.ingested_at, mapping,
                                              detail_raw=detail, identity=bundle))
    if not observations:
        raise ValueError("fixture contains no observations")
    return tuple(observations)


@dataclass(frozen=True)
class FrozenAssessment:
    assessment_id: str
    fixture_manifest_digest: str
    cutoff_at: datetime
    payloads: tuple[AssessmentPayload, ...]
    contract_version: str
    created_at: datetime
    schema_version: str = FROZEN_ASSESSMENT_SCHEMA_VERSION
    content_digest: str = ""

    def __post_init__(self) -> None:
        if not self.assessment_id or len(self.fixture_manifest_digest) != 64 or not self.payloads:
            raise ValueError("assessment ID, manifest digest, and payloads are required")
        if self.schema_version != FROZEN_ASSESSMENT_SCHEMA_VERSION:
            raise ValueError("unsupported frozen assessment schema")
        cutoff = _utc(self.cutoff_at, "cutoff_at")
        created = _utc(self.created_at, "created_at")
        if any(payload.cutoff_at != cutoff for payload in self.payloads):
            raise ValueError("all frozen payloads must use the assessment cutoff")
        object.__setattr__(self, "cutoff_at", cutoff)
        object.__setattr__(self, "created_at", created)
        computed = _digest(self._content_dict())
        if self.content_digest and self.content_digest != computed:
            raise ValueError("frozen assessment content digest does not match")
        object.__setattr__(self, "content_digest", computed)

    def _content_dict(self) -> dict[str, Any]:
        return {"assessment_id": self.assessment_id, "fixture_manifest_digest": self.fixture_manifest_digest,
                "cutoff_at": _iso(self.cutoff_at), "payloads": [item.to_dict() for item in self.payloads],
                "contract_version": self.contract_version, "created_at": _iso(self.created_at),
                "schema_version": self.schema_version}

    def to_dict(self) -> dict[str, Any]:
        return {**self._content_dict(), "content_digest": self.content_digest}

    def to_json(self) -> str:
        return _canonical_json(self.to_dict())

    @classmethod
    def from_json(cls, value: str) -> "FrozenAssessment":
        data = json.loads(value)
        return cls(data["assessment_id"], data["fixture_manifest_digest"], _parse_datetime(data["cutoff_at"]),
                   tuple(AssessmentPayload.from_dict(item) for item in data["payloads"]), data["contract_version"],
                   _parse_datetime(data["created_at"]), data["schema_version"], data["content_digest"])


def build_frozen_assessment(manifest: FixtureManifest, observations: tuple[Top30Observation, ...],
                            assessment_id: str, created_at: datetime) -> FrozenAssessment:
    cutoff = observations[0].cutoff_at
    if any(item.cutoff_at != cutoff for item in observations):
        raise ValueError("fixture observations must share one cutoff")
    payloads = tuple(AssessmentPayload.from_observation(item, cutoff) for item in observations)
    return FrozenAssessment(assessment_id, manifest.content_digest, cutoff, payloads,
                            "top30-assessment-payload-1", created_at)


def write_frozen_assessment(path: Path, assessment: FrozenAssessment) -> bool:
    """Write once; return False for byte-identical idempotent re-freezes."""
    content = assessment.to_json() + "\n"
    if path.exists():
        if path.read_bytes() == content.encode("utf-8"):
            return False
        raise FileExistsError(f"refusing to overwrite frozen assessment: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents a normal concurrent writer from replacing an artifact.
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
    except FileExistsError:
        if path.read_bytes() == content.encode("utf-8"):
            return False
        raise FileExistsError(f"refusing to overwrite frozen assessment: {path}")
    return True
