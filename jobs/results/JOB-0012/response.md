Message 15617 is approved as `PROMOTE_WITH_RESTRICTIONS`.

The new [evidence-admission policy](/D:/Project/research/docs/policies/historical-evidence-admission-policy.md:8) establishes:

- A: admitted through all stages with normal point-in-time controls.
- B: admitted through a separate, permanently labeled B-grade lane.
- C/D: parsing and inventory only.
- E: excluded except isolated forensic inspection.
- Unresolved identities remain in assessment and coverage denominators but cannot receive stock-specific outcomes.
- Retrospective corrections may only enter separately versioned sensitivity analyses after primary artifacts are frozen.

The [policy gate](/D:/Project/research/src/research_contracts/evidence_admission.py:213) preserves Class B, unknown historical availability, inherited limitations, digest lineage, unresolved identities, and write-once semantics. It does not create an A-grade `AssessmentPayload`, fabricate `available_at`, or weaken the existing quarantine and leakage protections.

Validation:

- 45 focused policy, provenance, Top30 contract, and point-in-time leakage tests passed.
- `git diff --check` passed.
- Full suite was not run, per FAST validation.
- No outcome data was added or accessed.
- No commit or push occurred.
- Existing untracked JOB-0012 files were untouched.

Recommended next step: perform a small, outcome-free corpus preflight covering independent evidence classification, report-date coverage, missingness, duplicates, and the frozen assessment-manifest design. Do not begin bulk three-year execution yet.

B_EVIDENCE_ADMITTED_WITH_RESTRICTIONS