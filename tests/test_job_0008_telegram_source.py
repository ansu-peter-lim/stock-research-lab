import hashlib
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.research_contracts.historical_fixture import (
    AvailabilityState,
    FIXTURE_PARSER_VERSION,
    FixtureManifest,
    FixtureManifestEntry,
    parse_top30_fixture,
)


UTC = timezone.utc
ROOT = Path(__file__).parents[1]


class GenuineTelegramSourceBoundaryTests(unittest.TestCase):
    def entry(self, raw: bytes, *, availability=AvailabilityState.UNKNOWN, edit=None):
        return FixtureManifestEntry(
            "telegram-balanceasset-123",
            "raw/message.utf8.txt",
            len(raw),
            hashlib.sha256(raw).hexdigest(),
            "Telegram API current-message retrieval; canonical UTF-8 representation",
            datetime(2024, 6, 3, 8, tzinfo=UTC),
            datetime(2026, 9, 19, 1, tzinfo=UTC),
            availability,
            datetime(2024, 6, 3, 8, tzinfo=UTC) if availability is AvailabilityState.KNOWN else None,
            "telegram_current_message_canonical_utf8",
            FIXTURE_PARSER_VERSION,
            "telegram:balanceasset:message:123",
            edit,
            "API date proves publication metadata, not historical message bytes",
            "job-0008-telethon-1.45.0-canonical-utf8-1",
        )

    def test_git_ignores_secret_and_telegram_session_artifacts(self):
        for path in (".env", "telegram_sessions/job-0008.session", "telegram_sessions/job-0008.session-journal"):
            result = subprocess.run(["git", "check-ignore", path], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(0, result.returncode, path)

    def test_manifest_binds_genuine_source_identity_bytes_and_distinct_times(self):
        raw = b"source-observed bytes"
        entry = self.entry(raw)
        manifest = FixtureManifest((entry,))
        data = entry.to_dict()
        self.assertEqual("telegram:balanceasset:message:123", data["source_identity"])
        self.assertNotEqual(data["source_timestamp"], data["ingested_at"])
        self.assertIsNone(data["edit_timestamp"])
        self.assertEqual("unknown", data["availability_state"])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / entry.raw_path
            target.parent.mkdir(parents=True)
            target.write_bytes(raw)
            manifest.validate_bytes(root)
            target.write_bytes(raw + b"x")
            with self.assertRaisesRegex(ValueError, "bytes do not match"):
                manifest.validate_bytes(root)

    def test_unknown_availability_and_post_cutoff_edit_fail_closed(self):
        raw = b"observation_date=2024-06-03\n1|Exact Source Name||detail\n"
        unknown = FixtureManifest((self.entry(raw),))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "raw/message.utf8.txt"
            target.parent.mkdir(parents=True)
            target.write_bytes(raw)
            with self.assertRaisesRegex(ValueError, "availability is unknown"):
                parse_top30_fixture(unknown, root, "telegram-balanceasset-123")

            post_edit = self.entry(raw, availability=AvailabilityState.KNOWN,
                                   edit=datetime(2024, 6, 3, 8, tzinfo=UTC) + timedelta(seconds=1))
            with self.assertRaisesRegex(ValueError, "edited after cutoff"):
                parse_top30_fixture(FixtureManifest((post_edit,)), root, post_edit.fixture_id)

    def test_parser_preserves_source_name_and_unresolved_identity(self):
        raw = b"observation_date=2024-06-03\n1|Exact Source Name||detail\n"
        entry = self.entry(raw, availability=AvailabilityState.KNOWN)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / entry.raw_path
            target.parent.mkdir(parents=True)
            target.write_bytes(raw)
            observation = parse_top30_fixture(FixtureManifest((entry,)), root, entry.fixture_id)[0]
        self.assertEqual("Exact Source Name", observation.stock_name)
        self.assertEqual("unresolved", observation.mapping.status)
        self.assertIsNone(observation.mapping.stock_code)

    def test_generated_research_data_cannot_contain_credential_assignment(self):
        raw_root = ROOT / "data" / "raw" / "telegram" / "job-0008"
        if not raw_root.exists():
            return
        for path in raw_root.rglob("*"):
            if path.is_file():
                self.assertNotIn(b"TELEGRAM_API_HASH=", path.read_bytes())
                self.assertNotIn(b"TELEGRAM_API_ID=", path.read_bytes())


if __name__ == "__main__":
    unittest.main()
