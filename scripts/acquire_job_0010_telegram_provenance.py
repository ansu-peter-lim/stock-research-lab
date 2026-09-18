"""Repair provenance for Telegram message 15617 and no other message.

The original legacy session is fingerprinted but never given to Telethon.
Only a verified Git-ignored copy under ``telegram_sessions`` is opened.
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from telethon import TelegramClient, utils

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.research_contracts.telegram_provenance_repair import (
    AuthorizationStatus,
    ComparisonResult,
    EditTimestampStatus,
    EvidenceClassification,
    ExternalFixtureReferenceManifest,
    FileFingerprint,
    ProvenanceRepairRecord,
    assert_unchanged,
    classify_evidence,
    compare_legacy_serialization,
    load_correction_link,
    load_processed_manifest_link,
    open_client_with_working_session,
    write_once,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
LEGACY_ROOT = Path("D:/Project/stock")
LEGACY_RAW = LEGACY_ROOT / "data/raw/telegram/daily/2023-09-01_07-36-30_15617.txt"
LEGACY_MANIFEST = LEGACY_ROOT / "data/processed/telegram/top30_report_manifest.csv"
CORRECTIONS = LEGACY_ROOT / "data/manual/telegram/top30_corrections.csv"
ORIGINAL_SESSION = LEGACY_ROOT / "telegram_test.session"
WORKING_SESSION = REPO_ROOT / "telegram_sessions/job-0010/telegram_test.session"
REPAIR_PATH = REPO_ROOT / "data/metadata/job-0010-telegram-provenance-repair.json"
FIXTURE_MANIFEST_PATH = REPO_ROOT / "data/fixtures/job-0010/fixture-manifest.json"
EXPECTED_CHANNEL = "balanceasset"
MESSAGE_ID = 15617


def _legacy_file_timestamp(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)


def _manifest_source_timestamp(link_path: Path, message_id: int) -> datetime | None:
    import csv

    with link_path.open("r", encoding="utf-8-sig", newline="") as handle:
        matches = [row for row in csv.DictReader(handle) if row.get("telegram_message_id") == str(message_id)]
    if len(matches) != 1 or not matches[0].get("telegram_posted_at"):
        return None
    return datetime.fromisoformat(matches[0]["telegram_posted_at"].replace("Z", "+00:00"))


def _build_record(
    *,
    raw_fingerprint: FileFingerprint,
    manifest_link,
    correction_link,
    session_before: FileFingerprint,
    session_after: FileFingerprint,
    authorization_status: AuthorizationStatus,
    source_identifier: str | None,
    source_timestamp: datetime | None,
    edit_timestamp: datetime | None,
    edit_status: EditTimestampStatus,
    retrieval_timestamp: datetime,
    unavailable_state: str,
    comparison,
    classification: EvidenceClassification,
) -> ProvenanceRepairRecord:
    fixture_allowed = classification in {
        EvidenceClassification.A_CUTOFF_VERIFIED,
        EvidenceClassification.B_SOURCE_VERIFIED_CONTENT_STRONGLY_SUPPORTED,
    }
    historical_availability = (
        "Current Telegram source/message metadata and matching content support provenance, but neither the "
        "current API response nor the later local file proves that these exact bytes were immutable and visible "
        "at the original source timestamp. Availability remains unknown for assessment purposes."
        if fixture_allowed else
        "Historical cutoff visibility is not established; the artifact remains unavailable to assessment."
    )
    return ProvenanceRepairRecord(
        repair_record_id="JOB-0010-telegram-balanceasset-15617",
        legacy_artifact=raw_fingerprint,
        legacy_file_timestamp=_legacy_file_timestamp(LEGACY_RAW),
        processed_manifest=manifest_link,
        correction=correction_link,
        original_session_before=session_before,
        original_session_after=session_after,
        original_session_unchanged=True,
        authorization_status=authorization_status,
        telegram_message_id=MESSAGE_ID,
        telegram_source_identifier=source_identifier,
        source_timestamp=source_timestamp,
        edit_timestamp=edit_timestamp,
        edit_timestamp_status=edit_status,
        retrieval_timestamp=retrieval_timestamp,
        intended_cutoff=source_timestamp,
        deletion_or_unavailability_state=unavailable_state,
        comparison=comparison,
        evidence_classification=classification,
        historical_availability=historical_availability,
        provenance_limitations=(
            "Telegram current-message retrieval does not expose revision history.",
            "A missing current edit timestamp is recorded only as none reported by the current API, not proof that no historical edit ever occurred.",
            "The legacy file timestamp and current/parser-time hashes are not acquisition-time evidence.",
            "The prompt's data/telegram path was absent; the canonical JOB-0009 data/raw/telegram path was used.",
            "No channel-completeness or deleted-message history is established by retrieval of one exact ID.",
        ),
        genuine_fixture_manifest_allowed=fixture_allowed,
        assessment_payload_allowed=False,
    )


async def acquire() -> int:
    raw_fingerprint = FileFingerprint.current_audit(LEGACY_RAW)
    raw = LEGACY_RAW.read_bytes()
    manifest_link = load_processed_manifest_link(LEGACY_MANIFEST, MESSAGE_ID, raw_fingerprint)
    correction_link = load_correction_link(CORRECTIONS, MESSAGE_ID)
    expected_source_timestamp = _manifest_source_timestamp(LEGACY_MANIFEST, MESSAGE_ID)

    load_dotenv(REPO_ROOT / ".env")
    if not os.environ.get("TELEGRAM_API_ID") or not os.environ.get("TELEGRAM_API_HASH"):
        print("JOB_0010_CREDENTIAL_CONFIGURATION_UNAVAILABLE")
        return 2

    client, session_before = open_client_with_working_session(
        TelegramClient,
        ORIGINAL_SESSION,
        WORKING_SESSION,
        REPO_ROOT,
        int(os.environ["TELEGRAM_API_ID"]),
        os.environ["TELEGRAM_API_HASH"],
    )
    authorization_status = AuthorizationStatus.CONNECTION_FAILED
    source_identifier = None
    source_timestamp = None
    edit_timestamp = None
    edit_status = EditTimestampStatus.UNKNOWN_NOT_RETRIEVED
    retrieval_timestamp = datetime.now(timezone.utc)
    unavailable_state = "NOT_RETRIEVED"
    comparison = compare_legacy_serialization(raw, None)
    classification = EvidenceClassification.D_LOCAL_ONLY_PROVENANCE
    exit_code = 7

    try:
        await client.connect()
        retrieval_timestamp = datetime.now(timezone.utc)
        if not await client.is_user_authorized():
            authorization_status = AuthorizationStatus.AUTHORIZATION_BLOCKED
            unavailable_state = "NOT_RETRIEVED_SESSION_UNAUTHORIZED"
            exit_code = 3
        else:
            authorization_status = AuthorizationStatus.AUTHORIZED
            channel = await client.get_entity(EXPECTED_CHANNEL)
            username = getattr(channel, "username", None)
            channel_matches = isinstance(username, str) and username.casefold() == EXPECTED_CHANNEL.casefold()
            peer_id = utils.get_peer_id(channel)
            source_identifier = f"telegram:channel_peer_id:{peer_id}:username:{EXPECTED_CHANNEL}"

            # This is a single-ID RPC, not history iteration or search.
            message = await client.get_messages(channel, ids=MESSAGE_ID)
            retrieval_timestamp = datetime.now(timezone.utc)
            if message is None or getattr(message, "id", None) != MESSAGE_ID:
                unavailable_state = "EXACT_MESSAGE_UNAVAILABLE_OR_DELETED"
                classification = EvidenceClassification.D_LOCAL_ONLY_PROVENANCE
                exit_code = 4
            else:
                unavailable_state = "CURRENT_MESSAGE_RETURNED"
                source_timestamp = message.date.astimezone(timezone.utc) if message.date else None
                edit_timestamp = message.edit_date.astimezone(timezone.utc) if message.edit_date else None
                edit_status = (
                    EditTimestampStatus.PRESENT if edit_timestamp
                    else EditTimestampStatus.NONE_REPORTED_BY_CURRENT_API
                )
                comparison = compare_legacy_serialization(raw, message.text)
                metadata_conflict = (
                    not channel_matches
                    or source_timestamp is None
                    or expected_source_timestamp is None
                    or source_timestamp != expected_source_timestamp
                    or manifest_link is None
                    or manifest_link.source_file != LEGACY_RAW.name
                    or not manifest_link.current_audit_hash_matches
                )
                edit_after_cutoff = bool(
                    edit_timestamp and source_timestamp and edit_timestamp > source_timestamp
                )
                classification = classify_evidence(
                    authorized=True,
                    identity_verified=channel_matches and message.id == MESSAGE_ID,
                    metadata_conflict=metadata_conflict,
                    comparison=comparison.result,
                    edit_after_cutoff=edit_after_cutoff,
                )
                exit_code = 0
    except Exception:
        authorization_status = AuthorizationStatus.CONNECTION_FAILED
        unavailable_state = "TELEGRAM_CONNECTION_OR_RETRIEVAL_FAILED"
        comparison = compare_legacy_serialization(raw, None)
        classification = EvidenceClassification.D_LOCAL_ONLY_PROVENANCE
        exit_code = 7
    finally:
        await client.disconnect()

    session_after = FileFingerprint.current_audit(ORIGINAL_SESSION)
    assert_unchanged(session_before, session_after)
    record = _build_record(
        raw_fingerprint=raw_fingerprint,
        manifest_link=manifest_link,
        correction_link=correction_link,
        session_before=session_before,
        session_after=session_after,
        authorization_status=authorization_status,
        source_identifier=source_identifier,
        source_timestamp=source_timestamp,
        edit_timestamp=edit_timestamp,
        edit_status=edit_status,
        retrieval_timestamp=retrieval_timestamp,
        unavailable_state=unavailable_state,
        comparison=comparison,
        classification=classification,
    )
    write_once(REPAIR_PATH, record.to_json())

    if record.genuine_fixture_manifest_allowed:
        fixture = ExternalFixtureReferenceManifest(
            fixture_id="telegram-balanceasset-15617",
            raw_reference=str(LEGACY_RAW),
            byte_length=raw_fingerprint.byte_length,
            current_audit_sha256=raw_fingerprint.sha256,
            provenance_repair_record=REPAIR_PATH.relative_to(REPO_ROOT).as_posix(),
            provenance_repair_digest=record.repair_record_digest,
            telegram_source_identifier=record.telegram_source_identifier or "",
            telegram_message_id=MESSAGE_ID,
            source_timestamp=record.source_timestamp,
            edit_timestamp=record.edit_timestamp,
            edit_timestamp_status=record.edit_timestamp_status,
            retrieval_timestamp=record.retrieval_timestamp,
        )
        fixture.validate_external_bytes((LEGACY_ROOT,))
        write_once(FIXTURE_MANIFEST_PATH, fixture.to_json())

    print(
        "JOB_0010_RESULT "
        f"authorization={authorization_status.value} "
        f"message_id={MESSAGE_ID} "
        f"comparison={comparison.result.value} "
        f"classification={classification.value} "
        "original_session_unchanged=true"
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(asyncio.run(acquire()))
