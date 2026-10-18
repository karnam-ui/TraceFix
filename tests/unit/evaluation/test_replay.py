"""Unit tests for chronological replay engine and future-leakage prevention (Phase 5)."""

from __future__ import annotations

import pytest

from tracefix.evaluation.cases import CaseRecord
from tracefix.evaluation.replay import (
    ChronologicalReplayEngine,
    ReplayLeakageError,
)
from tracefix.memory.repository import IncidentMemoryRepository
from tracefix.repair.interfaces import ValidationResult, VerificationResultSummary
from tracefix.repair.state_machine import RepairOrchestrator


class MockModelProvider:
    def __init__(self) -> None:
        self.counter = 0

    def generate_patch(self, prompt: str, config: object) -> str:
        self.counter += 1
        return (
            f"diff --git a/f{self.counter}.py b/f{self.counter}.py\n"
            f"--- a/f{self.counter}.py\n"
            f"+++ b/f{self.counter}.py\n"
            f"@@ -1,1 +1,1 @@\n"
            f"-old{self.counter}\n+new{self.counter}\n"
        )


class MockValidator:
    def validate(self, candidate_patch: object, base_revision: str) -> ValidationResult:
        return ValidationResult(is_valid=True)


class MockVerifier:
    def verify(
        self,
        case_id: str,
        base_revision: str,
        patch: str,
        test_suite: dict,
        timeout_seconds: int = 120,
    ) -> VerificationResultSummary:
        return VerificationResultSummary(status="VERIFIED", exit_code=0)


def _make_case(case_id: str, created_at: str, fix_commit: str | None = None) -> CaseRecord:
    return CaseRecord(
        case_id=case_id,
        repo="https://github.com/psf/requests",
        revision=f"rev_{case_id}",
        bug_report=f"Bug report for {case_id}",
        ground_truth_files=["requests/models.py"],
        ground_truth_functions=["requests.models.prepare"],
        localizable=True,
        fix_commit=fix_commit,
        fail_to_pass_tests=["test_foo"],
        created_at=created_at,
    )


def test_sort_cases_chronologically() -> None:
    engine = ChronologicalReplayEngine()
    c3 = _make_case("case3", "2013-05-10T12:00:00Z")
    c1 = _make_case("case1", "2013-01-10T12:00:00Z")
    c2 = _make_case("case2", "2013-03-10T12:00:00Z")

    sorted_cases = engine.sort_cases([c3, c1, c2])
    assert [c.case_id for c in sorted_cases] == ["case1", "case2", "case3"]


def test_sort_cases_missing_timestamp_raises() -> None:
    engine = ChronologicalReplayEngine()
    case = _make_case("c1", "2013-01-01T00:00:00Z")
    case.created_at = None
    with pytest.raises(ValueError, match="lacks created_at timestamp"):
        engine.sort_cases([case])


def test_leakage_guard_detects_fix_commit() -> None:
    engine = ChronologicalReplayEngine()
    case = _make_case("case1", "2013-01-01T00:00:00Z", fix_commit="deadbeef12345678")

    leaked_context = [{"evidence_id": "item1", "revision": "deadbeef12345678"}]
    with pytest.raises(ReplayLeakageError, match="target fix commit"):
        engine.assert_no_leakage(case, leaked_context)


def test_leakage_guard_detects_same_case_memory() -> None:
    engine = ChronologicalReplayEngine()
    case = _make_case("case1", "2013-01-01T00:00:00Z")

    leaked_context = [{"evidence_id": "mem_case1", "symbol": "case1"}]
    with pytest.raises(ReplayLeakageError, match="memory for current case"):
        engine.assert_no_leakage(case, leaked_context)


def test_dynamic_memory_accumulation_across_replay() -> None:
    mem_repo = IncidentMemoryRepository()
    engine = ChronologicalReplayEngine(memory_repository=mem_repo, memory_enabled=True)

    orchestrator = RepairOrchestrator(
        model_provider=MockModelProvider(),
        patch_validator=MockValidator(),
        sandbox_verifier=MockVerifier(),
    )

    c1 = _make_case("psf__requests-1142", "2013-01-25T05:19:16Z")
    c2 = _make_case("psf__requests-1327", "2013-04-25T10:01:49Z")
    c3 = _make_case("psf__requests-1339", "2013-04-30T20:05:30Z")

    # Before replay, 0 memories
    assert len(mem_repo.list_records()) == 0

    summary = engine.run_replay([c1, c2, c3], orchestrator)

    assert summary.total_cases == 3
    assert summary.verified_repairs == 3
    assert summary.memories_accumulated == 3
    assert all(step.leakage_checks_passed for step in summary.step_results)

    # Verify that memory queries are chronologically bounded:
    # As of Feb 2013, only c1 should be eligible
    eligible_feb = mem_repo.query_eligible(as_of_time="2013-02-01T00:00:00Z")
    assert len(eligible_feb) == 1
    assert eligible_feb[0].case_id == "psf__requests-1142"

    # As of May 2013, all 3 are eligible
    eligible_may = mem_repo.query_eligible(as_of_time="2013-05-01T00:00:00Z")
    assert len(eligible_may) == 3


def test_replay_with_memory_disabled_ablation() -> None:
    mem_repo = IncidentMemoryRepository()
    engine = ChronologicalReplayEngine(memory_repository=mem_repo, memory_enabled=False)

    orchestrator = RepairOrchestrator(
        model_provider=MockModelProvider(),
        patch_validator=MockValidator(),
        sandbox_verifier=MockVerifier(),
    )

    c1 = _make_case("case1", "2013-01-01T00:00:00Z")
    summary = engine.run_replay([c1], orchestrator)

    assert summary.verified_repairs == 1
    assert summary.memories_accumulated == 0
    assert len(mem_repo.list_records()) == 0
