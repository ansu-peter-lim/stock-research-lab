import json
import unittest
from dataclasses import FrozenInstanceError
from datetime import date, datetime, timedelta, timezone

from src.research_contracts.top30 import (
    AssessmentPayload,
    HistoricalIdentityBundle,
    IdentityEvidence,
    IdentityResolution,
    IdentityStatus,
    InformationBoundary,
    MappingState,
    Provenance,
    RetrospectiveEnrichment,
    Top30Observation,
)


UTC = timezone.utc
CUTOFF = datetime(2024, 4, 18, 12, tzinfo=UTC)


class PointInTimeLeakageTests(unittest.TestCase):
    def provenance(
        self,
        available_at: datetime = CUTOFF,
        boundary: InformationBoundary = InformationBoundary.POINT_IN_TIME,
        source_kind: str = "official_notice",
        digest: str = "a" * 64,
    ) -> Provenance:
        return Provenance(
            source_kind,
            f"{source_kind}:1",
            f"raw/{source_kind}-1",
            digest,
            available_at,
            boundary,
        )

    def unresolved_bundle(self, name: str = "Historical Name") -> HistoricalIdentityBundle:
        return HistoricalIdentityBundle(
            name,
            IdentityResolution(
                IdentityStatus.UNRESOLVED,
                resolution_method="no_cutoff_visible_evidence",
            ),
        )

    def verified_bundle(
        self,
        available_at: datetime = CUTOFF,
        *,
        effective_date: date = date(2024, 4, 18),
    ) -> HistoricalIdentityBundle:
        return HistoricalIdentityBundle(
            "Historical Name",
            IdentityResolution(
                IdentityStatus.POINT_IN_TIME_VERIFIED,
                "005930",
                IdentityEvidence(
                    self.provenance(available_at),
                    published_at=min(available_at, CUTOFF),
                    effective_date=effective_date,
                    reference="official notice 1",
                ),
                "official_notice_exact_name",
            ),
        )

    def observation(self, bundle: HistoricalIdentityBundle) -> Top30Observation:
        mapping = bundle.assessment_mapping(CUTOFF)
        return Top30Observation(
            date(2024, 4, 18),
            CUTOFF,
            1,
            bundle.observed_stock_name,
            self.provenance(CUTOFF, source_kind="telegram_export", digest="b" * 64),
            "test-parser-1",
            CUTOFF + timedelta(days=1),
            mapping,
            identity=bundle,
        )

    def test_effective_date_cannot_substitute_for_late_availability(self):
        bundle = self.verified_bundle(
            CUTOFF + timedelta(microseconds=1),
            effective_date=date(2020, 1, 1),
        )
        mapping = bundle.assessment_mapping(CUTOFF)
        self.assertEqual("unresolved", mapping.status)
        self.assertEqual("evidence_after_cutoff", mapping.resolution_method)
        self.assertIsNone(mapping.stock_code)

    def test_publication_before_cutoff_does_not_override_late_availability(self):
        evidence = IdentityEvidence(
            self.provenance(CUTOFF + timedelta(days=1)),
            published_at=CUTOFF - timedelta(days=1),
            effective_date=date(2024, 1, 1),
            reference="notice published earlier but acquired later",
        )
        bundle = HistoricalIdentityBundle(
            "Historical Name",
            IdentityResolution(
                IdentityStatus.POINT_IN_TIME_VERIFIED,
                "005930",
                evidence,
                "official_notice_exact_name",
            ),
        )
        self.assertIsNone(bundle.assessment_mapping(CUTOFF).stock_code)

    def test_cutoff_equality_and_equivalent_timezone_are_inclusive(self):
        korea = timezone(timedelta(hours=9))
        same_instant = datetime(2024, 4, 18, 21, tzinfo=korea)
        bundle = self.verified_bundle(same_instant)
        mapping = bundle.assessment_mapping(CUTOFF)
        self.assertEqual("005930", mapping.stock_code)
        self.assertEqual(CUTOFF, mapping.evidence.available_at)

    def test_naive_and_date_only_availability_are_rejected(self):
        with self.assertRaises(ValueError):
            self.provenance(datetime(2024, 4, 18, 12))
        serialized = self.provenance().to_dict()
        serialized["available_at"] = "2024-04-18"
        with self.assertRaises(ValueError):
            Provenance.from_dict(serialized)

    def test_missing_serialized_boundary_cannot_default_to_point_in_time(self):
        serialized = self.provenance(
            boundary=InformationBoundary.RETROSPECTIVE,
            source_kind="krx_current_master",
        ).to_dict()
        serialized.pop("boundary")
        with self.assertRaisesRegex(ValueError, "boundary is required"):
            Provenance.from_dict(serialized)

    def test_retrospective_source_cannot_masquerade_as_observation_source(self):
        bundle = self.unresolved_bundle()
        with self.assertRaisesRegex(ValueError, "observation source must be point-in-time"):
            Top30Observation(
                date(2024, 4, 18),
                CUTOFF,
                1,
                "Historical Name",
                self.provenance(
                    CUTOFF,
                    InformationBoundary.RETROSPECTIVE,
                    "telegram_export_reconstructed",
                ),
                "test-parser-1",
                CUTOFF,
                bundle.assessment_mapping(CUTOFF),
                identity=bundle,
            )

    def test_confirmed_observation_cannot_bypass_identity_bundle(self):
        mapping = MappingState(
            "point_in_time_confirmed",
            "005930",
            self.provenance(),
            "direct_current_master_lookup",
        )
        with self.assertRaisesRegex(ValueError, "historical identity bundle"):
            Top30Observation(
                date(2024, 4, 18),
                CUTOFF,
                1,
                "Historical Name",
                self.provenance(source_kind="telegram_export", digest="b" * 64),
                "test-parser-1",
                CUTOFF,
                mapping,
            )

    def test_serialized_confirmed_mapping_cannot_drop_bundle(self):
        observation = self.observation(self.verified_bundle())
        serialized = observation.to_dict()
        serialized["identity"] = None
        with self.assertRaisesRegex(ValueError, "historical identity bundle"):
            Top30Observation.from_dict(serialized)

    def test_direct_assessment_cannot_inject_code_without_identity(self):
        with self.assertRaisesRegex(ValueError, "cutoff-selected identity"):
            AssessmentPayload(
                date(2024, 4, 18),
                CUTOFF,
                1,
                "Historical Name",
                "005930",
                self.provenance(source_kind="telegram_export", digest="b" * 64),
                "test-parser-1",
                "point_in_time_confirmed",
                None,
            )

    def test_direct_assessment_rejects_future_identity_evidence(self):
        future_mapping = MappingState(
            "point_in_time_confirmed",
            "005930",
            self.provenance(CUTOFF + timedelta(microseconds=1)),
            "future_notice",
        )
        with self.assertRaisesRegex(ValueError, "identity evidence became available after"):
            AssessmentPayload(
                date(2024, 4, 18),
                CUTOFF,
                1,
                "Historical Name",
                "005930",
                self.provenance(source_kind="telegram_export", digest="b" * 64),
                "test-parser-1",
                "point_in_time_confirmed",
                None,
                identity=future_mapping,
            )

    def test_assessment_rejects_inconsistent_duplicate_identity_fields(self):
        unresolved = MappingState("unresolved", resolution_method="no_evidence")
        with self.assertRaisesRegex(ValueError, "stock_code must equal"):
            AssessmentPayload(
                date(2024, 4, 18),
                CUTOFF,
                1,
                "Historical Name",
                "005930",
                self.provenance(source_kind="telegram_export", digest="b" * 64),
                "test-parser-1",
                "unresolved",
                None,
                identity=unresolved,
            )

    def test_assessment_round_trip_revalidates_and_is_deterministic(self):
        payload = AssessmentPayload.from_observation(
            self.observation(self.verified_bundle()),
            CUTOFF,
        )
        restored = AssessmentPayload.from_json(payload.to_json())
        self.assertEqual(payload, restored)
        self.assertEqual(payload.to_json(), restored.to_json())

        tampered = json.loads(payload.to_json())
        tampered["identity"]["stock_code"] = "000001"
        with self.assertRaisesRegex(ValueError, "stock_code must equal"):
            AssessmentPayload.from_dict(tampered)

    def test_retrospective_primary_resolution_is_rejected(self):
        retrospective = IdentityResolution(
            IdentityStatus.RETROSPECTIVE_ENRICHMENT,
            "005930",
            IdentityEvidence(
                self.provenance(
                    CUTOFF + timedelta(days=1),
                    InformationBoundary.RETROSPECTIVE,
                    "krx_current_master",
                ),
                reference="current master",
            ),
            "current_master_lookup",
        )
        with self.assertRaisesRegex(ValueError, "primary resolution"):
            HistoricalIdentityBundle("Historical Name", retrospective)

    def test_direct_constructor_cannot_backdate_retrospective_enrichment(self):
        bundle = self.unresolved_bundle()
        enrichment = RetrospectiveEnrichment(
            "stock_code",
            "005930",
            self.provenance(
                CUTOFF,
                InformationBoundary.RETROSPECTIVE,
                "krx_current_master",
            ),
            "backdated current master",
        )
        with self.assertRaisesRegex(ValueError, "retrospective to the cutoff"):
            Top30Observation(
                date(2024, 4, 18),
                CUTOFF,
                1,
                "Historical Name",
                self.provenance(source_kind="telegram_export", digest="b" * 64),
                "test-parser-1",
                CUTOFF,
                bundle.assessment_mapping(CUTOFF),
                enrichments=(enrichment,),
                identity=bundle,
            )

    def test_frozen_unresolved_observation_remains_unresolved_at_later_projection(self):
        observation = self.observation(self.unresolved_bundle())
        with self.assertRaises(FrozenInstanceError):
            observation.mapping = self.verified_bundle().assessment_mapping(CUTOFF)
        later_payload = AssessmentPayload.from_observation(
            observation,
            CUTOFF + timedelta(days=365),
        )
        self.assertEqual("unresolved", later_payload.mapping_status)
        self.assertIsNone(later_payload.stock_code)


if __name__ == "__main__":
    unittest.main()
