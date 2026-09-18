"""Explicit policy gate for historical source-evidence admission.

The strict :mod:`top30` contracts continue to represent cutoff-verified
evidence.  This module provides a separate lane for policy-admitted Class B
source content without inventing historical availability or upgrading it to
Class A.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from .pre_assessment import PreAssessmentRow, PreAssessmentTop30, QUARANTINE_STATUS
from .telegram_provenance_repair import EvidenceClassification


POLICY_VERSION = "historical-evidence-admission-policy-1"
ADMISSION_SCHEMA_VERSION = "policy-admitted-historical-assessment-input-1"
PROMOTION_DECISION = "PROMOTE_WITH_RESTRICTIONS"
ADMISSION_STATUS = "ADMITTED_FOR_HISTORICAL_ASSESSMENT_WITH_RESTRICTIONS"
CONFIDENCE_SEMANTICS = (
    "strong source/content support; historical cutoff availability is not verified; "
    "this is an ordinal evidence label, not a probability"
)


class ResearchStage(StrEnum):
    PARSING = "parsing"
    HISTORICAL_ASSESSMENT = "historical_assessment"
    OUTCOME_EVALUATION = "outcome_evaluation"
    FULL_WALK_FORWARD = "full_three_year_walk_forward"


# Whether evidence of each class may pass the named source-evidence stage.
# Later stages still have independent identity, freeze, outcome-data, and
# corpus-completeness gates described by the policy document.
ADMISSION_MATRIX: dict[EvidenceClassification, dict[ResearchStage, bool]] = {
    EvidenceClassification.A_CUTOFF_VERIFIED: {
        ResearchStage.PARSING: True,
        ResearchStage.HISTORICAL_ASSESSMENT: True,
        ResearchStage.OUTCOME_EVALUATION: True,
        ResearchStage.FULL_WALK_FORWARD: True,
    },
    EvidenceClassification.B_SOURCE_VERIFIED_CONTENT_STRONGLY_SUPPORTED: {
        ResearchStage.PARSING: True,
        ResearchStage.HISTORICAL_ASSESSMENT: True,
        ResearchStage.OUTCOME_EVALUATION: True,
        ResearchStage.FULL_WALK_FORWARD: True,
    },
    EvidenceClassification.C_SOURCE_VERIFIED_CONTENT_UNCERTAIN: {
        ResearchStage.PARSING: True,
        ResearchStage.HISTORICAL_ASSESSMENT: False,
        ResearchStage.OUTCOME_EVALUATION: False,
        ResearchStage.FULL_WALK_FORWARD: False,
    },
    EvidenceClassification.D_LOCAL_ONLY_PROVENANCE: {
        ResearchStage.PARSING: True,
        ResearchStage.HISTORICAL_ASSESSMENT: False,
        ResearchStage.OUTCOME_EVALUATION: False,
        ResearchStage.FULL_WALK_FORWARD: False,
    },
    EvidenceClassification.E_CONTRADICTED: {
        ResearchStage.PARSING: False,
        ResearchStage.HISTORICAL_ASSESSMENT: False,
        ResearchStage.OUTCOME_EVALUATION: False,
        ResearchStage.FULL_WALK_FORWARD: False,
    },
}


B_RESTRICTIONS = (
    "evidence_class must remain B_SOURCE_VERIFIED_CONTENT_STRONGLY_SUPPORTED in every descendant",
    "historical availability must remain unknown and no synthetic available_at may be created",
    "Class B must be stored, analyzed, and reported as a separate evidence stratum from Class A",
    "the assessment input must be frozen before any outcome data are accessed or joined",
    "unresolved identities must remain in coverage denominators and cannot receive stock-specific outcomes",
    "retrospective corrections and identity enrichments cannot alter the primary frozen assessment",
    "full walk-forward use additionally requires a predeclared corpus coverage and missingness audit",
)


class EvidenceAdmissionError(ValueError):
    """Raised when evidence does not satisfy the selected admission lane."""


def _canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def is_admitted(evidence_class: EvidenceClassification | str, stage: ResearchStage | str) -> bool:
    """Return the policy matrix decision without bypassing stage-specific gates."""
    return ADMISSION_MATRIX[EvidenceClassification(evidence_class)][ResearchStage(stage)]


@dataclass(frozen=True)
class PolicyAdmittedAssessmentInput:
    """Class-B assessment input that permanently retains its weaker evidence semantics."""

    source_representation_digest: str
    source_fixture_manifest_digest: str
    source_content_sha256: str
    provenance_repair_record: str
    provenance_repair_digest: str
    evidence_class: str
    confidence_semantics: str
    historical_availability_state: str
    historical_availability_interpretation: str
    provenance_limitations: tuple[str, ...]
    telegram_message_id: int
    source_timestamp: str
    edit_timestamp: str | None
    edit_timestamp_status: str
    retrieval_timestamp: str
    digest_kind: str
    parser_version: str
    report_date_candidate: str | None
    recognized_as_top30: bool
    rows: tuple[PreAssessmentRow, ...]
    issues: tuple[str, ...]
    correction_count: int
    correction_boundary: str
    identity_state: str
    admission_status: str = ADMISSION_STATUS
    admission_decision: str = PROMOTION_DECISION
    admitted_stage: str = ResearchStage.HISTORICAL_ASSESSMENT.value
    restrictions: tuple[str, ...] = B_RESTRICTIONS
    policy_version: str = POLICY_VERSION
    schema_version: str = ADMISSION_SCHEMA_VERSION
    content_digest: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != ADMISSION_SCHEMA_VERSION or self.policy_version != POLICY_VERSION:
            raise EvidenceAdmissionError("unsupported evidence-admission schema or policy version")
        if self.evidence_class != EvidenceClassification.B_SOURCE_VERIFIED_CONTENT_STRONGLY_SUPPORTED.value:
            raise EvidenceAdmissionError("the Class B lane cannot change or upgrade evidence_class")
        if self.confidence_semantics != CONFIDENCE_SEMANTICS:
            raise EvidenceAdmissionError("Class B confidence semantics must remain explicit")
        if self.historical_availability_state != "unknown":
            raise EvidenceAdmissionError("Class B admission cannot claim verified historical availability")
        if self.admission_decision != PROMOTION_DECISION or self.admission_status != ADMISSION_STATUS:
            raise EvidenceAdmissionError("Class B admission requires the restricted promotion decision")
        if self.admitted_stage != ResearchStage.HISTORICAL_ASSESSMENT.value:
            raise EvidenceAdmissionError("this gate admits only historical assessment input")
        if self.restrictions != B_RESTRICTIONS or not self.provenance_limitations:
            raise EvidenceAdmissionError("all Class B restrictions and source limitations are permanent")
        if self.digest_kind != "CURRENT_AUDIT_DIGEST":
            raise EvidenceAdmissionError("a current audit digest cannot be relabeled as historical")
        if not self.recognized_as_top30 or self.issues:
            raise EvidenceAdmissionError("only a cleanly parsed Top30 source may enter assessment")
        if len(self.rows) != 30 or {row.rank for row in self.rows} != set(range(1, 31)):
            raise EvidenceAdmissionError("Top30 assessment input requires ranks 1 through 30 exactly once")
        if any(row.identity_state != "unresolved" for row in self.rows):
            raise EvidenceAdmissionError("this gate cannot resolve stock identities")
        if self.identity_state != "unresolved" or self.correction_count != 0:
            raise EvidenceAdmissionError("identity and retrospective corrections must remain outside this gate")
        if self.correction_boundary != "retrospective":
            raise EvidenceAdmissionError("correction boundary must remain retrospective")
        computed = _digest(self._content_dict())
        if self.content_digest and self.content_digest != computed:
            raise EvidenceAdmissionError("policy-admitted assessment input digest mismatch")
        object.__setattr__(self, "content_digest", computed)

    def _content_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "policy_version": self.policy_version,
            "admission_status": self.admission_status,
            "admission_decision": self.admission_decision,
            "admitted_stage": self.admitted_stage,
            "source_representation_digest": self.source_representation_digest,
            "source_fixture_manifest_digest": self.source_fixture_manifest_digest,
            "source_content_sha256": self.source_content_sha256,
            "provenance_repair_record": self.provenance_repair_record,
            "provenance_repair_digest": self.provenance_repair_digest,
            "evidence_class": self.evidence_class,
            "confidence_semantics": self.confidence_semantics,
            "historical_availability_state": self.historical_availability_state,
            "historical_availability_interpretation": self.historical_availability_interpretation,
            "provenance_limitations": list(self.provenance_limitations),
            "telegram_message_id": self.telegram_message_id,
            "source_timestamp": self.source_timestamp,
            "edit_timestamp": self.edit_timestamp,
            "edit_timestamp_status": self.edit_timestamp_status,
            "retrieval_timestamp": self.retrieval_timestamp,
            "digest_kind": self.digest_kind,
            "parser_version": self.parser_version,
            "report_date_candidate": self.report_date_candidate,
            "recognized_as_top30": self.recognized_as_top30,
            "rows": [row.to_dict() for row in self.rows],
            "issues": list(self.issues),
            "correction_count": self.correction_count,
            "correction_boundary": self.correction_boundary,
            "identity_state": self.identity_state,
            "restrictions": list(self.restrictions),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._content_dict(), "content_digest": self.content_digest}

    def to_json(self) -> str:
        return _canonical_json(self.to_dict())


def admit_preassessment_for_historical_assessment(
    parsed: PreAssessmentTop30, repair_record_path: Path,
) -> PolicyAdmittedAssessmentInput:
    """Admit a clean Class-B pre-assessment through the explicit policy lane.

    The source object remains quarantined and unchanged.  The returned object
    is a new, digest-bound assessment input, not an A-grade ``AssessmentPayload``.
    """
    evidence_class = EvidenceClassification(parsed.provenance_classification)
    if not is_admitted(evidence_class, ResearchStage.HISTORICAL_ASSESSMENT):
        raise EvidenceAdmissionError(f"{evidence_class.value} is not admitted for historical assessment")
    if evidence_class is not EvidenceClassification.B_SOURCE_VERIFIED_CONTENT_STRONGLY_SUPPORTED:
        raise EvidenceAdmissionError("this explicit gate is only for Class B pre-assessment evidence")
    if parsed.quarantine_status != QUARANTINE_STATUS or parsed.availability_state != "unknown":
        raise EvidenceAdmissionError("the source pre-assessment must retain its original quarantine metadata")

    repair = json.loads(repair_record_path.read_text(encoding="utf-8"))
    stored_digest = repair.pop("repair_record_digest", None)
    if not stored_digest or _digest(repair) != stored_digest:
        raise EvidenceAdmissionError("provenance repair record digest mismatch")
    if stored_digest != parsed.provenance_repair_digest:
        raise EvidenceAdmissionError("pre-assessment is not bound to this provenance repair record")
    if repair.get("evidence_classification") != evidence_class.value:
        raise EvidenceAdmissionError("repair and pre-assessment evidence classes differ")
    if repair.get("telegram_message_id") != parsed.telegram_message_id:
        raise EvidenceAdmissionError("repair and pre-assessment message identities differ")
    if repair.get("source_timestamp") != parsed.source_timestamp.isoformat(timespec="microseconds").replace("+00:00", "Z"):
        raise EvidenceAdmissionError("repair and pre-assessment source timestamps differ")
    if repair.get("assessment_payload_allowed") is not False:
        raise EvidenceAdmissionError("Class B must not masquerade as strict AssessmentPayload eligibility")

    legacy = repair.get("legacy_artifact", {})
    correction = repair.get("correction", {})
    if legacy.get("sha256") != parsed.source_content_sha256:
        raise EvidenceAdmissionError("repair and pre-assessment source digests differ")
    if correction.get("entries_found") != parsed.correction_count or correction.get("raw_content_modified"):
        raise EvidenceAdmissionError("retrospective correction metadata does not match the source")

    return PolicyAdmittedAssessmentInput(
        source_representation_digest=parsed.representation_digest,
        source_fixture_manifest_digest=parsed.source_fixture_manifest_digest,
        source_content_sha256=parsed.source_content_sha256,
        provenance_repair_record=parsed.provenance_repair_record,
        provenance_repair_digest=parsed.provenance_repair_digest,
        evidence_class=evidence_class.value,
        confidence_semantics=CONFIDENCE_SEMANTICS,
        historical_availability_state=parsed.availability_state,
        historical_availability_interpretation=repair["historical_availability"],
        provenance_limitations=tuple(repair["provenance_limitations"]),
        telegram_message_id=parsed.telegram_message_id,
        source_timestamp=repair["source_timestamp"],
        edit_timestamp=repair.get("edit_timestamp"),
        edit_timestamp_status=repair["edit_timestamp_status"],
        retrieval_timestamp=repair["retrieval_timestamp"],
        digest_kind=legacy["digest_kind"],
        parser_version=parsed.parser_version,
        report_date_candidate=(parsed.report_date_candidate.isoformat()
                               if parsed.report_date_candidate else None),
        recognized_as_top30=parsed.recognized_as_top30,
        rows=parsed.rows,
        issues=parsed.issues,
        correction_count=parsed.correction_count,
        correction_boundary=correction["boundary"],
        identity_state="unresolved",
    )


def write_policy_admission(path: Path, admission: PolicyAdmittedAssessmentInput) -> bool:
    """Write once; refuse to replace a different evidence-admission artifact."""
    content = (admission.to_json() + "\n").encode("utf-8")
    if path.exists():
        if path.read_bytes() == content:
            return False
        raise FileExistsError(f"refusing to overwrite policy admission artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(content)
    return True
