"""Contracts for repairing one legacy Telegram artifact's provenance.

The adapter using these contracts may read an explicitly allowlisted legacy
artifact and hash an original session for mutation detection.  It must give a
Telegram client only a Git-ignored working copy of that session.  Current
audit and retrieval digests are deliberately distinct from acquisition-time
historical evidence.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable


REPAIR_SCHEMA_VERSION = "job-0010-telegram-provenance-repair-1"
FIXTURE_REFERENCE_SCHEMA_VERSION = "job-0010-external-fixture-reference-1"


def _utc(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _utc(value, "datetime").isoformat(timespec="microseconds").replace("+00:00", "Z")


def _canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class AuthorizationStatus(StrEnum):
    AUTHORIZED = "AUTHORIZED"
    AUTHORIZATION_BLOCKED = "AUTHORIZATION_BLOCKED"
    CONNECTION_FAILED = "CONNECTION_FAILED"


class EditTimestampStatus(StrEnum):
    PRESENT = "PRESENT"
    NONE_REPORTED_BY_CURRENT_API = "NONE_REPORTED_BY_CURRENT_API"
    UNKNOWN_NOT_RETRIEVED = "UNKNOWN_NOT_RETRIEVED"


class ComparisonResult(StrEnum):
    EXACT_MATCH = "EXACT_MATCH"
    CANONICAL_MATCH = "CANONICAL_MATCH"
    MISMATCH = "MISMATCH"
    COMPARISON_IMPOSSIBLE = "COMPARISON_IMPOSSIBLE"


class EvidenceClassification(StrEnum):
    A_CUTOFF_VERIFIED = "A_CUTOFF_VERIFIED"
    B_SOURCE_VERIFIED_CONTENT_STRONGLY_SUPPORTED = "B_SOURCE_VERIFIED_CONTENT_STRONGLY_SUPPORTED"
    C_SOURCE_VERIFIED_CONTENT_UNCERTAIN = "C_SOURCE_VERIFIED_CONTENT_UNCERTAIN"
    D_LOCAL_ONLY_PROVENANCE = "D_LOCAL_ONLY_PROVENANCE"
    E_CONTRADICTED = "E_CONTRADICTED"


@dataclass(frozen=True)
class FileFingerprint:
    path: str
    byte_length: int
    sha256: str
    digest_kind: str

    def __post_init__(self) -> None:
        if not self.path or self.byte_length < 0 or not _is_sha256(self.sha256):
            raise ValueError("file fingerprint requires path, byte length, and lowercase SHA-256")
        if self.digest_kind not in {"CURRENT_AUDIT_DIGEST", "RETRIEVAL_AUDIT_DIGEST"}:
            raise ValueError("digest kind cannot imply acquisition-time historical evidence")

    @classmethod
    def current_audit(cls, path: Path) -> "FileFingerprint":
        return cls(str(path), path.stat().st_size, file_sha256(path), "CURRENT_AUDIT_DIGEST")

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "byte_length": self.byte_length,
            "sha256": self.sha256,
            "digest_kind": self.digest_kind,
        }


def assert_unchanged(before: FileFingerprint, after: FileFingerprint) -> None:
    if before.path != after.path or before.byte_length != after.byte_length or before.sha256 != after.sha256:
        raise RuntimeError("HIGH: original legacy session changed during Telegram access")


def git_ignores(path: Path, repo_root: Path) -> bool:
    try:
        relative = path.resolve().relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ValueError("working session must be inside the target repository") from exc
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--", relative.as_posix()],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    return result.returncode == 0


def make_working_session_copy(original: Path, working: Path, repo_root: Path) -> FileFingerprint:
    """Copy a session only after proving the destination is local and ignored."""
    original = original.resolve()
    working = working.resolve()
    repo_root = repo_root.resolve()
    if original == working:
        raise ValueError("original session can never be used as the working session")
    try:
        relative = working.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError("working session must be inside the target repository") from exc
    if not relative.parts or relative.parts[0] != "telegram_sessions":
        raise ValueError("working session must be under the local telegram_sessions area")
    if not git_ignores(working, repo_root):
        raise ValueError("working session copy is not Git-ignored")
    baseline = FileFingerprint.current_audit(original)
    working.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(original, working)
    copied = FileFingerprint.current_audit(working)
    if (copied.byte_length, copied.sha256) != (baseline.byte_length, baseline.sha256):
        raise RuntimeError("working session copy failed byte verification")
    return baseline


def open_client_with_working_session(
    client_factory: Callable[..., Any], original: Path, working: Path, repo_root: Path, *credentials: Any
) -> tuple[Any, FileFingerprint]:
    """Construct a client only with a verified working copy, never the original."""
    baseline = make_working_session_copy(original, working, repo_root)
    client = client_factory(str(working.resolve()), *credentials)
    return client, baseline


@dataclass(frozen=True)
class ProcessedManifestLink:
    manifest_path: str
    source_file: str
    telegram_message_id: int
    stored_content_sha256: str
    current_audit_hash_matches: bool
    digest_semantics: str = "PARSER_TIME_PROCESSED_MANIFEST_DIGEST_NOT_ACQUISITION_TIME_EVIDENCE"

    def __post_init__(self) -> None:
        if not self.manifest_path or not self.source_file or not _is_sha256(self.stored_content_sha256):
            raise ValueError("processed manifest linkage is incomplete")

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_path": self.manifest_path,
            "source_file": self.source_file,
            "telegram_message_id": self.telegram_message_id,
            "stored_content_sha256": self.stored_content_sha256,
            "current_audit_hash_matches": self.current_audit_hash_matches,
            "digest_semantics": self.digest_semantics,
        }


def load_processed_manifest_link(
    manifest_path: Path, message_id: int, raw_fingerprint: FileFingerprint
) -> ProcessedManifestLink | None:
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        matches = [row for row in csv.DictReader(handle) if row.get("telegram_message_id") == str(message_id)]
    if not matches:
        return None
    if len(matches) != 1:
        raise ValueError("processed manifest linkage is not unique")
    row = matches[0]
    stored = row.get("content_sha256", "")
    return ProcessedManifestLink(
        str(manifest_path), row.get("source_file", ""), message_id, stored,
        stored == raw_fingerprint.sha256,
    )


@dataclass(frozen=True)
class CorrectionLink:
    registry_path: str
    message_id: int
    entries_found: int
    boundary: str = "retrospective"
    raw_content_modified: bool = False

    def __post_init__(self) -> None:
        if self.boundary != "retrospective" or self.raw_content_modified or self.entries_found < 0:
            raise ValueError("correction metadata must remain a separate retrospective layer")

    def to_dict(self) -> dict[str, Any]:
        return {
            "registry_path": self.registry_path,
            "message_id": self.message_id,
            "entries_found": self.entries_found,
            "boundary": self.boundary,
            "raw_content_modified": self.raw_content_modified,
        }


def load_correction_link(registry_path: Path, message_id: int) -> CorrectionLink:
    with registry_path.open("r", encoding="utf-8-sig", newline="") as handle:
        count = sum(row.get("telegram_message_id") == str(message_id) for row in csv.DictReader(handle))
    return CorrectionLink(str(registry_path), message_id, count)


@dataclass(frozen=True)
class ComparisonEvidence:
    raw_file_bytes_sha256: str
    raw_file_byte_length: int
    legacy_serialized_content_sha256: str | None
    legacy_serialized_content_byte_length: int | None
    current_telegram_content_sha256: str | None
    current_telegram_content_byte_length: int | None
    transformations: tuple[str, ...]
    result: ComparisonResult

    def __post_init__(self) -> None:
        if not _is_sha256(self.raw_file_bytes_sha256) or self.raw_file_byte_length < 0:
            raise ValueError("raw comparison level requires current bytes")
        for value in (self.legacy_serialized_content_sha256, self.current_telegram_content_sha256):
            if value is not None and not _is_sha256(value):
                raise ValueError("comparison digest must be lowercase SHA-256")
        if not isinstance(self.result, ComparisonResult):
            object.__setattr__(self, "result", ComparisonResult(self.result))
        if self.result is not ComparisonResult.COMPARISON_IMPOSSIBLE and not self.transformations:
            raise ValueError("comparison transformations must be explicit")

    def to_dict(self) -> dict[str, Any]:
        return {
            "levels": {
                "RAW_FILE_BYTES": {
                    "sha256": self.raw_file_bytes_sha256,
                    "byte_length": self.raw_file_byte_length,
                    "digest_kind": "CURRENT_AUDIT_DIGEST",
                },
                "LEGACY_SERIALIZED_MESSAGE_CONTENT": {
                    "sha256": self.legacy_serialized_content_sha256,
                    "byte_length": self.legacy_serialized_content_byte_length,
                },
                "CURRENT_TELEGRAM_MESSAGE_CONTENT": {
                    "sha256": self.current_telegram_content_sha256,
                    "byte_length": self.current_telegram_content_byte_length,
                    "digest_kind": "RETRIEVAL_AUDIT_DIGEST" if self.current_telegram_content_sha256 else None,
                },
            },
            "transformations": list(self.transformations),
            "result": self.result.value,
        }


def compare_legacy_serialization(raw: bytes, current_text: str | None) -> ComparisonEvidence:
    raw_digest = hashlib.sha256(raw).hexdigest()
    if current_text is None:
        return ComparisonEvidence(raw_digest, len(raw), None, None, None, None, (),
                                  ComparisonResult.COMPARISON_IMPOSSIBLE)
    current = current_text.encode("utf-8")
    # Exact reconstruction of Path.write_text(text, encoding="utf-8") on the
    # Windows host used by the legacy collector: TextIOWrapper newline=None
    # translates each LF code point to CRLF.  No Unicode or whitespace
    # normalization, trimming, BOM insertion, or trailing newline is applied.
    legacy_serialized = current_text.replace("\n", "\r\n").encode("utf-8")
    transformations = (
        "CURRENT_TELEGRAM_MESSAGE_CONTENT: str.encode('utf-8'); no normalization",
        "LEGACY_SERIALIZED_MESSAGE_CONTENT: replace each U+000A LF with CRLF for Windows text-mode newline translation, then UTF-8 encode",
        "No BOM, Unicode normalization, whitespace trimming, header insertion, or trailing-newline insertion",
    )
    if raw == current:
        result = ComparisonResult.EXACT_MATCH
    elif raw == legacy_serialized:
        result = ComparisonResult.CANONICAL_MATCH
    else:
        result = ComparisonResult.MISMATCH
    return ComparisonEvidence(
        raw_digest, len(raw), hashlib.sha256(legacy_serialized).hexdigest(), len(legacy_serialized),
        hashlib.sha256(current).hexdigest(), len(current), transformations, result,
    )


def classify_evidence(
    *, authorized: bool, identity_verified: bool, metadata_conflict: bool,
    comparison: ComparisonResult, edit_after_cutoff: bool,
) -> EvidenceClassification:
    if not authorized or not identity_verified:
        return EvidenceClassification.D_LOCAL_ONLY_PROVENANCE
    if metadata_conflict or comparison is ComparisonResult.MISMATCH:
        return EvidenceClassification.E_CONTRADICTED
    if comparison is ComparisonResult.COMPARISON_IMPOSSIBLE or edit_after_cutoff:
        return EvidenceClassification.C_SOURCE_VERIFIED_CONTENT_UNCERTAIN
    # A current API response and a later-preserved local copy do not alone
    # prove byte-level content availability at the original historical cutoff.
    return EvidenceClassification.B_SOURCE_VERIFIED_CONTENT_STRONGLY_SUPPORTED


@dataclass(frozen=True)
class ProvenanceRepairRecord:
    repair_record_id: str
    legacy_artifact: FileFingerprint
    legacy_file_timestamp: datetime
    processed_manifest: ProcessedManifestLink | None
    correction: CorrectionLink
    original_session_before: FileFingerprint
    original_session_after: FileFingerprint
    original_session_unchanged: bool
    authorization_status: AuthorizationStatus
    telegram_message_id: int
    telegram_source_identifier: str | None
    source_timestamp: datetime | None
    edit_timestamp: datetime | None
    edit_timestamp_status: EditTimestampStatus
    retrieval_timestamp: datetime
    intended_cutoff: datetime | None
    deletion_or_unavailability_state: str
    comparison: ComparisonEvidence
    evidence_classification: EvidenceClassification
    historical_availability: str
    provenance_limitations: tuple[str, ...]
    genuine_fixture_manifest_allowed: bool
    assessment_payload_allowed: bool = False
    schema_version: str = REPAIR_SCHEMA_VERSION
    repair_record_digest: str = ""

    def __post_init__(self) -> None:
        if not self.repair_record_id or self.schema_version != REPAIR_SCHEMA_VERSION:
            raise ValueError("repair record identity/version is required")
        if self.legacy_artifact.digest_kind != "CURRENT_AUDIT_DIGEST":
            raise ValueError("legacy digest must remain current audit evidence")
        if not isinstance(self.authorization_status, AuthorizationStatus):
            object.__setattr__(self, "authorization_status", AuthorizationStatus(self.authorization_status))
        if not isinstance(self.edit_timestamp_status, EditTimestampStatus):
            object.__setattr__(self, "edit_timestamp_status", EditTimestampStatus(self.edit_timestamp_status))
        if not isinstance(self.evidence_classification, EvidenceClassification):
            object.__setattr__(self, "evidence_classification", EvidenceClassification(self.evidence_classification))
        legacy_file_timestamp = _utc(self.legacy_file_timestamp, "legacy_file_timestamp")
        retrieval = _utc(self.retrieval_timestamp, "retrieval_timestamp")
        object.__setattr__(self, "legacy_file_timestamp", legacy_file_timestamp)
        object.__setattr__(self, "retrieval_timestamp", retrieval)
        for name in ("source_timestamp", "edit_timestamp", "intended_cutoff"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _utc(value, name))
        if self.edit_timestamp_status is EditTimestampStatus.PRESENT and self.edit_timestamp is None:
            raise ValueError("present edit status requires edit timestamp")
        if self.edit_timestamp_status is not EditTimestampStatus.PRESENT and self.edit_timestamp is not None:
            raise ValueError("edit timestamp is allowed only when API reports it present")
        if not self.original_session_unchanged:
            raise ValueError("a repair record cannot be issued after original session mutation")
        assert_unchanged(self.original_session_before, self.original_session_after)
        if self.assessment_payload_allowed and self.evidence_classification is not EvidenceClassification.A_CUTOFF_VERIFIED:
            raise ValueError("only cutoff-verified evidence can permit an assessment payload")
        if self.genuine_fixture_manifest_allowed and self.evidence_classification not in {
            EvidenceClassification.A_CUTOFF_VERIFIED,
            EvidenceClassification.B_SOURCE_VERIFIED_CONTENT_STRONGLY_SUPPORTED,
        }:
            raise ValueError("fixture manifest requires at least strongly supported content")
        computed = _digest(self._content_dict())
        if self.repair_record_digest and self.repair_record_digest != computed:
            raise ValueError("repair record digest mismatch")
        object.__setattr__(self, "repair_record_digest", computed)

    def _content_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "repair_record_id": self.repair_record_id,
            "legacy_artifact": self.legacy_artifact.to_dict(),
            "legacy_file_timestamp": _iso(self.legacy_file_timestamp),
            "processed_manifest": self.processed_manifest.to_dict() if self.processed_manifest else None,
            "correction": self.correction.to_dict(),
            "original_session_mutation_check": {
                "path": self.original_session_before.path,
                "before_byte_length": self.original_session_before.byte_length,
                "before_sha256": self.original_session_before.sha256,
                "after_byte_length": self.original_session_after.byte_length,
                "after_sha256": self.original_session_after.sha256,
                "digest_kind": "CURRENT_AUDIT_DIGEST_FOR_MUTATION_DETECTION_ONLY",
                "unchanged": self.original_session_unchanged,
            },
            "authorization_status": self.authorization_status.value,
            "telegram_message_id": self.telegram_message_id,
            "telegram_source_identifier": self.telegram_source_identifier,
            "source_timestamp": _iso(self.source_timestamp),
            "edit_timestamp": _iso(self.edit_timestamp),
            "edit_timestamp_status": self.edit_timestamp_status.value,
            "retrieval_timestamp": _iso(self.retrieval_timestamp),
            "intended_cutoff": _iso(self.intended_cutoff),
            "deletion_or_unavailability_state": self.deletion_or_unavailability_state,
            "comparison": self.comparison.to_dict(),
            "evidence_classification": self.evidence_classification.value,
            "historical_availability": self.historical_availability,
            "provenance_limitations": list(self.provenance_limitations),
            "genuine_fixture_manifest_allowed": self.genuine_fixture_manifest_allowed,
            "assessment_payload_allowed": self.assessment_payload_allowed,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._content_dict(), "repair_record_digest": self.repair_record_digest}

    def to_json(self) -> str:
        return _canonical_json(self.to_dict())


@dataclass(frozen=True)
class ExternalFixtureReferenceManifest:
    fixture_id: str
    raw_reference: str
    byte_length: int
    current_audit_sha256: str
    provenance_repair_record: str
    provenance_repair_digest: str
    telegram_source_identifier: str
    telegram_message_id: int
    source_timestamp: datetime
    edit_timestamp: datetime | None
    edit_timestamp_status: EditTimestampStatus
    retrieval_timestamp: datetime
    availability_state: str = "unknown"
    available_at: None = None
    assessment_permitted: bool = False
    raw_reference_access: str = "read_only"
    digest_kind: str = "CURRENT_AUDIT_DIGEST"
    schema_version: str = FIXTURE_REFERENCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.fixture_id or not self.raw_reference or not _is_sha256(self.current_audit_sha256):
            raise ValueError("external fixture identity, path, and current digest are required")
        if not _is_sha256(self.provenance_repair_digest):
            raise ValueError("external fixture must bind the repair record")
        if self.raw_reference_access != "read_only" or self.digest_kind != "CURRENT_AUDIT_DIGEST":
            raise ValueError("external fixture cannot upgrade or write legacy evidence")
        if self.availability_state != "unknown" or self.available_at is not None or self.assessment_permitted:
            raise ValueError("restricted repaired fixture must fail closed before assessment")
        object.__setattr__(self, "source_timestamp", _utc(self.source_timestamp, "source_timestamp"))
        object.__setattr__(self, "retrieval_timestamp", _utc(self.retrieval_timestamp, "retrieval_timestamp"))
        if self.edit_timestamp is not None:
            object.__setattr__(self, "edit_timestamp", _utc(self.edit_timestamp, "edit_timestamp"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "fixtures": [{
                "fixture_id": self.fixture_id,
                "raw_reference": self.raw_reference,
                "raw_reference_access": self.raw_reference_access,
                "byte_length": self.byte_length,
                "content_sha256": self.current_audit_sha256,
                "digest_kind": self.digest_kind,
                "provenance_repair_record": self.provenance_repair_record,
                "provenance_repair_digest": self.provenance_repair_digest,
                "telegram_source_identifier": self.telegram_source_identifier,
                "telegram_message_id": self.telegram_message_id,
                "source_timestamp": _iso(self.source_timestamp),
                "edit_timestamp": _iso(self.edit_timestamp),
                "edit_timestamp_status": self.edit_timestamp_status.value,
                "retrieval_timestamp": _iso(self.retrieval_timestamp),
                "availability_state": self.availability_state,
                "available_at": self.available_at,
                "assessment_permitted": self.assessment_permitted,
            }],
        }

    def to_json(self) -> str:
        return _canonical_json(self.to_dict())

    @property
    def content_digest(self) -> str:
        return _digest(self.to_dict())

    def validate_external_bytes(self, allowed_read_only_roots: tuple[Path, ...]) -> None:
        path = Path(self.raw_reference).resolve()
        roots = tuple(root.resolve() for root in allowed_read_only_roots)
        if not any(path.is_relative_to(root) for root in roots):
            raise ValueError("external fixture is outside allowlisted read-only roots")
        if path.stat().st_size != self.byte_length or file_sha256(path) != self.current_audit_sha256:
            raise ValueError("external fixture bytes do not match current audit evidence")


def write_once(path: Path, content: str) -> bool:
    encoded = (content + "\n").encode("utf-8")
    if path.exists():
        if path.read_bytes() == encoded:
            return False
        raise FileExistsError(f"refusing to overwrite different evidence artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(encoded)
    return True
