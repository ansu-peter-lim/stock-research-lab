import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from src.research_contracts.evidence_admission import (
    ADMISSION_STATUS,
    B_RESTRICTIONS,
    CONFIDENCE_SEMANTICS,
    PROMOTION_DECISION,
    EvidenceAdmissionError,
    ResearchStage,
    admit_preassessment_for_historical_assessment,
    is_admitted,
    write_policy_admission,
)
from src.research_contracts.pre_assessment import (
    QUARANTINE_STATUS,
    QuarantineError,
    parse_restricted_telegram_fixture,
)
from src.research_contracts.telegram_provenance_repair import EvidenceClassification


ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "data/fixtures/job-0010/fixture-manifest.json"
REPAIR = ROOT / "data/metadata/job-0010-telegram-provenance-repair.json"
CORRECTIONS = Path("D:/Project/stock/data/manual/telegram/top30_corrections.csv")
LEGACY_ROOT = Path("D:/Project/stock")


class HistoricalEvidenceAdmissionTests(unittest.TestCase):
    def preassessment(self):
        return parse_restricted_telegram_fixture(FIXTURE, REPAIR, CORRECTIONS, (LEGACY_ROOT,))

    def admission(self):
        return admit_preassessment_for_historical_assessment(self.preassessment(), REPAIR)

    def test_matrix_admits_only_a_and_b_beyond_parsing(self):
        a = EvidenceClassification.A_CUTOFF_VERIFIED
        b = EvidenceClassification.B_SOURCE_VERIFIED_CONTENT_STRONGLY_SUPPORTED
        c = EvidenceClassification.C_SOURCE_VERIFIED_CONTENT_UNCERTAIN
        d = EvidenceClassification.D_LOCAL_ONLY_PROVENANCE
        e = EvidenceClassification.E_CONTRADICTED
        for stage in ResearchStage:
            self.assertTrue(is_admitted(a, stage))
            self.assertTrue(is_admitted(b, stage))
        self.assertTrue(is_admitted(c, ResearchStage.PARSING))
        self.assertTrue(is_admitted(d, ResearchStage.PARSING))
        for evidence_class in (c, d):
            for stage in (ResearchStage.HISTORICAL_ASSESSMENT,
                          ResearchStage.OUTCOME_EVALUATION,
                          ResearchStage.FULL_WALK_FORWARD):
                self.assertFalse(is_admitted(evidence_class, stage))
        for stage in ResearchStage:
            self.assertFalse(is_admitted(e, stage))

    def test_message_15617_is_promoted_only_to_the_explicit_b_assessment_lane(self):
        parsed = self.preassessment()
        admitted = admit_preassessment_for_historical_assessment(parsed, REPAIR)

        self.assertEqual(QUARANTINE_STATUS, parsed.quarantine_status)
        self.assertEqual(PROMOTION_DECISION, admitted.admission_decision)
        self.assertEqual(ADMISSION_STATUS, admitted.admission_status)
        self.assertEqual(ResearchStage.HISTORICAL_ASSESSMENT.value, admitted.admitted_stage)
        self.assertEqual(
            EvidenceClassification.B_SOURCE_VERIFIED_CONTENT_STRONGLY_SUPPORTED.value,
            admitted.evidence_class,
        )
        self.assertEqual("unknown", admitted.historical_availability_state)
        self.assertEqual(CONFIDENCE_SEMANTICS, admitted.confidence_semantics)
        self.assertEqual(B_RESTRICTIONS, admitted.restrictions)
        self.assertEqual(parsed.representation_digest, admitted.source_representation_digest)
        self.assertEqual(30, len(admitted.rows))
        self.assertEqual("unresolved", admitted.identity_state)
        self.assertTrue(all(row.identity_state == "unresolved" for row in admitted.rows))

        # The old strict A-grade paths remain closed; policy admission is not
        # permission to manufacture a Top30Observation or AssessmentPayload.
        for method in (parsed.promote_to_top30_observations,
                       parsed.assessment_payload,
                       parsed.freeze_assessment):
            with self.assertRaises(QuarantineError):
                method()

    def test_admitted_artifact_permanently_carries_limitations_and_cannot_upgrade(self):
        admitted = self.admission()
        artifact = admitted.to_dict()
        self.assertGreater(len(artifact["provenance_limitations"]), 0)
        self.assertEqual("CURRENT_AUDIT_DIGEST", artifact["digest_kind"])
        self.assertEqual("NONE_REPORTED_BY_CURRENT_API", artifact["edit_timestamp_status"])
        self.assertIsNone(artifact["edit_timestamp"])
        self.assertEqual("retrospective", artifact["correction_boundary"])
        self.assertNotIn("outcome", artifact)
        self.assertNotIn("stock_code", artifact)

        with self.assertRaisesRegex(EvidenceAdmissionError, "cannot change or upgrade"):
            replace(admitted, evidence_class=EvidenceClassification.A_CUTOFF_VERIFIED.value,
                    content_digest="")
        with self.assertRaisesRegex(EvidenceAdmissionError, "limitations"):
            replace(admitted, provenance_limitations=(), content_digest="")
        with self.assertRaisesRegex(EvidenceAdmissionError, "historical availability"):
            replace(admitted, historical_availability_state="known", content_digest="")

    def test_gate_rejects_parse_issues_or_retrospective_corrections(self):
        parsed = self.preassessment()
        with self.assertRaisesRegex(EvidenceAdmissionError, "cleanly parsed"):
            admit_preassessment_for_historical_assessment(
                replace(parsed, issues=("MALFORMED_ROW",), representation_digest=""), REPAIR
            )
        with self.assertRaisesRegex(EvidenceAdmissionError, "correction metadata"):
            admit_preassessment_for_historical_assessment(
                replace(parsed, correction_count=1, representation_digest=""), REPAIR
            )

    def test_serialization_is_deterministic_and_write_once(self):
        first, second = self.admission(), self.admission()
        self.assertEqual(first.to_json(), second.to_json())
        self.assertEqual(first.content_digest, second.content_digest)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "admission.json"
            self.assertTrue(write_policy_admission(path, first))
            self.assertFalse(write_policy_admission(path, second))
            changed = replace(first, report_date_candidate="2023-09-02", content_digest="")
            with self.assertRaises(FileExistsError):
                write_policy_admission(path, changed)


if __name__ == "__main__":
    unittest.main()
