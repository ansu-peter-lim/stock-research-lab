import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.research_contracts.legacy_artifact_inventory import (
    LegacyArtifactAudit,
    PointInTimeClassification,
    audit_current_bytes,
    is_legacy_source_path,
)


class LegacyArtifactInventoryTests(unittest.TestCase):
    def test_legacy_paths_are_explicitly_read_only(self):
        roots = ("D:/Project/stock", "D:/Project/stock-trading-system-reference")
        self.assertTrue(is_legacy_source_path("D:/Project/stock/data/raw/telegram/daily/x.txt", roots))
        self.assertFalse(is_legacy_source_path("D:/Project/research/data/x.txt", roots))
        digest = "a" * 64
        with self.assertRaisesRegex(ValueError, "read_only"):
            LegacyArtifactAudit("D:/Project/stock/x", 1, digest, None, None, False, "unknown",
                                PointInTimeClassification.LOCALLY_PRESERVED_PROVENANCE_LIMITED, "writable")

    def test_current_digest_is_never_labeled_historical_proof(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifact.txt"
            path.write_bytes(b"observed")
            audit = audit_current_bytes(path, stored_digest=None, availability_state="unknown",
                                        classification=PointInTimeClassification.LOCALLY_PRESERVED_PROVENANCE_LIMITED)
        self.assertEqual(hashlib.sha256(b"observed").hexdigest(), audit.current_audit_sha256)
        self.assertFalse(audit.historical_digest_available)
        self.assertEqual("CURRENT_AUDIT_DIGEST", audit.to_dict()["current_audit_digest_kind"])

    def test_missing_availability_and_classification_remain_explicit(self):
        audit = LegacyArtifactAudit("D:/Project/stock/x", 0, "b" * 64, None, None, False, "unknown",
                                    PointInTimeClassification.LOCALLY_PRESERVED_PROVENANCE_LIMITED)
        self.assertEqual("unknown", audit.availability_state)
        self.assertEqual("LOCALLY_PRESERVED_PROVENANCE_LIMITED", audit.to_dict()["point_in_time_classification"])

    def test_stored_digest_validation_is_separate_from_historical_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifact.txt"
            path.write_bytes(b"manifested")
            digest = hashlib.sha256(b"manifested").hexdigest()
            audit = audit_current_bytes(path, stored_digest=digest, availability_state="unknown",
                                        classification=PointInTimeClassification.LOCALLY_PRESERVED_PROVENANCE_LIMITED)
        self.assertTrue(audit.stored_digest_matches_current)
        self.assertFalse(audit.historical_digest_available)

    def test_correction_metadata_is_not_raw_source_metadata(self):
        raw = LegacyArtifactAudit("D:/Project/stock/data/raw/telegram/daily/x.txt", 1, "c" * 64,
                                  None, None, False, "unknown",
                                  PointInTimeClassification.LOCALLY_PRESERVED_PROVENANCE_LIMITED)
        correction = {"registry_path": "D:/Project/stock/data/manual/telegram/top30_corrections.csv",
                      "boundary": "retrospective", "message_id": 1}
        self.assertNotIn("correction", raw.to_dict())
        self.assertEqual("retrospective", correction["boundary"])

    def test_generated_inventory_keeps_corrections_outside_raw_artifacts(self):
        inventory_path = Path(__file__).parents[1] / "data" / "metadata" / "job-0009-legacy-artifact-inventory.json"
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        self.assertTrue(all("correction" not in item for item in inventory["representative_artifacts"]))
        self.assertEqual("retrospective", inventory["correction_layer"]["boundary"])
