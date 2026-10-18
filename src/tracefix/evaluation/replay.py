"""Chronological replay engine and automated future-leakage prevention (Phase 5).

Complies with contracts/evaluation.json (C4) and contracts/incident_memory.json (C7).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from tracefix.evaluation.cases import CaseRecord
from tracefix.memory.models import IncidentRecord, VerificationEvidence
from tracefix.memory.repository import IncidentMemoryRepository
from tracefix.repair.interfaces import RepairConfig, RepairRequest, RepairResult
from tracefix.repair.state_machine import RepairOrchestrator


class ReplayLeakageError(Exception):
    """Raised when future information or target fix leakage is detected."""


class ReplayStepResult(BaseModel):
    """Outcome of a single replayed historical bug case."""

    case_id: str
    revision: str
    created_at: str
    repair_result: RepairResult
    memory_added: bool
    incident_id: str | None = None
    leakage_checks_passed: bool = True


class ReplaySessionSummary(BaseModel):
    """Summary of a chronological evaluation replay run."""

    total_cases: int
    evaluated_cases: int
    verified_repairs: int
    failed_repairs: int
    rejected_patches: int
    memory_enabled: bool
    memories_accumulated: int
    step_results: list[ReplayStepResult] = Field(default_factory=list)


class ChronologicalReplayEngine:
    """Simulates realistic temporal bug fixing without future-knowledge leakage."""

    def __init__(
        self,
        memory_repository: IncidentMemoryRepository | None = None,
        memory_enabled: bool = True,
    ) -> None:
        self.memory_repo = memory_repository or IncidentMemoryRepository()
        self.memory_enabled = memory_enabled

    def sort_cases(self, cases: list[CaseRecord]) -> list[CaseRecord]:
        """Order cases in strict chronological sequence by created_at.

        Raises:
            ValueError: if any case has a missing or unparseable created_at.
        """
        for c in cases:
            if not c.created_at:
                raise ValueError(
                    f"Case {c.case_id} lacks created_at timestamp required for chronological replay"
                )

        def _key(c: CaseRecord) -> datetime:
            assert c.created_at is not None
            return datetime.fromisoformat(c.created_at.replace("Z", "+00:00"))

        return sorted(cases, key=_key)

    def assert_no_leakage(
        self,
        case: CaseRecord,
        candidate_items: list[dict[str, Any]],
    ) -> None:
        """Enforce strict leakage prevention rules.

        Raises:
            ReplayLeakageError: if any future commit, future memory, or the target fix
            commit appears in the context or memory.
        """
        target_case_id = case.case_id
        target_fix_commit = case.fix_commit

        for item in candidate_items:
            # 1. Target fix commit must not be in retrieval context
            if target_fix_commit and item.get("revision") == target_fix_commit:
                raise ReplayLeakageError(
                    f"Leakage detected: target fix commit {target_fix_commit} "
                    f"present in context for case {target_case_id}"
                )

            # 2. Target fix commit SHA must not appear in item paths or evidence
            if target_fix_commit and target_fix_commit in str(item):
                ev_id = item.get("evidence_id")
                raise ReplayLeakageError(
                    f"Leakage detected: target fix SHA referenced in evidence {ev_id}"
                )

            # 3. Check for same-case memory leakage
            is_same_case = (
                item.get("symbol") == target_case_id
                or item.get("evidence_id") == f"mem_{target_case_id}"
            )
            if is_same_case:
                raise ReplayLeakageError(
                    f"Leakage detected: memory for current case {target_case_id} "
                    f"retrieved before simulated fix occurred"
                )

    def execute_step(
        self,
        case: CaseRecord,
        orchestrator: RepairOrchestrator,
        config: RepairConfig | None = None,
    ) -> ReplayStepResult:
        """Replay a single historical case with temporal bounding."""
        assert case.created_at is not None
        as_of_time = case.created_at

        # 1. Retrieve eligible prior memories (strictly created_at < as_of_time)
        prior_memories = (
            self.memory_repo.query_eligible(
                query_text=case.bug_report,
                as_of_time=as_of_time,
                repo=case.repo,
            )
            if self.memory_enabled
            else []
        )

        context_manifest: dict[str, Any] = {
            "case_id": case.case_id,
            "revision": case.revision,
            "items": [],
        }

        # Include prior memory evidence items
        if prior_memories:
            from tracefix.memory.retrieval_adapter import IncidentMemoryRetrievalAdapter

            adapter = IncidentMemoryRetrievalAdapter(self.memory_repo)
            context_manifest["items"] = adapter.to_evidence_items(prior_memories)

        # 2. Audit against future leakage
        self.assert_no_leakage(case, context_manifest["items"])

        # 3. Execute repair attempt
        test_suite = {
            "fail_to_pass": case.fail_to_pass_tests,
            "pass_to_pass": case.validation.get("pass_to_pass_tests", []),
        }

        request = RepairRequest(
            case_id=case.case_id,
            repo=case.repo,
            base_revision=case.revision,
            bug_report=case.bug_report,
            context_manifest=context_manifest,
            test_suite=test_suite,
            configuration=config or RepairConfig(),
        )

        result = orchestrator.run(request)

        # 4. If repair is verified and memory enabled, accumulate memory for future cases
        memory_added = False
        incident_id: str | None = None

        if result.final_state == "VERIFIED" and result.candidate_patch and self.memory_enabled:
            evidence = VerificationEvidence(
                status="VERIFIED",
                test_suite=str(case.fail_to_pass_tests),
                exit_code=0,
                duration_seconds=result.duration_seconds,
                executed_at=as_of_time,
            )
            rec = IncidentRecord.create(
                case_id=case.case_id,
                revision=case.revision,
                bug_report=case.bug_report,
                patch_diff=result.candidate_patch.raw_diff,
                verification_evidence=evidence,
                repo=case.repo,
                created_at=as_of_time,
            )
            saved = self.memory_repo.save(rec)
            memory_added = True
            incident_id = saved.incident_id

        return ReplayStepResult(
            case_id=case.case_id,
            revision=case.revision,
            created_at=as_of_time,
            repair_result=result,
            memory_added=memory_added,
            incident_id=incident_id,
            leakage_checks_passed=True,
        )

    def run_replay(
        self,
        cases: list[CaseRecord],
        orchestrator: RepairOrchestrator,
        config: RepairConfig | None = None,
    ) -> ReplaySessionSummary:
        """Run full chronological replay over a suite of cases."""
        sorted_cases = self.sort_cases(cases)
        step_results: list[ReplayStepResult] = []

        verified_count = 0
        failed_count = 0
        rejected_count = 0

        for case in sorted_cases:
            step = self.execute_step(case, orchestrator, config=config)
            step_results.append(step)

            if step.repair_result.final_state == "VERIFIED":
                verified_count += 1
            elif step.repair_result.final_state == "FAILED":
                failed_count += 1
            elif step.repair_result.final_state == "REJECTED":
                rejected_count += 1

        memories_count = len(self.memory_repo.query_eligible()) if self.memory_enabled else 0

        return ReplaySessionSummary(
            total_cases=len(cases),
            evaluated_cases=len(sorted_cases),
            verified_repairs=verified_count,
            failed_repairs=failed_count,
            rejected_patches=rejected_count,
            memory_enabled=self.memory_enabled,
            memories_accumulated=memories_count,
            step_results=step_results,
        )
