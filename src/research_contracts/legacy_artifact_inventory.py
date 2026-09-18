"""Minimal, read-only inventory model for external legacy artifacts.

This model records a current audit of an artifact without upgrading a newly
computed digest or locally preserved path into historical availability proof.
It deliberately contains no writer for a legacy source tree.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PureWindowsPath


class PointInTimeClassification(StrEnum):
    CUTOFF_VERIFIED = "CUTOFF_VERIFIED"
    SOURCE_VERIFIED_CONTENT_UNCERTAIN = "SOURCE_VERIFIED_CONTENT_UNCERTAIN"
    LOCALLY_PRESERVED_PROVENANCE_LIMITED = "LOCALLY_PRESERVED_PROVENANCE_LIMITED"
    RETROSPECTIVE_ONLY = "RETROSPECTIVE_ONLY"
    INVALID_OR_INCONSISTENT = "INVALID_OR_INCONSISTENT"


def is_legacy_source_path(path: str, roots: tuple[str, ...]) -> bool:
    """Return whether *path* is contained by an explicitly read-only root."""
    candidate = PureWindowsPath(path)
    return any(candidate.is_relative_to(PureWindowsPath(root)) for root in roots)


@dataclass(frozen=True)
class LegacyArtifactAudit:
    """A compact provenance record whose digest semantics stay explicit."""

    source_path: str
    byte_length: int
    current_audit_sha256: str
    stored_digest: str | None
    stored_digest_matches_current: bool | None
    historical_digest_available: bool
    availability_state: str
    point_in_time_classification: PointInTimeClassification
    source_access: str = "read_only"

    def __post_init__(self) -> None:
        if self.source_access != "read_only":
            raise ValueError("legacy source paths must be read_only")
        if self.byte_length < 0 or not _is_sha256(self.current_audit_sha256):
            raise ValueError("current audit byte length and SHA-256 are required")
        if self.stored_digest is not None and not _is_sha256(self.stored_digest):
            raise ValueError("stored digest must be a SHA-256 when present")
        if self.historical_digest_available and self.stored_digest is None:
            raise ValueError("historical digest availability requires a stored digest")
        if self.availability_state not in {"verified", "plausible_but_unverified", "unknown", "contradicted"}:
            raise ValueError("availability state must be explicit")
        if not isinstance(self.point_in_time_classification, PointInTimeClassification):
            object.__setattr__(self, "point_in_time_classification", PointInTimeClassification(self.point_in_time_classification))

    def to_dict(self) -> dict[str, object]:
        return {
            "source_path": self.source_path,
            "source_access": self.source_access,
            "byte_length": self.byte_length,
            "current_audit_sha256": self.current_audit_sha256,
            "current_audit_digest_kind": "CURRENT_AUDIT_DIGEST",
            "stored_digest": self.stored_digest,
            "stored_digest_matches_current": self.stored_digest_matches_current,
            "historical_digest_available": self.historical_digest_available,
            "availability_state": self.availability_state,
            "point_in_time_classification": self.point_in_time_classification.value,
        }


def audit_current_bytes(path: Path, *, stored_digest: str | None, availability_state: str,
                        classification: PointInTimeClassification) -> LegacyArtifactAudit:
    """Read bytes only and label their digest as a current audit digest."""
    import hashlib

    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    return LegacyArtifactAudit(
        str(path), len(data), digest, stored_digest,
        digest == stored_digest if stored_digest is not None else None,
        False, availability_state, classification,
    )


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)
