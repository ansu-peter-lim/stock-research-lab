"""Quarantined parsing for one provenance-repaired Telegram source.

This is deliberately *before* ``Top30Observation``.  It preserves genuine
source text but never supplies a cutoff-visible source or identity assertion.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .telegram_provenance_repair import ExternalFixtureReferenceManifest, file_sha256


PARSER_VERSION = "job-0011-telegram-preassessment-1"
SCHEMA_VERSION = "preassessment-top30-1"
QUARANTINE_STATUS = "QUARANTINED / NOT ASSESSMENT ELIGIBLE"
QUARANTINE_REASON = "historical availability is unknown; JOB-0010 evidence is not cutoff-verified"
DAILY_HEADER_RE = re.compile(r"(?P<year>\d{4})\s*년\s*(?P<month>\d{1,2})\s*월\s*(?P<day>\d{1,2})\s*일\s*상승률\s*TOP\s*30", re.I)
ROW_RE = re.compile(r"(?m)^\s*(?P<rank>\d{1,2})\.\s*(?P<name>[^\r\n(]+?)\s*\((?P<return>[+-]?\d+(?:\.\d+)?)\s*%\)\s*:\s*")
RANK_LINE_RE = re.compile(r"(?m)^\s*\d{1,2}\.")


class QuarantineError(ValueError):
    """Raised when a pre-assessment object is offered to an assessment API."""


def _canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass(frozen=True)
class PreAssessmentRow:
    rank: int | None
    source_stock_name: str
    return_pct: Decimal | None
    detail_raw: str
    identity_state: str = "unresolved"
    normalization_metadata: str = "none; source_stock_name preserved verbatim"

    def to_dict(self) -> dict[str, Any]:
        return {"rank": self.rank, "source_stock_name": self.source_stock_name,
                "return_pct": None if self.return_pct is None else str(self.return_pct),
                "detail_raw": self.detail_raw, "identity_state": self.identity_state,
                "normalization_metadata": self.normalization_metadata}


@dataclass(frozen=True)
class PreAssessmentTop30:
    fixture_id: str
    source_fixture_manifest_digest: str
    source_content_sha256: str
    provenance_repair_record: str
    provenance_repair_digest: str
    provenance_classification: str
    telegram_message_id: int
    source_timestamp: datetime
    report_date_candidate: date | None
    parser_version: str
    availability_state: str
    quarantine_status: str
    quarantine_reason: str
    recognized_as_top30: bool
    rows: tuple[PreAssessmentRow, ...]
    issues: tuple[str, ...]
    correction_count: int
    representation_digest: str = ""
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION or self.parser_version != PARSER_VERSION:
            raise ValueError("unsupported pre-assessment schema or parser version")
        if self.availability_state != "unknown" or self.quarantine_status != QUARANTINE_STATUS:
            raise ValueError("pre-assessment source must remain quarantined with unknown availability")
        if self.provenance_classification != "B_SOURCE_VERIFIED_CONTENT_STRONGLY_SUPPORTED":
            raise ValueError("unexpected provenance classification for this restricted source")
        if any(row.identity_state != "unresolved" for row in self.rows):
            raise ValueError("pre-assessment rows cannot resolve identities")
        computed = _digest(self._content_dict())
        if self.representation_digest and self.representation_digest != computed:
            raise ValueError("pre-assessment representation digest mismatch")
        object.__setattr__(self, "representation_digest", computed)

    def _content_dict(self) -> dict[str, Any]:
        return {"schema_version": self.schema_version, "fixture_id": self.fixture_id,
                "source_fixture_manifest_digest": self.source_fixture_manifest_digest,
                "source_content_sha256": self.source_content_sha256,
                "provenance_repair_record": self.provenance_repair_record,
                "provenance_repair_digest": self.provenance_repair_digest,
                "provenance_classification": self.provenance_classification,
                "telegram_message_id": self.telegram_message_id,
                "source_timestamp": self.source_timestamp.isoformat(timespec="microseconds").replace("+00:00", "Z"),
                "report_date_candidate": self.report_date_candidate.isoformat() if self.report_date_candidate else None,
                "parser_version": self.parser_version, "availability_state": self.availability_state,
                "quarantine_status": self.quarantine_status, "quarantine_reason": self.quarantine_reason,
                "recognized_as_top30": self.recognized_as_top30,
                "rows": [row.to_dict() for row in self.rows], "issues": list(self.issues),
                "correction_count": self.correction_count}

    def to_dict(self) -> dict[str, Any]:
        return {**self._content_dict(), "representation_digest": self.representation_digest}

    def to_json(self) -> str:
        return _canonical_json(self.to_dict())

    def promote_to_top30_observations(self) -> None:
        raise QuarantineError(QUARANTINE_REASON)

    def assessment_payload(self) -> None:
        raise QuarantineError(QUARANTINE_REASON)

    def freeze_assessment(self) -> None:
        raise QuarantineError(QUARANTINE_REASON)


def _fixture_manifest_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _correction_count(path: Path, message_id: int) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return sum(row.get("telegram_message_id") == str(message_id) for row in csv.DictReader(handle))


def parse_restricted_telegram_fixture(
    fixture_manifest_path: Path, repair_record_path: Path, correction_registry_path: Path,
    allowed_read_only_roots: tuple[Path, ...],
) -> PreAssessmentTop30:
    """Validate JOB-0010 evidence, then parse exactly its one restricted source."""
    fixture_data = json.loads(fixture_manifest_path.read_text(encoding="utf-8"))
    fixtures = fixture_data.get("fixtures", [])
    if fixture_data.get("schema_version") != "job-0010-external-fixture-reference-1" or len(fixtures) != 1:
        raise ValueError("expected exactly one JOB-0010 restricted fixture")
    item = fixtures[0]
    fixture = ExternalFixtureReferenceManifest(
        item["fixture_id"], item["raw_reference"], item["byte_length"], item["content_sha256"],
        item["provenance_repair_record"], item["provenance_repair_digest"], item["telegram_source_identifier"],
        item["telegram_message_id"], _parse_utc(item["source_timestamp"]),
        _parse_utc(item["edit_timestamp"]) if item.get("edit_timestamp") else None,
        item["edit_timestamp_status"], _parse_utc(item["retrieval_timestamp"]),
        item["availability_state"], item["available_at"], item["assessment_permitted"],
        item["raw_reference_access"], item["digest_kind"], fixture_data["schema_version"],
    )
    fixture.validate_external_bytes(allowed_read_only_roots)
    repair = json.loads(repair_record_path.read_text(encoding="utf-8"))
    stored_repair_digest = repair.pop("repair_record_digest")
    if _digest(repair) != stored_repair_digest or stored_repair_digest != fixture.provenance_repair_digest:
        raise ValueError("provenance repair record digest mismatch")
    if repair.get("evidence_classification") != "B_SOURCE_VERIFIED_CONTENT_STRONGLY_SUPPORTED":
        raise ValueError("restricted fixture provenance classification mismatch")
    if repair.get("assessment_payload_allowed") or repair.get("telegram_message_id") != fixture.telegram_message_id:
        raise ValueError("repair record cannot permit assessment or identify another message")
    if repair.get("legacy_artifact", {}).get("sha256") != fixture.current_audit_sha256:
        raise ValueError("repair record source digest does not match restricted fixture")
    raw_path = Path(fixture.raw_reference)
    raw = raw_path.read_bytes()
    if file_sha256(raw_path) != fixture.current_audit_sha256:
        raise ValueError("source byte mismatch blocks parsing")
    text = raw.decode("utf-8")
    header = DAILY_HEADER_RE.search(text)
    recognized = header is not None
    report_date = date(int(header["year"]), int(header["month"]), int(header["day"])) if header else None
    matches = list(ROW_RE.finditer(text)) if recognized else []
    rows: list[PreAssessmentRow] = []
    issues: list[str] = []
    for index, match in enumerate(matches):
        rank, name = int(match["rank"]), match["name"].strip()
        try:
            return_pct = Decimal(match["return"])
        except (InvalidOperation, ValueError):
            return_pct = None
            issues.append(f"RETURN_PCT_INVALID:{rank}")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        rows.append(PreAssessmentRow(rank, name, return_pct, text[match.end():end].rstrip("\r\n")))
    matched_starts = {match.start() for match in matches}
    for rank_start in RANK_LINE_RE.finditer(text):
        if rank_start.start() not in matched_starts:
            issues.append(f"MALFORMED_ROW_AT_OFFSET:{rank_start.start()}")
    ranks = [row.rank for row in rows if row.rank is not None]
    if len(rows) != 30:
        issues.append(f"RANK_COUNT_NOT_30:{len(rows)}")
    if len(set(ranks)) != len(ranks):
        issues.append("DUPLICATE_RANK")
    if set(ranks) != set(range(1, 31)):
        issues.append("RANK_COVERAGE_INCOMPLETE")
    correction_count = _correction_count(correction_registry_path, fixture.telegram_message_id)
    return PreAssessmentTop30(
        fixture.fixture_id, _fixture_manifest_digest(fixture_manifest_path), fixture.current_audit_sha256,
        fixture.provenance_repair_record, fixture.provenance_repair_digest,
        repair["evidence_classification"], fixture.telegram_message_id, fixture.source_timestamp, report_date,
        PARSER_VERSION, fixture.availability_state, QUARANTINE_STATUS, QUARANTINE_REASON, recognized,
        tuple(rows), tuple(sorted(issues)), correction_count,
    )


def write_preassessment_artifact(path: Path, parsed: PreAssessmentTop30) -> bool:
    content = (parsed.to_json() + "\n").encode("utf-8")
    if path.exists():
        if path.read_bytes() == content:
            return False
        raise FileExistsError(f"refusing to overwrite different pre-assessment artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(content)
    return True
