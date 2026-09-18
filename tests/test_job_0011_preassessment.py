import hashlib
import json
import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from src.research_contracts.pre_assessment import (
    PARSER_VERSION,
    QUARANTINE_STATUS,
    QuarantineError,
    parse_restricted_telegram_fixture,
    write_preassessment_artifact,
)


ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "data/fixtures/job-0010/fixture-manifest.json"
REPAIR = ROOT / "data/metadata/job-0010-telegram-provenance-repair.json"
CORRECTIONS = Path("D:/Project/stock/data/manual/telegram/top30_corrections.csv")
LEGACY_ROOT = Path("D:/Project/stock")


class Job0011PreassessmentTests(unittest.TestCase):
    def parse(self):
        return parse_restricted_telegram_fixture(FIXTURE, REPAIR, CORRECTIONS, (LEGACY_ROOT,))

    def test_genuine_fixture_digest_is_validated_before_parsing_and_source_mismatch_blocks(self):
        self.assertEqual(30, len(self.parse().rows))
        with tempfile.TemporaryDirectory() as directory:
            fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
            fixture["fixtures"][0]["content_sha256"] = "0" * 64
            path = Path(directory) / "fixture.json"
            path.write_text(json.dumps(fixture), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "bytes do not match"):
                parse_restricted_telegram_fixture(path, REPAIR, CORRECTIONS, (LEGACY_ROOT,))

    def test_real_format_preserves_names_order_and_numeric_fields(self):
        parsed = self.parse()
        self.assertTrue(parsed.recognized_as_top30)
        self.assertEqual("2023-09-01", parsed.report_date_candidate.isoformat())
        self.assertEqual(list(range(1, 31)), [row.rank for row in parsed.rows])
        self.assertEqual("희림", parsed.rows[0].source_stock_name)
        self.assertEqual("샘씨엔에스", parsed.rows[-1].source_stock_name)
        self.assertEqual("29.94", str(parsed.rows[0].return_pct))
        self.assertEqual(0, parsed.correction_count)
        self.assertEqual(30, sum(row.identity_state == "unresolved" for row in parsed.rows))
        self.assertEqual((), parsed.issues)

    def test_malformed_row_is_explicit_and_cannot_become_valid(self):
        raw_path = Path("D:/Project/stock/data/raw/telegram/daily/2023-09-01_07-36-30_15617.txt")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = raw_path.read_bytes().replace("30. 샘씨엔에스 (10.80%) :".encode(), b"30. malformed")
            local_raw = root / "message.txt"; local_raw.write_bytes(raw)
            digest = hashlib.sha256(raw).hexdigest()
            repair = json.loads(REPAIR.read_text(encoding="utf-8")); repair.pop("repair_record_digest")
            repair["legacy_artifact"]["path"] = str(local_raw); repair["legacy_artifact"]["byte_length"] = len(raw); repair["legacy_artifact"]["sha256"] = digest
            repair["repair_record_digest"] = hashlib.sha256(json.dumps(repair, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            repair_path = root / "repair.json"; repair_path.write_text(json.dumps(repair, ensure_ascii=False), encoding="utf-8")
            fixture = json.loads(FIXTURE.read_text(encoding="utf-8")); item = fixture["fixtures"][0]
            item["raw_reference"] = str(local_raw); item["byte_length"] = len(raw); item["content_sha256"] = digest; item["provenance_repair_digest"] = repair["repair_record_digest"]
            fixture_path = root / "fixture.json"; fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
            parsed = parse_restricted_telegram_fixture(fixture_path, repair_path, CORRECTIONS, (root,))
            self.assertIn("RANK_COUNT_NOT_30:29", parsed.issues)
            self.assertTrue(any(issue.startswith("MALFORMED_ROW") for issue in parsed.issues))

    def test_quarantine_blocks_observation_payload_and_freeze(self):
        parsed = self.parse()
        self.assertEqual(QUARANTINE_STATUS, parsed.quarantine_status)
        for method in (parsed.promote_to_top30_observations, parsed.assessment_payload, parsed.freeze_assessment):
            with self.assertRaises(QuarantineError):
                method()

    def test_digest_is_deterministic_and_binds_source_and_parser_version(self):
        first, second = self.parse(), self.parse()
        self.assertEqual(first.to_json(), second.to_json())
        self.assertEqual(first.representation_digest, second.representation_digest)
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            replace(first, source_content_sha256="a" * 64)
        with self.assertRaisesRegex(ValueError, "parser version"):
            replace(first, parser_version="changed")

    def test_artifact_is_write_once_and_clearly_quarantined(self):
        parsed = self.parse()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "quarantined.json"
            self.assertTrue(write_preassessment_artifact(path, parsed))
            self.assertFalse(write_preassessment_artifact(path, parsed))
            self.assertIn("QUARANTINED / NOT ASSESSMENT ELIGIBLE", path.read_text(encoding="utf-8"))
            with self.assertRaises(FileExistsError):
                write_preassessment_artifact(path, replace(parsed, correction_count=1, representation_digest=""))

    def test_committed_quarantined_artifact_matches_deterministic_parse(self):
        artifact = ROOT / "data/fixtures/job-0011/quarantined/telegram-balanceasset-15617.preassessment.json"
        self.assertEqual(self.parse().to_json() + "\n", artifact.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
