"""Unit tests for MultiArmExperimentRunner (B6.1)."""

from __future__ import annotations

from typing import Any

from tracefix.evaluation.cases import CaseRecord
from tracefix.evaluation.experiment_runner import (
    ExperimentArm,
    MultiArmExperimentRunner,
    provisional_relevance,
)
from tracefix.evaluation.metrics import MetricsConfig
from tracefix.graph.models import Provenance
from tracefix.memory.repository import IncidentMemoryRepository
from tracefix.repair.interfaces import VerificationResultSummary
from tracefix.repair.state_machine import RepairOrchestrator
from tracefix.retrieval.interfaces import (
    EvidenceTarget,
    RankedItem,
    RetrievalQuery,
    RetrievalResult,
)


class StubSandboxVerifier:
    def __init__(self, status: str = "VERIFIED") -> None:
        self.status = status

    def verify(
        self,
        case_id: str,
        base_revision: str,
        patch: str,
        test_suite: dict[str, Any],
        timeout_seconds: int = 120,
    ) -> VerificationResultSummary:
        return VerificationResultSummary(
            status=self.status,
            exit_code=0 if self.status == "VERIFIED" else 1,
            passed_tests=["tests/test_api.py::test_fix"] if self.status == "VERIFIED" else [],
            failed_tests=[] if self.status == "VERIFIED" else ["tests/test_api.py::test_fix"],
            duration_seconds=1.0,
        )


class StubRetrievalStrategy:
    """Deterministic stub strategy for testing retrieval arms."""

    def __init__(self, name: str, relevant_symbol: str) -> None:
        self.name = name
        self.relevant_symbol = relevant_symbol

    def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        items = [
            RankedItem(
                evidence_id=f"{self.name}_1",
                strategy=self.name,
                rank=1,
                score=0.95,
                target=EvidenceTarget(file="requests/api.py", symbol=self.relevant_symbol),
                source_revision=query.revision,
                provenance=Provenance.OBSERVED,
                source="stub",
            ),
            RankedItem(
                evidence_id=f"{self.name}_2",
                strategy=self.name,
                rank=2,
                score=0.80,
                target=EvidenceTarget(file="requests/models.py", symbol="unrelated_func"),
                source_revision=query.revision,
                provenance=Provenance.OBSERVED,
                source="stub",
            ),
        ]
        return RetrievalResult(
            items=items,
            strategy=self.name,
            revision=query.revision,
            elapsed_ms=12.5,
        )


class FailingRetrievalStrategy:
    name = "failing"

    def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        raise RuntimeError("Simulated retrieval failure")


def _make_case(
    case_id: str,
    created_at: str,
    gt_symbol: str = "request",
    localizable: bool = True,
    excluded_reason: str | None = None,
) -> CaseRecord:
    return CaseRecord(
        case_id=case_id,
        repo="https://github.com/psf/requests",
        revision="a" * 40,
        bug_report=f"Bug report for {case_id}",
        ground_truth_files=["requests/api.py"] if localizable else [],
        ground_truth_functions=[f"requests.api.{gt_symbol}"] if localizable else [],
        localizable=localizable,
        excluded_reason=excluded_reason if not localizable else None,
        created_at=created_at,
        fail_to_pass_tests=["tests/test_api.py::test_fix"],
    )


class DynamicMockModelProvider:
    def __init__(self, tag: str = "fix") -> None:
        self.tag = tag
        self.counter = 0

    def generate_patch(self, prompt: str, config: Any) -> str:
        self.counter += 1
        return (
            f"```diff\n"
            f"diff --git a/requests/api.py b/requests/api.py\n"
            f"--- a/requests/api.py\n"
            f"+++ b/requests/api.py\n"
            f"@@ -1,3 +1,3 @@\n"
            f"-def old_{self.tag}_{self.counter}(): pass\n"
            f"+def new_{self.tag}_{self.counter}(): pass\n"
            f"```"
        )


def _make_orchestrator(success: bool = True, unique_tag: str = "fix") -> RepairOrchestrator:
    from tracefix.repair.patch_validator import PatchValidator

    provider = DynamicMockModelProvider(tag=unique_tag)
    verifier = StubSandboxVerifier(status="VERIFIED" if success else "FAILED")
    validator = PatchValidator()
    return RepairOrchestrator(
        model_provider=provider,
        patch_validator=validator,
        sandbox_verifier=verifier,
    )


def test_provisional_relevance_matching() -> None:
    case = _make_case("c1", "2023-01-01T10:00:00Z", gt_symbol="request")
    item_match = RankedItem(
        evidence_id="ev1",
        strategy="test",
        rank=1,
        score=1.0,
        target=EvidenceTarget(file="requests/api.py", symbol="request"),
        source_revision="a" * 40,
        provenance=Provenance.OBSERVED,
        source="test",
    )
    item_nomatch = RankedItem(
        evidence_id="ev2",
        strategy="test",
        rank=2,
        score=0.5,
        target=EvidenceTarget(file="requests/api.py", symbol="other"),
        source_revision="a" * 40,
        provenance=Provenance.OBSERVED,
        source="test",
    )
    assert provisional_relevance(case, item_match) is True
    assert provisional_relevance(case, item_nomatch) is False


def test_arm_handles_excluded_case() -> None:
    runner = MultiArmExperimentRunner()
    arm = ExperimentArm(
        arm_id="arm_test",
        name="Test Arm",
        strategy_factory=StubRetrievalStrategy("stub", "request"),
        orchestrator_factory=_make_orchestrator(True),
    )
    case_excluded = _make_case(
        "c_ex",
        "2023-01-01T00:00:00Z",
        localizable=False,
        excluded_reason="no-enclosing-function",
    )

    agg, results = runner.run_arm(arm, [case_excluded])
    assert agg.cases_total == 1
    assert agg.cases_localizable == 0
    assert agg.cases_evaluated == 0
    assert agg.cases_excluded == 1
    assert results[0].status == "excluded"
    assert results[0].evaluated is False
    assert results[0].excluded_reason == "no-enclosing-function"


def test_arm_handles_retrieval_failure() -> None:
    runner = MultiArmExperimentRunner()
    arm = ExperimentArm(
        arm_id="arm_fail",
        name="Failing Arm",
        strategy_factory=FailingRetrievalStrategy(),
        orchestrator_factory=_make_orchestrator(True),
    )
    case = _make_case("c1", "2023-01-01T10:00:00Z")

    agg, results = runner.run_arm(arm, [case])
    assert agg.cases_total == 1
    assert agg.cases_evaluated == 0
    assert agg.cases_failed == 1
    assert results[0].status == "failed"
    assert "Simulated retrieval failure" in (results[0].failure_reason or "")


def test_multi_arm_experiment_comparison(tmp_path: Any) -> None:
    # 3 chronological cases
    case1 = _make_case("c1", "2023-01-01T10:00:00Z", gt_symbol="f1")
    case2 = _make_case("c2", "2023-01-02T10:00:00Z", gt_symbol="f2")
    case3 = _make_case("c3", "2023-01-03T10:00:00Z", gt_symbol="f3")
    cases = [case2, case1, case3]  # intentionally unsorted to test ordering

    # Arm A: lexical baseline (hits f1, misses f2 and f3)
    arm_a = ExperimentArm(
        arm_id="arm_a",
        name="Arm A (Lexical)",
        strategy_factory=StubRetrievalStrategy("lexical", "f1"),
        memory_enabled=False,
        orchestrator_factory=lambda: _make_orchestrator(True, unique_tag="arm_a"),
    )

    # Arm B: graph-guided (hits all, memory disabled)
    arm_b = ExperimentArm(
        arm_id="arm_b",
        name="Arm B (Graph)",
        strategy_factory=StubRetrievalStrategy("graph", "f2"),
        memory_enabled=False,
        orchestrator_factory=lambda: _make_orchestrator(True, unique_tag="arm_b"),
    )

    # Arm C: graph-guided + memory enabled
    shared_repo = IncidentMemoryRepository(storage_path=tmp_path / "memory_arm_c.json")
    arm_c = ExperimentArm(
        arm_id="arm_c",
        name="Arm C (Graph + Memory)",
        strategy_factory=StubRetrievalStrategy("graph", "f2"),
        memory_enabled=True,
        memory_repository=shared_repo,
        orchestrator_factory=lambda: _make_orchestrator(True, unique_tag="arm_c"),
    )

    runner = MultiArmExperimentRunner(metrics_config=MetricsConfig(k_values=(5, 10), primary_k=10))
    res = runner.run_experiment(
        experiment_name="Unit Test Experiment",
        case_set_fingerprint="test_fp_12345",
        arms=[arm_a, arm_b, arm_c],
        cases=cases,
    )

    assert res.experiment_name == "Unit Test Experiment"
    assert "arm_a" in res.arms
    assert "arm_b" in res.arms
    assert "arm_c" in res.arms

    # Check Arm A
    agg_a = res.arms["arm_a"]
    assert agg_a.cases_total == 3
    assert agg_a.cases_evaluated == 3
    assert agg_a.verified_repair_rate == 1.0
    assert agg_a.memories_accumulated == 0

    # Check Arm C: dynamic memory accumulation occurred
    agg_c = res.arms["arm_c"]
    assert agg_c.cases_evaluated == 3
    assert agg_c.memories_accumulated > 0
