"""Point-in-time boundary between historical Top30 parsing and research."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any


class InformationBoundary(StrEnum):
    POINT_IN_TIME = "point_in_time"
    RETROSPECTIVE = "retrospective"


def _utc(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return _utc(value, "datetime").isoformat(timespec="microseconds").replace("+00:00", "Z")


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass(frozen=True)
class Provenance:
    """Identity of an immutable source artifact and when it became available."""

    source_kind: str
    source_id: str
    raw_reference: str
    content_sha256: str
    available_at: datetime
    boundary: InformationBoundary

    def __post_init__(self) -> None:
        if not self.source_kind or not self.source_id or not self.raw_reference:
            raise ValueError("source_kind, source_id, and raw_reference are required")
        if not re.fullmatch(r"[0-9a-f]{64}", self.content_sha256):
            raise ValueError("content_sha256 must be a lowercase SHA-256 digest")
        if not isinstance(self.boundary, InformationBoundary):
            object.__setattr__(self, "boundary", InformationBoundary(self.boundary))
        object.__setattr__(self, "available_at", _utc(self.available_at, "available_at"))

    def to_dict(self) -> dict[str, Any]:
        return {"source_kind": self.source_kind, "source_id": self.source_id,
                "raw_reference": self.raw_reference, "content_sha256": self.content_sha256,
                "available_at": _iso(self.available_at), "boundary": self.boundary.value}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Provenance":
        data = dict(value)
        if "boundary" not in data:
            raise ValueError("provenance boundary is required")
        data["available_at"] = _parse_datetime(data["available_at"])
        return cls(**data)


@dataclass(frozen=True)
class MappingState:
    """Code identity, only when supported by evidence visible at the cutoff."""

    status: str
    stock_code: str | None = None
    evidence: Provenance | None = None
    resolution_method: str = "unresolved"
    evidence_published_at: datetime | None = None
    effective_date: date | None = None

    def __post_init__(self) -> None:
        if self.status not in {"unresolved", "point_in_time_confirmed"}:
            raise ValueError("mapping status must be unresolved or point_in_time_confirmed")
        if self.status == "unresolved" and self.stock_code is not None:
            raise ValueError("unresolved mapping cannot contain a stock code")
        if self.status == "point_in_time_confirmed" and (not self.stock_code or self.evidence is None):
            raise ValueError("confirmed mapping requires stock_code and evidence")
        if self.stock_code is not None and not re.fullmatch(r"[0-9]{6}", self.stock_code):
            raise ValueError("stock_code must be six ASCII digits")
        if self.evidence and self.evidence.boundary != InformationBoundary.POINT_IN_TIME:
            raise ValueError("mapping evidence must be point-in-time")
        if not self.resolution_method:
            raise ValueError("mapping resolution_method is required")
        if self.status == "point_in_time_confirmed" and self.resolution_method == "unresolved":
            raise ValueError("confirmed mapping requires an explicit resolution method")
        if self.evidence_published_at is not None:
            published = _utc(self.evidence_published_at, "evidence_published_at")
            if self.evidence is None:
                raise ValueError("evidence_published_at requires evidence")
            if published > self.evidence.available_at:
                raise ValueError("evidence publication cannot be after availability")
            object.__setattr__(self, "evidence_published_at", published)

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status, "stock_code": self.stock_code,
                "evidence": self.evidence.to_dict() if self.evidence else None,
                "resolution_method": self.resolution_method,
                "evidence_published_at": (_iso(self.evidence_published_at)
                                          if self.evidence_published_at else None),
                "effective_date": self.effective_date.isoformat() if self.effective_date else None}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "MappingState":
        evidence = value.get("evidence")
        return cls(
            value["status"], value.get("stock_code"),
            Provenance.from_dict(evidence) if evidence else None,
            value.get("resolution_method", "unresolved"),
            _parse_datetime(value["evidence_published_at"])
            if value.get("evidence_published_at") else None,
            date.fromisoformat(value["effective_date"])
            if value.get("effective_date") else None,
        )


class IdentityStatus(StrEnum):
    """How a name/code assertion is classified before cutoff selection."""

    SOURCE_OBSERVED = "source_observed"
    POINT_IN_TIME_VERIFIED = "point_in_time_verified"
    UNRESOLVED = "unresolved"
    RETROSPECTIVE_ENRICHMENT = "retrospective_enrichment"


@dataclass(frozen=True)
class IdentityEvidence:
    """One immutable identity assertion, retaining publication and effective dates."""

    source: Provenance
    published_at: datetime | None = None
    effective_date: date | None = None
    reference: str = ""

    def __post_init__(self) -> None:
        if self.published_at is not None:
            published = _utc(self.published_at, "published_at")
            if published > self.source.available_at:
                raise ValueError("identity evidence publication cannot be after availability")
            object.__setattr__(self, "published_at", published)

    @property
    def available_at(self) -> datetime:
        return self.source.available_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source.to_dict(),
            "published_at": _iso(self.published_at) if self.published_at else None,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "reference": self.reference,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "IdentityEvidence":
        return cls(
            Provenance.from_dict(value["source"]),
            _parse_datetime(value["published_at"]) if value.get("published_at") else None,
            date.fromisoformat(value["effective_date"]) if value.get("effective_date") else None,
            value.get("reference", ""),
        )


@dataclass(frozen=True)
class IdentityResolution:
    """An observed, verified, unresolved, or retrospective identity assertion."""

    status: IdentityStatus
    stock_code: str | None = None
    evidence: IdentityEvidence | None = None
    resolution_method: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.status, IdentityStatus):
            object.__setattr__(self, "status", IdentityStatus(self.status))
        if self.status is IdentityStatus.POINT_IN_TIME_VERIFIED:
            if not self.stock_code or self.evidence is None:
                raise ValueError("verified identity requires stock_code and evidence")
            if self.evidence.source.boundary is not InformationBoundary.POINT_IN_TIME:
                raise ValueError("verified identity evidence must be point-in-time")
        elif self.status is IdentityStatus.RETROSPECTIVE_ENRICHMENT:
            if not self.stock_code or self.evidence is None:
                raise ValueError("retrospective identity requires stock_code and evidence")
            if self.evidence.source.boundary is not InformationBoundary.RETROSPECTIVE:
                raise ValueError("retrospective identity evidence must be retrospective")
        elif self.stock_code is not None:
            raise ValueError("observed or unresolved identity cannot contain a stock code")
        if not self.resolution_method:
            raise ValueError("identity resolution_method is required")
        if self.stock_code is not None and not re.fullmatch(r"[0-9]{6}", self.stock_code):
            raise ValueError("stock_code must be six ASCII digits")

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status.value, "stock_code": self.stock_code,
                "evidence": self.evidence.to_dict() if self.evidence else None,
                "resolution_method": self.resolution_method}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "IdentityResolution":
        evidence = value.get("evidence")
        return cls(value["status"], value.get("stock_code"),
                   IdentityEvidence.from_dict(evidence) if evidence else None,
                   value["resolution_method"])


@dataclass(frozen=True)
class HistoricalIdentityBundle:
    """Identity candidates for one observed name; only cutoff-visible evidence is assessed."""

    observed_stock_name: str
    resolution: IdentityResolution
    retrospective: tuple[IdentityResolution, ...] = ()

    def __post_init__(self) -> None:
        if not self.observed_stock_name:
            raise ValueError("observed_stock_name is required")
        if self.resolution.status is IdentityStatus.RETROSPECTIVE_ENRICHMENT:
            raise ValueError("primary resolution cannot be a retrospective enrichment")
        if any(item.status is not IdentityStatus.RETROSPECTIVE_ENRICHMENT for item in self.retrospective):
            raise ValueError("retrospective bundle entries must be retrospective enrichments")

    def assessment_mapping(self, cutoff_at: datetime) -> MappingState:
        cutoff = _utc(cutoff_at, "cutoff_at")
        item = self.resolution
        if (item.status is IdentityStatus.POINT_IN_TIME_VERIFIED
                and item.evidence is not None and item.evidence.available_at <= cutoff):
            return MappingState("point_in_time_confirmed", item.stock_code, item.evidence.source,
                                item.resolution_method, item.evidence.published_at,
                                item.evidence.effective_date)
        method = ("evidence_after_cutoff" if item.status is IdentityStatus.POINT_IN_TIME_VERIFIED
                  else item.resolution_method)
        return MappingState("unresolved", resolution_method=method)

    def to_dict(self) -> dict[str, Any]:
        return {"observed_stock_name": self.observed_stock_name,
                "resolution": self.resolution.to_dict(),
                "retrospective": [item.to_dict() for item in self.retrospective]}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "HistoricalIdentityBundle":
        return cls(value["observed_stock_name"], IdentityResolution.from_dict(value["resolution"]),
                   tuple(IdentityResolution.from_dict(item) for item in value.get("retrospective", [])))


@dataclass(frozen=True)
class RetrospectiveEnrichment:
    """Later information retained for audit, never part of the base assessment."""

    field_name: str
    value: str
    source: Provenance
    reason: str

    def __post_init__(self) -> None:
        if not self.field_name or not self.reason:
            raise ValueError("retrospective enrichment requires field_name and reason")
        if self.source.boundary != InformationBoundary.RETROSPECTIVE:
            raise ValueError("enrichment source must be marked retrospective")

    def to_dict(self) -> dict[str, Any]:
        return {"field_name": self.field_name, "value": self.value,
                "source": self.source.to_dict(), "reason": self.reason}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RetrospectiveEnrichment":
        return cls(value["field_name"], value["value"], Provenance.from_dict(value["source"]), value["reason"])


@dataclass(frozen=True)
class Top30Observation:
    observation_date: date
    cutoff_at: datetime
    rank: int | None
    stock_name: str
    source: Provenance
    parser_version: str
    ingested_at: datetime
    mapping: MappingState
    return_pct: Decimal | None = None
    detail_raw: str = ""
    enrichments: tuple[RetrospectiveEnrichment, ...] = ()
    identity: HistoricalIdentityBundle | None = None

    def __post_init__(self) -> None:
        cutoff = _utc(self.cutoff_at, "cutoff_at")
        ingested = _utc(self.ingested_at, "ingested_at")
        if not self.stock_name:
            raise ValueError("stock_name must preserve the non-empty source value")
        if self.rank is not None and not 1 <= self.rank <= 30:
            raise ValueError("rank must be between 1 and 30")
        if self.source.boundary is not InformationBoundary.POINT_IN_TIME:
            raise ValueError("observation source must be point-in-time")
        if self.source.available_at > cutoff:
            raise ValueError("source became available after cutoff_at")
        if self.mapping.evidence and self.mapping.evidence.available_at > cutoff:
            raise ValueError("mapping evidence became available after cutoff_at")
        if self.mapping.status == "point_in_time_confirmed" and self.identity is None:
            raise ValueError("confirmed mapping requires a historical identity bundle")
        if self.identity is not None:
            if self.identity.observed_stock_name != self.stock_name:
                raise ValueError("identity bundle name must equal the source-observed stock_name")
            expected_mapping = self.identity.assessment_mapping(cutoff)
            if self.mapping != expected_mapping:
                raise ValueError("mapping must equal the identity bundle's cutoff-visible result")
        if ingested < cutoff:
            raise ValueError("ingested_at cannot precede cutoff_at")
        if any(item.source.available_at <= cutoff for item in self.enrichments):
            raise ValueError("enrichment source must be retrospective to the cutoff")
        object.__setattr__(self, "cutoff_at", cutoff)
        object.__setattr__(self, "ingested_at", ingested)
        if self.return_pct is not None and not isinstance(self.return_pct, Decimal):
            object.__setattr__(self, "return_pct", Decimal(str(self.return_pct)))

    def with_enrichment(self, enrichment: RetrospectiveEnrichment) -> "Top30Observation":
        if enrichment.source.available_at <= self.cutoff_at:
            raise ValueError("enrichment source must be retrospective to the cutoff")
        return Top30Observation(
            self.observation_date, self.cutoff_at, self.rank, self.stock_name, self.source,
            self.parser_version, self.ingested_at, self.mapping, self.return_pct,
            self.detail_raw, self.enrichments + (enrichment,), self.identity,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_date": self.observation_date.isoformat(),
            "cutoff_at": _iso(self.cutoff_at), "rank": self.rank,
            "stock_name": self.stock_name, "source": self.source.to_dict(),
            "parser_version": self.parser_version, "ingested_at": _iso(self.ingested_at),
            "mapping": self.mapping.to_dict(),
            "return_pct": None if self.return_pct is None else str(self.return_pct),
            "detail_raw": self.detail_raw,
            "enrichments": [item.to_dict() for item in self.enrichments],
            "identity": self.identity.to_dict() if self.identity else None,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Top30Observation":
        return cls(
            date.fromisoformat(value["observation_date"]), _parse_datetime(value["cutoff_at"]),
            value["rank"], value["stock_name"], Provenance.from_dict(value["source"]),
            value["parser_version"], _parse_datetime(value["ingested_at"]),
            MappingState.from_dict(value["mapping"]),
            Decimal(value["return_pct"]) if value.get("return_pct") is not None else None,
            value.get("detail_raw", ""),
            tuple(RetrospectiveEnrichment.from_dict(item) for item in value.get("enrichments", [])),
            HistoricalIdentityBundle.from_dict(value["identity"]) if value.get("identity") else None,
        )

    @classmethod
    def from_json(cls, value: str) -> "Top30Observation":
        return cls.from_dict(json.loads(value))


@dataclass(frozen=True)
class AssessmentPayload:
    """Cutoff-visible projection; retrospective enrichments are intentionally absent."""

    observation_date: date
    cutoff_at: datetime
    rank: int | None
    stock_name: str
    stock_code: str | None
    source: Provenance
    parser_version: str
    mapping_status: str
    return_pct: Decimal | None
    boundary: InformationBoundary = InformationBoundary.POINT_IN_TIME
    identity: MappingState | None = None

    def __post_init__(self) -> None:
        cutoff = _utc(self.cutoff_at, "cutoff_at")
        if not isinstance(self.boundary, InformationBoundary):
            object.__setattr__(self, "boundary", InformationBoundary(self.boundary))
        if self.boundary is not InformationBoundary.POINT_IN_TIME:
            raise ValueError("assessment boundary must be point-in-time")
        if not self.stock_name:
            raise ValueError("stock_name must preserve the non-empty source value")
        if not self.parser_version:
            raise ValueError("parser_version is required")
        if self.rank is not None and not 1 <= self.rank <= 30:
            raise ValueError("rank must be between 1 and 30")
        if self.source.boundary is not InformationBoundary.POINT_IN_TIME:
            raise ValueError("assessment source must be point-in-time")
        if self.source.available_at > cutoff:
            raise ValueError("assessment source became available after cutoff_at")
        if self.identity is None:
            raise ValueError("assessment requires its cutoff-selected identity state")
        if self.mapping_status != self.identity.status:
            raise ValueError("mapping_status must equal identity status")
        if self.stock_code != self.identity.stock_code:
            raise ValueError("stock_code must equal identity stock_code")
        if self.identity.evidence and self.identity.evidence.available_at > cutoff:
            raise ValueError("assessment identity evidence became available after cutoff_at")
        object.__setattr__(self, "cutoff_at", cutoff)
        if self.return_pct is not None and not isinstance(self.return_pct, Decimal):
            object.__setattr__(self, "return_pct", Decimal(str(self.return_pct)))

    @classmethod
    def from_observation(cls, observation: Top30Observation, cutoff_at: datetime) -> "AssessmentPayload":
        cutoff = _utc(cutoff_at, "cutoff_at")
        if observation.cutoff_at > cutoff:
            raise ValueError("observation is not visible at requested cutoff")
        return cls(observation.observation_date, observation.cutoff_at, observation.rank,
                   observation.stock_name, observation.mapping.stock_code, observation.source,
                   observation.parser_version, observation.mapping.status, observation.return_pct,
                   InformationBoundary.POINT_IN_TIME, observation.mapping)

    def to_dict(self) -> dict[str, Any]:
        return {"observation_date": self.observation_date.isoformat(), "cutoff_at": _iso(self.cutoff_at),
                "rank": self.rank, "stock_name": self.stock_name, "stock_code": self.stock_code,
                "source": self.source.to_dict(), "parser_version": self.parser_version,
                "mapping_status": self.mapping_status,
                "return_pct": None if self.return_pct is None else str(self.return_pct),
                "boundary": self.boundary.value,
                "identity": self.identity.to_dict() if self.identity else None}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AssessmentPayload":
        identity = value.get("identity")
        return cls(
            date.fromisoformat(value["observation_date"]),
            _parse_datetime(value["cutoff_at"]),
            value["rank"],
            value["stock_name"],
            value.get("stock_code"),
            Provenance.from_dict(value["source"]),
            value["parser_version"],
            value["mapping_status"],
            Decimal(value["return_pct"]) if value.get("return_pct") is not None else None,
            value["boundary"],
            MappingState.from_dict(identity) if identity else None,
        )

    @classmethod
    def from_json(cls, value: str) -> "AssessmentPayload":
        return cls.from_dict(json.loads(value))
