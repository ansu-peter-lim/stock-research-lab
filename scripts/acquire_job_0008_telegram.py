"""Acquire one Telegram Top30 message without persisting credentials.

The Telegram API supplies a current message representation, not its revision
history.  Therefore the resulting manifest deliberately records unknown
historical byte availability and cannot be used to create an assessment.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from telethon import TelegramClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.research_contracts.historical_fixture import (
    AvailabilityState,
    FixtureManifest,
    FixtureManifestEntry,
)


CHANNEL = "balanceasset"
TARGET_BEFORE = datetime(2024, 7, 1, tzinfo=timezone.utc)
SEARCH_LIMIT = 200
ACQUISITION_VERSION = "job-0008-telethon-1.45.0-canonical-utf8-1"
ROOT = Path("data/raw/telegram/job-0008")
SESSION = Path("telegram_sessions/job-0008")


def is_top30(text: str) -> bool:
    normalized = text.upper().replace(" ", "")
    return "TOP30" in normalized and "수익률" in text


async def acquire() -> int:
    load_dotenv(Path(".env"))
    required = ("TELEGRAM_API_ID", "TELEGRAM_API_HASH")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        print("MISSING:" + ",".join(missing))
        return 2

    SESSION.parent.mkdir(parents=True, exist_ok=True)
    client = None
    try:
        client = TelegramClient(str(SESSION), int(os.environ["TELEGRAM_API_ID"]), os.environ["TELEGRAM_API_HASH"])
        await client.connect()
        if not await client.is_user_authorized():
            print("TELEGRAM_AUTHORIZATION_REQUIRED")
            return 3
        channel = await client.get_entity(CHANNEL)
        selected = None
        async for message in client.iter_messages(channel, offset_date=TARGET_BEFORE, limit=SEARCH_LIMIT):
            if message.text and is_top30(message.text):
                selected = message
                break
        if selected is None:
            print("NO_HISTORICAL_TOP30_MESSAGE_FOUND_WITHIN_LIMIT")
            return 4

        # Telethon exposes Unicode text, not original Telegram transport bytes.
        raw = selected.text.encode("utf-8")
        ingested_at = datetime.now(timezone.utc)
        source_at = selected.date.astimezone(timezone.utc)
        edit_at = selected.edit_date.astimezone(timezone.utc) if selected.edit_date else None
        artifact_id = f"telegram-balanceasset-{selected.id}"
        raw_name = f"raw/{artifact_id}.utf8.txt"
        raw_path = ROOT / raw_name
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        if raw_path.exists() and raw_path.read_bytes() != raw:
            print("REFUSING_TO_OVERWRITE_DIFFERENT_RAW_ARTIFACT")
            return 5
        if not raw_path.exists():
            raw_path.write_bytes(raw)

        entry = FixtureManifestEntry(
            fixture_id=artifact_id,
            raw_path=raw_name,
            byte_length=len(raw),
            content_sha256=hashlib.sha256(raw).hexdigest(),
            provenance="Telegram API current-message retrieval; canonical UTF-8 representation",
            source_timestamp=source_at,
            ingested_at=ingested_at,
            availability_state=AvailabilityState.UNKNOWN,
            available_at=None,
            artifact_type="telegram_current_message_canonical_utf8",
            parser_version="legacy-telegram-top30-parser-patterns-reviewed",
            source_identity=f"telegram:balanceasset:message:{selected.id}",
            edit_timestamp=edit_at,
            availability_evidence=(
                "Telegram API returned message date and current text at ingestion; "
                "no historical byte-level cutoff availability or revision history is proven"
            ),
            acquisition_version=ACQUISITION_VERSION,
        )
        manifest_path = ROOT / "fixture-manifest.json"
        manifest = FixtureManifest((entry,))
        content = manifest.to_json() + "\n"
        if manifest_path.exists() and manifest_path.read_text(encoding="utf-8") != content:
            print("REFUSING_TO_OVERWRITE_EXISTING_MANIFEST")
            return 6
        if not manifest_path.exists():
            manifest_path.write_text(content, encoding="utf-8", newline="\n")
        print(f"ACQUIRED message_id={selected.id} sha256={entry.content_sha256} source_timestamp={source_at.isoformat()} edit_timestamp={'present' if edit_at else 'none'}")
        return 0
    except Exception:
        print("TELEGRAM_CONNECTION_OR_RETRIEVAL_FAILED")
        return 7
    finally:
        if client is not None:
            await client.disconnect()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(acquire()))
