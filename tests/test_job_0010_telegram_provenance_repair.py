import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.research_contracts.telegram_provenance_repair import (
    AuthorizationStatus,
    ComparisonResult,
    CorrectionLink,
    EditTimestampStatus,
    EvidenceClassification,
    ExternalFixtureReferenceManifest,
    FileFingerprint,
    ProcessedManifestLink,
    ProvenanceRepairRecord,
    assert_unchanged,
    classify_evidence,
    compare_legacy_serialization,
    git_ignores,
    load_processed_manifest_link,
    open_client_with_working_session,
)


UTC = timezone.utc
ROOT = Path(__file__).parents[1]


class TelegramProvenanceRepairTests(unittest.TestCase):
    def fingerprint(self, path: str = "D:/legacy/session.session", data: bytes = b"session"):
        return FileFingerprint(path, len(data), hashlib.sha256(data).hexdigest(), "CURRENT_AUDIT_DIGEST")

    def record(self, *, edit=None, edit_status=EditTimestampStatus.NONE_REPORTED_BY_CURRENT_API):
        source = datetime(2023, 9, 1, 7, 36, 30, tzinfo=UTC)
        retrieval = datetime(2026, 9, 19, 3, 0, tzinfo=UTC)
        raw = b"line one\r\nline two"
        session = self.fingerprint()
        return ProvenanceRepairRecord(
            "JOB-0010-test",
            FileFingerprint("D:/legacy/message.txt", len(raw), hashlib.sha256(raw).hexdigest(),
                            "CURRENT_AUDIT_DIGEST"),
            datetime(2026, 8, 29, tzinfo=UTC),
            ProcessedManifestLink("D:/legacy/manifest.csv", "message.txt", 15617,
                                  hashlib.sha256(raw).hexdigest(), True),
            CorrectionLink("D:/legacy/corrections.csv", 15617, 0),
            session,
            session,
            True,
            AuthorizationStatus.AUTHORIZED,
            15617,
            "telegram:channel_peer_id:-100123:username:balanceasset",
            source,
            edit,
            edit_status,
            retrieval,
            source,
            "CURRENT_MESSAGE_RETURNED",
            compare_legacy_serialization(raw, "line one\nline two"),
            EvidenceClassification.B_SOURCE_VERIFIED_CONTENT_STRONGLY_SUPPORTED,
            "Current content matches; historical byte availability remains unknown.",
            ("None reported by the current API is not proof that no historical edit ever occurred.",),
            True,
            False,
        )

    def test_adapter_opens_only_verified_working_copy_and_cannot_modify_original(self):
        original_bytes = b"SESSION_SECRET_SENTINEL"
        called = {}

        def fake_factory(session_path, api_id, api_hash):
            called["session_path"] = Path(session_path)
            called["api_id"] = api_id
            called["api_hash"] = api_hash
            return object()

        session_root = ROOT / "telegram_sessions"
        session_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=session_root) as working_dir, tempfile.TemporaryDirectory() as source_dir:
            original = Path(source_dir) / "original.session"
            original.write_bytes(original_bytes)
            working = Path(working_dir) / "copy.session"
            client, baseline = open_client_with_working_session(
                fake_factory, original, working, ROOT, 123, "runtime-only-secret"
            )
            self.assertIsNotNone(client)
            self.assertEqual(working.resolve(), called["session_path"])
            self.assertNotEqual(original.resolve(), called["session_path"])
            self.assertEqual(original_bytes, original.read_bytes())
            assert_unchanged(baseline, FileFingerprint.current_audit(original))

    def test_working_session_paths_are_git_ignored(self):
        for path in (
            ROOT / "telegram_sessions/job-0010/telegram_test.session",
            ROOT / "telegram_sessions/job-0010/telegram_test.session-journal",
        ):
            self.assertTrue(git_ignores(path, ROOT), path)

    def test_original_session_size_or_hash_mutation_is_detected(self):
        before = self.fingerprint(data=b"before")
        changed_size = self.fingerprint(data=b"after-longer")
        with self.assertRaisesRegex(RuntimeError, "HIGH"):
            assert_unchanged(before, changed_size)
        changed_hash = FileFingerprint(before.path, before.byte_length, hashlib.sha256(b"xxxxxx").hexdigest(),
                                       "CURRENT_AUDIT_DIGEST")
        with self.assertRaisesRegex(RuntimeError, "HIGH"):
            assert_unchanged(before, changed_hash)

    def test_credentials_and_session_contents_are_not_persisted(self):
        serialized = self.record().to_json()
        self.assertNotIn("SESSION_SECRET_SENTINEL", serialized)
        self.assertNotIn("runtime-only-secret", serialized)
        self.assertNotIn("TELEGRAM_API_HASH", serialized)
        self.assertNotIn("TELEGRAM_API_ID", serialized)

    def test_legacy_raw_digest_is_deterministic_and_manifest_link_is_validated(self):
        raw = b"legacy bytes"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "message.txt"
            artifact.write_bytes(raw)
            fingerprint = FileFingerprint.current_audit(artifact)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), fingerprint.sha256)
            manifest = root / "manifest.csv"
            manifest.write_text(
                "telegram_message_id,source_file,content_sha256\n"
                f"15617,message.txt,{fingerprint.sha256}\n",
                encoding="utf-8",
            )
            link = load_processed_manifest_link(manifest, 15617, fingerprint)
            self.assertTrue(link.current_audit_hash_matches)
            self.assertIn("NOT_ACQUISITION_TIME", link.digest_semantics)

    def test_source_message_identity_and_distinct_timestamps_are_explicit(self):
        data = self.record().to_dict()
        self.assertEqual(15617, data["telegram_message_id"])
        self.assertIn("channel_peer_id", data["telegram_source_identifier"])
        self.assertNotEqual(data["source_timestamp"], data["retrieval_timestamp"])
        self.assertNotEqual(data["legacy_file_timestamp"], data["retrieval_timestamp"])
        self.assertEqual(data["source_timestamp"], data["intended_cutoff"])

    def test_no_edit_and_unknown_edit_semantics_are_not_overstated(self):
        no_edit = self.record().to_dict()
        self.assertIsNone(no_edit["edit_timestamp"])
        self.assertEqual("NONE_REPORTED_BY_CURRENT_API", no_edit["edit_timestamp_status"])
        self.assertTrue(any("not proof" in item for item in no_edit["provenance_limitations"]))
        with self.assertRaisesRegex(ValueError, "allowed only"):
            self.record(edit=datetime(2023, 9, 1, 8, tzinfo=UTC),
                        edit_status=EditTimestampStatus.UNKNOWN_NOT_RETRIEVED)

    def test_comparison_levels_and_transformations_are_explicit(self):
        evidence = compare_legacy_serialization(b"a\r\nb", "a\nb")
        data = evidence.to_dict()
        self.assertEqual(ComparisonResult.CANONICAL_MATCH, evidence.result)
        self.assertEqual(
            {"RAW_FILE_BYTES", "LEGACY_SERIALIZED_MESSAGE_CONTENT", "CURRENT_TELEGRAM_MESSAGE_CONTENT"},
            set(data["levels"]),
        )
        self.assertTrue(any("CRLF" in item for item in data["transformations"]))
        self.assertTrue(any("No BOM" in item for item in data["transformations"]))

    def test_undocumented_normalization_cannot_turn_mismatch_into_match(self):
        evidence = compare_legacy_serialization(b"a b", "ab")
        self.assertEqual(ComparisonResult.MISMATCH, evidence.result)
        self.assertNotIn("whitespace collapse", " ".join(evidence.transformations).lower())
        classification = classify_evidence(
            authorized=True,
            identity_verified=True,
            metadata_conflict=False,
            comparison=evidence.result,
            edit_after_cutoff=False,
        )
        self.assertEqual(EvidenceClassification.E_CONTRADICTED, classification)

    def test_repaired_classification_is_explicit_and_current_api_cannot_create_class_a(self):
        classification = classify_evidence(
            authorized=True,
            identity_verified=True,
            metadata_conflict=False,
            comparison=ComparisonResult.CANONICAL_MATCH,
            edit_after_cutoff=False,
        )
        self.assertEqual(EvidenceClassification.B_SOURCE_VERIFIED_CONTENT_STRONGLY_SUPPORTED, classification)
        self.assertEqual(classification.value, self.record().to_dict()["evidence_classification"])

    def test_current_audit_digest_cannot_masquerade_as_acquisition_time_digest(self):
        with self.assertRaisesRegex(ValueError, "cannot imply"):
            FileFingerprint("D:/legacy/x", 1, "a" * 64, "ACQUISITION_TIME_DIGEST")
        data = self.record().to_dict()
        self.assertEqual("CURRENT_AUDIT_DIGEST", data["legacy_artifact"]["digest_kind"])
        self.assertFalse(data["assessment_payload_allowed"])

    def test_retrospective_correction_remains_separate_from_raw_and_fixture(self):
        record = self.record()
        data = record.to_dict()
        self.assertEqual("retrospective", data["correction"]["boundary"])
        self.assertFalse(data["correction"]["raw_content_modified"])
        fixture = ExternalFixtureReferenceManifest(
            "telegram-balanceasset-15617",
            record.legacy_artifact.path,
            record.legacy_artifact.byte_length,
            record.legacy_artifact.sha256,
            "data/metadata/job-0010.json",
            record.repair_record_digest,
            record.telegram_source_identifier,
            15617,
            record.source_timestamp,
            record.edit_timestamp,
            record.edit_timestamp_status,
            record.retrieval_timestamp,
        )
        fixture_data = json.loads(fixture.to_json())["fixtures"][0]
        self.assertNotIn("correction", fixture_data)
        self.assertEqual("unknown", fixture_data["availability_state"])
        self.assertFalse(fixture_data["assessment_permitted"])

    def test_generated_record_and_fixture_are_digest_bound_and_secret_free(self):
        repair_path = ROOT / "data/metadata/job-0010-telegram-provenance-repair.json"
        fixture_path = ROOT / "data/fixtures/job-0010/fixture-manifest.json"
        if not repair_path.exists():
            self.skipTest("network acquisition artifact is not present")
        raw = repair_path.read_bytes()
        repair = json.loads(raw)
        stored_digest = repair.pop("repair_record_digest")
        canonical = json.dumps(repair, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.assertEqual(stored_digest, hashlib.sha256(canonical.encode("utf-8")).hexdigest())
        self.assertTrue(repair["original_session_mutation_check"]["unchanged"])
        self.assertFalse(repair["assessment_payload_allowed"])
        for marker in (b"TELEGRAM_API_ID", b"TELEGRAM_API_HASH", b"SESSION_SECRET_SENTINEL"):
            self.assertNotIn(marker, raw)

        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))["fixtures"][0]
        self.assertEqual(stored_digest, fixture["provenance_repair_digest"])
        self.assertEqual("unknown", fixture["availability_state"])
        self.assertFalse(fixture["assessment_permitted"])


if __name__ == "__main__":
    unittest.main()
