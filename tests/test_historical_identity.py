import json
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from src.research_contracts.top30 import (
    AssessmentPayload,
    HistoricalIdentityBundle,
    IdentityEvidence,
    IdentityResolution,
    IdentityStatus,
    MappingState,
    Provenance,
    Top30Observation,
)


UTC = timezone.utc
FIXTURE = Path(__file__).parent / "fixtures" / "historical_identity_bundle.json"


class HistoricalIdentityTests(unittest.TestCase):
    def source(self, available_at: datetime, boundary: str = "point_in_time") -> Provenance:
        return Provenance("official_notice", "notice:1", "notices/1.html", "a" * 64,
                          available_at, boundary)

    def verified(self, available_at: datetime, *, published_at: datetime | None = None) -> IdentityResolution:
        return IdentityResolution(
            IdentityStatus.POINT_IN_TIME_VERIFIED, "005930",
            IdentityEvidence(self.source(available_at), published_at, date(2024, 4, 19), "notice #1"),
            "official_notice_exact_name",
        )

    def observation(self, bundle: HistoricalIdentityBundle, mapping: MappingState) -> Top30Observation:
        cutoff = datetime(2024, 4, 18, 12, tzinfo=UTC)
        source = Provenance("telegram_export", "telegram:1", "raw/1.txt#rank=1", "b" * 64,
                            cutoff, "point_in_time")
        return Top30Observation(date(2024, 4, 18), cutoff, 1, bundle.observed_stock_name,
                                source, "test", cutoff, mapping, identity=bundle)

    def test_identity_known_by_cutoff_can_be_used(self):
        bundle = HistoricalIdentityBundle("Example Historical Name", self.verified(
            datetime(2024, 4, 18, 9, 5, tzinfo=UTC),
            published_at=datetime(2024, 4, 18, 9, tzinfo=UTC),
        ))
        mapping = bundle.assessment_mapping(datetime(2024, 4, 18, 12, tzinfo=UTC))
        self.assertEqual("005930", mapping.stock_code)
        self.assertEqual("point_in_time_confirmed", mapping.status)
        self.assertEqual("official_notice_exact_name", mapping.resolution_method)

    def test_evidence_after_cutoff_cannot_enter_assessment(self):
        bundle = HistoricalIdentityBundle("Example Historical Name", self.verified(
            datetime(2024, 4, 19, 9, tzinfo=UTC),
        ))
        mapping = bundle.assessment_mapping(datetime(2024, 4, 18, 12, tzinfo=UTC))
        self.assertIsNone(mapping.stock_code)
        self.assertEqual("evidence_after_cutoff", mapping.resolution_method)
        observation = self.observation(bundle, mapping)
        self.assertIsNone(AssessmentPayload.from_observation(observation, observation.cutoff_at).stock_code)

    def test_unresolved_historical_identity_is_not_guessed(self):
        bundle = HistoricalIdentityBundle(
            "Unknown Historical Name",
            IdentityResolution(IdentityStatus.UNRESOLVED, resolution_method="no_cutoff_visible_evidence"),
        )
        mapping = bundle.assessment_mapping(datetime(2024, 4, 18, 12, tzinfo=UTC))
        self.assertEqual("unresolved", mapping.status)
        self.assertIsNone(mapping.stock_code)

    def test_retrospective_mapping_is_auditable_but_excluded(self):
        retrospective = IdentityResolution(
            IdentityStatus.RETROSPECTIVE_ENRICHMENT, "005930",
            IdentityEvidence(self.source(datetime(2026, 8, 30, tzinfo=UTC), "retrospective"),
                             reference="current master"),
            "current_master_cross_check",
        )
        bundle = HistoricalIdentityBundle(
            "Example Historical Name",
            IdentityResolution(IdentityStatus.SOURCE_OBSERVED, resolution_method="parsed_top30_name"),
            (retrospective,),
        )
        mapping = bundle.assessment_mapping(datetime(2024, 4, 18, 12, tzinfo=UTC))
        observation = self.observation(bundle, mapping)
        payload = AssessmentPayload.from_observation(observation, observation.cutoff_at)
        self.assertEqual("005930", bundle.retrospective[0].stock_code)
        self.assertIsNone(payload.stock_code)
        self.assertIsNone(payload.identity.evidence)

    def test_publication_and_effective_dates_remain_distinct(self):
        bundle = HistoricalIdentityBundle.from_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))
        evidence = bundle.resolution.evidence
        self.assertEqual(datetime(2024, 4, 18, 9, tzinfo=UTC), evidence.published_at)
        self.assertEqual(date(2024, 4, 19), evidence.effective_date)
        self.assertNotEqual(evidence.published_at.date(), evidence.effective_date)

    def test_provenance_survives_serialization_round_trip(self):
        bundle = HistoricalIdentityBundle.from_dict(json.loads(FIXTURE.read_text(encoding="utf-8")))
        restored = HistoricalIdentityBundle.from_dict(bundle.to_dict())
        self.assertEqual(bundle.to_dict(), restored.to_dict())
        self.assertEqual("notices/example-1.html", restored.resolution.evidence.source.raw_reference)
        self.assertEqual("e" * 64, restored.resolution.evidence.source.content_sha256)

    def test_top30_integration_retains_only_cutoff_visible_identity(self):
        bundle = HistoricalIdentityBundle("Example Historical Name", self.verified(
            datetime(2024, 4, 18, 9, 5, tzinfo=UTC),
            published_at=datetime(2024, 4, 18, 9, tzinfo=UTC),
        ))
        observation = self.observation(bundle, bundle.assessment_mapping(datetime(2024, 4, 18, 12, tzinfo=UTC)))
        restored = Top30Observation.from_json(observation.to_json())
        payload = AssessmentPayload.from_observation(restored, restored.cutoff_at)
        self.assertEqual("005930", payload.stock_code)
        self.assertEqual(date(2024, 4, 19), payload.identity.effective_date)
        self.assertEqual("point_in_time", payload.identity.evidence.boundary.value)


if __name__ == "__main__":
    unittest.main()
