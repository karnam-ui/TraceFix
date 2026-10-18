"""Unit tests for incident memory models, eligibility, and repository (Phase 4)."""

from __future__ import annotations

from pathlib import Path

from tracefix.memory.eligibility import EligibilityEvaluator
from tracefix.memory.models import (
    IncidentRecord,
    RootCauseExplanation,
    VerificationEvidence,
)
from tracefix.memory.repository import IncidentMemoryRepository
from tracefix.memory.retrieval_adapter import IncidentMemoryRetrievalAdapter


def _sample_verified_evidence() -> VerificationEvidence:
    return VerificationEvidence(
        status="VERIFIED",
        test_suite="pytest tests/test_calc.py",
        exit_code=0,
        passed_tests=["test_add"],
        failed_tests=[],
        executed_at="2026-10-15T10:00:00Z",
    )


def _sample_failed_evidence() -> VerificationEvidence:
    return VerificationEvidence(
        status="TEST_FAILED",
        test_suite="pytest tests/test_calc.py",
        exit_code=1,
        passed_tests=[],
        failed_tests=["test_add"],
        executed_at="2026-10-15T10:00:00Z",
    )


def test_incident_record_creation() -> None:
    evidence = _sample_verified_evidence()
    record = IncidentRecord.create(
        case_id="psf__requests-1142",
        revision="22623bd8c265b78b161542663ee980738441c307",
        bug_report="requests.get always sends content-length",
        patch_diff="diff --git a/a.py b/a.py\n+fix\n",
        verification_evidence=evidence,
    )
    assert record.incident_id.startswith("inc_")
    assert len(record.patch_hash) == 64
    assert record.lifecycle_status == "VERIFIED"


def test_eligibility_rules() -> None:
    evaluator = EligibilityEvaluator()

    # 1. Verified record is ELIGIBLE
    v_rec = IncidentRecord.create(
        case_id="case1",
        revision="rev1",
        bug_report="bug",
        patch_diff="+fix",
        verification_evidence=_sample_verified_evidence(),
    )
    status, reason = evaluator.evaluate(v_rec)
    assert status == "ELIGIBLE"
    assert reason is None

    # 2. Failed verification is INELIGIBLE
    f_rec = IncidentRecord.create(
        case_id="case2",
        revision="rev1",
        bug_report="bug",
        patch_diff="+bad_fix",
        verification_evidence=_sample_failed_evidence(),
    )
    status, reason = evaluator.evaluate(f_rec)
    assert status == "INELIGIBLE"
    assert "Rule 1 violation" in (reason or "")

    # 3. Model claiming verified=True explanation is rejected
    exp_rec = IncidentRecord.create(
        case_id="case3",
        revision="rev1",
        bug_report="bug",
        patch_diff="+fix",
        verification_evidence=_sample_verified_evidence(),
        root_cause_explanation=RootCauseExplanation(text="Model explanation", verified=True),
    )
    status, reason = evaluator.evaluate(exp_rec)
    assert status == "INELIGIBLE"
    assert "Rule 2 violation" in (reason or "")


def test_chronological_isolation() -> None:
    evaluator = EligibilityEvaluator()
    past_rec = IncidentRecord.create(
        case_id="past",
        revision="rev1",
        bug_report="past bug",
        patch_diff="+fix",
        verification_evidence=_sample_verified_evidence(),
        created_at="2026-01-01T12:00:00Z",
    )
    future_rec = IncidentRecord.create(
        case_id="future",
        revision="rev1",
        bug_report="future bug",
        patch_diff="+fix",
        verification_evidence=_sample_verified_evidence(),
        created_at="2026-06-01T12:00:00Z",
    )

    query_time = "2026-03-01T00:00:00Z"
    assert evaluator.is_chronologically_eligible(past_rec, query_time)
    assert not evaluator.is_chronologically_eligible(future_rec, query_time)


def test_repository_save_and_chronological_query(tmp_path: Path) -> None:
    storage = tmp_path / "incidents.json"
    repo = IncidentMemoryRepository(storage_path=storage)

    rec1 = IncidentRecord.create(
        case_id="case1",
        revision="rev1",
        bug_report="connection adapter sorting issue",
        patch_diff="+adapter_fix",
        verification_evidence=_sample_verified_evidence(),
        created_at="2026-01-10T00:00:00Z",
    )
    rec2 = IncidentRecord.create(
        case_id="case2",
        revision="rev2",
        bug_report="case insensitive dict bug",
        patch_diff="+dict_fix",
        verification_evidence=_sample_verified_evidence(),
        created_at="2026-05-10T00:00:00Z",
    )
    rec_fail = IncidentRecord.create(
        case_id="case_failed",
        revision="rev3",
        bug_report="adapter error",
        patch_diff="+wrong_fix",
        verification_evidence=_sample_failed_evidence(),
        created_at="2026-01-05T00:00:00Z",
    )

    repo.save(rec1)
    repo.save(rec2)
    repo.save(rec_fail)

    # Reload from disk into new repo instance
    repo2 = IncidentMemoryRepository(storage_path=storage)
    assert len(repo2.list_records()) == 3

    # Query as of 2026-02-01: should return rec1 only!
    # (rec2 is in the future; rec_fail is ineligible)
    results = repo2.query_eligible(query_text="adapter", as_of_time="2026-02-01T00:00:00Z")
    assert len(results) == 1
    assert results[0].case_id == "case1"

    # Query negative patterns should return rec_fail
    negatives = repo2.query_negative_patterns()
    assert len(negatives) == 1
    assert negatives[0].case_id == "case_failed"


def test_retrieval_adapter() -> None:
    repo = IncidentMemoryRepository()
    rec = IncidentRecord.create(
        case_id="psf__requests-1142",
        revision="22623bd8c265b78b161542663ee980738441c307",
        bug_report="content length header bug",
        patch_diff="diff --git a/models.py b/models.py\n+fix",
        verification_evidence=_sample_verified_evidence(),
        created_at="2026-01-01T00:00:00Z",
    )
    repo.save(rec)

    adapter = IncidentMemoryRetrievalAdapter(repo)
    ranked = adapter.retrieve_as_ranked_items(
        query_text="content length", as_of_time="2026-02-01T00:00:00Z"
    )
    assert len(ranked) == 1
    assert ranked[0].strategy == "incident_memory"
    assert ranked[0].source == "verified_incident_memory"
    assert ranked[0].provenance == "observed"

    evidence_items = adapter.to_evidence_items([rec])
    assert len(evidence_items) == 1
    assert evidence_items[0]["selection_reason"] == "prior_verified_fix"
    assert evidence_items[0]["evidence_type"] == "incident_memory"
