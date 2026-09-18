import json
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from src.research_contracts.historical_fixture import (
    AvailabilityState,
    FixtureManifest,
    FixtureManifestEntry,
    FrozenAssessment,
    build_frozen_assessment,
    parse_top30_fixture,
    write_frozen_assessment,
)
from src.research_contracts.top30 import (
    HistoricalIdentityBundle,
    IdentityEvidence,
    IdentityResolution,
    IdentityStatus,
    InformationBoundary,
    Provenance,
    Top30Observation,
)


UTC = timezone.utc
ROOT = Path(__file__).parents[1] / "data" / "fixtures" / "job-0007"
MANIFEST_PATH = ROOT / "fixture-manifest.json"
FROZEN_PATH = ROOT / "frozen" / "job-0007-top30-2024-04-18.json"
FIXTURE_ID = "job-0007-top30-2024-04-18"


class HistoricalFixtureTests(unittest.TestCase):
    def manifest(self) -> FixtureManifest:
        return FixtureManifest.from_json(MANIFEST_PATH.read_text(encoding="utf-8"))

    def pipeline(self):
        manifest = self.manifest()
        observations = parse_top30_fixture(manifest, ROOT, FIXTURE_ID)
        return manifest, observations, build_frozen_assessment(
            manifest, observations, "job-0007-top30-2024-04-18", datetime(2024, 4, 18, 12, tzinfo=UTC)
        )

    def test_raw_fixture_bytes_match_stored_digest_and_manifest_is_deterministic(self):
        manifest = self.manifest()
        manifest.validate_bytes(ROOT)
        self.assertEqual(manifest.to_json(), FixtureManifest.from_json(manifest.to_json()).to_json())
        self.assertEqual(manifest.to_json(), self.manifest().to_json())

    def test_byte_modification_fails_manifest_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            copied = Path(temp) / "fixture"
            shutil.copytree(ROOT, copied)
            raw = copied / "raw" / "top30-2024-04-18.txt"
            raw.write_bytes(raw.read_bytes() + b"x")
            with self.assertRaisesRegex(ValueError, "fixture bytes do not match"):
                self.manifest().validate_bytes(copied)

    def test_provenance_round_trip_and_unknown_availability_are_explicit(self):
        entry = self.manifest().entry(FIXTURE_ID)
        restored = FixtureManifestEntry.from_dict(entry.to_dict())
        self.assertEqual(entry.to_dict(), restored.to_dict())
        unknown = FixtureManifestEntry("unknown", entry.raw_path, entry.byte_length, entry.content_sha256,
                                       "local fixture", None, datetime(2024, 4, 18, tzinfo=UTC),
                                       AvailabilityState.UNKNOWN, None, entry.artifact_type, entry.parser_version)
        self.assertIsNone(unknown.available_at)
        self.assertEqual("unknown", unknown.to_dict()["availability_state"])
        unavailable_manifest = FixtureManifest((unknown,))
        with self.assertRaisesRegex(ValueError, "availability is unknown"):
            parse_top30_fixture(unavailable_manifest, ROOT, "unknown")

    def test_unresolved_identity_survives_full_pipeline(self):
        _, observations, frozen = self.pipeline()
        self.assertEqual(2, len(observations))
        self.assertEqual(1, sum(item.mapping.stock_code is not None for item in observations))
        unresolved = frozen.payloads[1]
        self.assertEqual("Fixture Unresolved Co", unresolved.stock_name)
        self.assertEqual("unresolved", unresolved.mapping_status)
        self.assertIsNone(unresolved.stock_code)

    def test_retrospective_identity_cannot_enter_frozen_assessment(self):
        manifest, observations, _ = self.pipeline()
        observation = observations[1]
        retrospective = IdentityResolution(
            IdentityStatus.RETROSPECTIVE_ENRICHMENT, "005930",
            IdentityEvidence(Provenance("current_master", "current:1", "current.csv", "b" * 64,
                                        datetime(2025, 1, 1, tzinfo=UTC), InformationBoundary.RETROSPECTIVE)),
            "current_master",
        )
        bundle = HistoricalIdentityBundle(observation.stock_name, observation.identity.resolution, (retrospective,))
        later = Top30Observation(observation.observation_date, observation.cutoff_at, observation.rank,
                                 observation.stock_name, observation.source, observation.parser_version,
                                 observation.ingested_at, bundle.assessment_mapping(observation.cutoff_at),
                                 detail_raw=observation.detail_raw, identity=bundle)
        frozen = build_frozen_assessment(manifest, (observations[0], later), "identity-boundary-test",
                                         datetime(2024, 4, 18, 12, tzinfo=UTC))
        self.assertIsNone(frozen.payloads[1].stock_code)
        self.assertNotIn("retrospective", frozen.to_json())

    def test_frozen_serialization_is_deterministic_and_binds_manifest(self):
        manifest, _, frozen = self.pipeline()
        self.assertEqual(frozen.to_json(), FrozenAssessment.from_json(frozen.to_json()).to_json())
        self.assertEqual(frozen.to_json(), FrozenAssessment.from_json(FROZEN_PATH.read_text(encoding="utf-8")).to_json())
        self.assertEqual(manifest.content_digest, frozen.fixture_manifest_digest)
        artifact = json.loads(frozen.to_json())
        forbidden = {"outcome", "future", "ohlcv", "sector_performance", "label", "success"}

        def keys(value):
            if isinstance(value, dict):
                return set(value).union(*(keys(child) for child in value.values()))
            if isinstance(value, list):
                return set().union(*(keys(child) for child in value)) if value else set()
            return set()

        self.assertTrue(forbidden.isdisjoint(keys(artifact)))

    def test_write_once_is_idempotent_and_rejects_different_content(self):
        _, _, frozen = self.pipeline()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "frozen.json"
            self.assertTrue(write_frozen_assessment(path, frozen))
            self.assertFalse(write_frozen_assessment(path, frozen))
            changed = FrozenAssessment(frozen.assessment_id, frozen.fixture_manifest_digest, frozen.cutoff_at,
                                       frozen.payloads, frozen.contract_version,
                                       datetime(2024, 4, 18, 12, 1, tzinfo=UTC))
            with self.assertRaises(FileExistsError):
                write_frozen_assessment(path, changed)


if __name__ == "__main__":
    unittest.main()
