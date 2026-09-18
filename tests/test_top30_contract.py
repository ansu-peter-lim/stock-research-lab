import json
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from src.research_contracts.top30 import (
    AssessmentPayload, InformationBoundary, MappingState, Provenance, RetrospectiveEnrichment,
    Top30Observation,
)


FIXTURE = Path(__file__).parent / "fixtures" / "top30_legacy_row.json"


class Top30ContractTests(unittest.TestCase):
    def observation(self) -> Top30Observation:
        return Top30Observation.from_json(FIXTURE.read_text(encoding="utf-8"))

    def test_valid_observation_preserves_source_name_and_unresolved_code(self):
        observation = self.observation()
        self.assertEqual(observation.stock_name, "삼성전자")
        self.assertEqual(observation.mapping.status, "unresolved")
        self.assertIsNone(observation.mapping.stock_code)
        self.assertEqual(observation.rank, 1)

    def test_retrospective_enrichment_is_separate_from_assessment(self):
        observation = self.observation()
        later_source = Provenance(
            "krx_master", "krx:2026-09-01", "master.csv#삼성전자",
            "b" * 64, datetime(2026, 9, 1, tzinfo=timezone.utc), InformationBoundary.RETROSPECTIVE,
        )
        enriched = observation.with_enrichment(
            RetrospectiveEnrichment("stock_code", "005930", later_source, "later master snapshot")
        )
        self.assertEqual(enriched.enrichments[0].value, "005930")
        payload = AssessmentPayload.from_observation(enriched, observation.cutoff_at)
        self.assertIsNone(payload.stock_code)
        self.assertEqual(payload.mapping_status, "unresolved")

    def test_future_information_is_rejected(self):
        observation = self.observation()
        future_source = Provenance(
            "krx_master", "krx:future", "master.csv#1", "c" * 64,
            datetime(2026, 9, 19, tzinfo=timezone.utc), InformationBoundary.RETROSPECTIVE,
        )
        enriched = observation.with_enrichment(
            RetrospectiveEnrichment("stock_code", "005930", future_source, "future")
        )
        # The later fact is auditable, but cannot enter the cutoff assessment.
        self.assertIsNone(AssessmentPayload.from_observation(enriched, observation.cutoff_at).stock_code)
        with self.assertRaises(ValueError):
            AssessmentPayload.from_observation(observation, datetime(2026, 8, 28, tzinfo=timezone.utc))

    def test_deterministic_serialization_and_provenance_round_trip(self):
        observation = self.observation()
        first = observation.to_json()
        second = Top30Observation.from_json(first).to_json()
        self.assertEqual(first, second)
        decoded = json.loads(second)
        self.assertEqual(decoded["source"]["raw_reference"], "2026-08-29_01-02-03_123.txt#rank=1")
        self.assertEqual(decoded["source"]["content_sha256"], "a" * 64)
        self.assertEqual(Top30Observation.from_json(second).return_pct, Decimal("12.10"))

    def test_confirmed_mapping_requires_cutoff_visible_evidence(self):
        source = self.observation().source
        confirmed = MappingState("point_in_time_confirmed", "005930", source)
        self.assertEqual(confirmed.stock_code, "005930")
        with self.assertRaises(ValueError):
            Top30Observation(self.observation().observation_date, self.observation().cutoff_at, 1,
                             "삼성전자", source, "v", self.observation().ingested_at,
                             MappingState("point_in_time_confirmed", "005930", Provenance(
                                 "krx", "future", "x", "d" * 64,
                                 datetime(2026, 9, 19, tzinfo=timezone.utc))))


if __name__ == "__main__":
    unittest.main()
