"""Unit tests for the repair state machine and orchestrator (Phase 1).

Covers:
- Valid state transitions
- Invalid transitions and illegal state jumps
- Terminal state immutability
- Retry budget tracking and exhaustion
- Orchestrator end-to-end execution with mocks (success, rejection, retries, failure)
"""

from __future__ import annotations

import pytest

from tracefix.repair.interfaces import (
    CandidatePatch,
    InvalidStateTransitionError,
    RepairConfig,
    RepairRequest,
    RepairState,
    RetryExhaustedError,
    ValidationResult,
    VerificationResultSummary,
)
from tracefix.repair.state_machine import (
    RepairOrchestrator,
    RepairStateMachine,
    SimplePatchParser,
)


class MockModelProvider:
    """Mock LLM returning configured diffs or raising errors."""

    def __init__(self, responses: list[str | Exception]) -> None:
        self.responses = list(responses)
        self.calls: list[str] = []

    def generate_patch(self, prompt: str, config: RepairConfig) -> str:
        self.calls.append(prompt)
        if not self.responses:
            return (
                "diff --git a/pkg/mod.py b/pkg/mod.py\n"
                "--- a/pkg/mod.py\n"
                "+++ b/pkg/mod.py\n"
                "@@ -1,1 +1,1 @@\n"
                "-old\n+new\n"
            )
        resp = self.responses.pop(0)
        if isinstance(resp, Exception):
            raise resp
        return resp


class MockPatchValidator:
    """Mock patch validator returning configured results."""

    def __init__(self, results: list[ValidationResult]) -> None:
        self.results = list(results)
        self.calls: list[CandidatePatch] = []

    def validate(self, candidate_patch: CandidatePatch, base_revision: str) -> ValidationResult:
        self.calls.append(candidate_patch)
        if not self.results:
            return ValidationResult(is_valid=True)
        return self.results.pop(0)


class MockSandboxVerifier:
    """Mock sandbox verifier returning configured verification summaries."""

    def __init__(self, summaries: list[VerificationResultSummary]) -> None:
        self.summaries = list(summaries)
        self.calls: list[dict] = []

    def verify(
        self,
        case_id: str,
        base_revision: str,
        patch: str,
        test_suite: dict,
        timeout_seconds: int = 120,
    ) -> VerificationResultSummary:
        self.calls.append(
            {
                "case_id": case_id,
                "base_revision": base_revision,
                "patch": patch,
                "test_suite": test_suite,
            }
        )
        if not self.summaries:
            return VerificationResultSummary(status="VERIFIED", exit_code=0)
        return self.summaries.pop(0)


# ============================================================================
# State Machine Unit Tests
# ============================================================================


def test_initial_state_is_received() -> None:
    sm = RepairStateMachine(max_retries=2)
    assert sm.current_state == "RECEIVED"
    assert sm.attempt_number == 1
    assert not sm.is_terminal
    assert len(sm.history) == 0


def test_valid_happy_path_transitions() -> None:
    sm = RepairStateMachine(max_retries=2)
    sm.transition_to("CONTEXT_READY", "context loaded")
    assert sm.current_state == "CONTEXT_READY"

    sm.transition_to("PATCH_GENERATED", "model returned diff")
    assert sm.current_state == "PATCH_GENERATED"

    sm.transition_to("PATCH_VALIDATED", "syntax & safety passed")
    assert sm.current_state == "PATCH_VALIDATED"

    sm.transition_to("VERIFICATION_RUNNING", "sandbox spawned")
    assert sm.current_state == "VERIFICATION_RUNNING"

    sm.transition_to("VERIFIED", "all tests passed")
    assert sm.current_state == "VERIFIED"
    assert sm.is_terminal
    assert len(sm.history) == 5


def test_valid_rejection_path() -> None:
    sm = RepairStateMachine()
    sm.transition_to("CONTEXT_READY")
    sm.transition_to("PATCH_GENERATED")
    sm.transition_to("PATCH_VALIDATED")
    sm.transition_to("REJECTED", "path traversal detected")
    assert sm.current_state == "REJECTED"
    assert sm.is_terminal


@pytest.mark.parametrize(
    ("from_state", "illegal_to"),
    [
        ("RECEIVED", "PATCH_GENERATED"),
        ("RECEIVED", "PATCH_VALIDATED"),
        ("RECEIVED", "VERIFIED"),
        ("CONTEXT_READY", "VERIFIED"),
        ("CONTEXT_READY", "VERIFICATION_RUNNING"),
        ("PATCH_GENERATED", "VERIFIED"),
        ("PATCH_VALIDATED", "VERIFIED"),
        ("VERIFICATION_RUNNING", "PATCH_VALIDATED"),
    ],
)
def test_illegal_state_jumps_rejected(from_state: str, illegal_to: str) -> None:
    sm = RepairStateMachine()
    # Bring to from_state via legitimate path
    active_steps = {
        "CONTEXT_READY",
        "PATCH_GENERATED",
        "PATCH_VALIDATED",
        "VERIFICATION_RUNNING",
    }
    if from_state in active_steps:
        sm.transition_to("CONTEXT_READY")
    if from_state in {"PATCH_GENERATED", "PATCH_VALIDATED", "VERIFICATION_RUNNING"}:
        sm.transition_to("PATCH_GENERATED")
    if from_state in {"PATCH_VALIDATED", "VERIFICATION_RUNNING"}:
        sm.transition_to("PATCH_VALIDATED")
    if from_state == "VERIFICATION_RUNNING":
        sm.transition_to("VERIFICATION_RUNNING")

    with pytest.raises(InvalidStateTransitionError, match="Illegal state transition"):
        sm.transition_to(illegal_to, "illegal move")  # type: ignore[arg-type]


@pytest.mark.parametrize("terminal", ["VERIFIED", "FAILED", "REJECTED"])
def test_terminal_states_are_immutable(terminal: RepairState) -> None:
    sm = RepairStateMachine()
    sm.transition_to("FAILED" if terminal == "FAILED" else "CONTEXT_READY")
    if terminal != "FAILED":
        sm.transition_to("PATCH_GENERATED")
        sm.transition_to("PATCH_VALIDATED")
        if terminal == "REJECTED":
            sm.transition_to("REJECTED")
        else:
            sm.transition_to("VERIFICATION_RUNNING")
            sm.transition_to("VERIFIED")

    assert sm.current_state == terminal
    assert sm.is_terminal

    with pytest.raises(InvalidStateTransitionError, match="Terminal states are immutable"):
        sm.transition_to("RECEIVED", "attempt resurrection")


def test_retry_mechanics() -> None:
    sm = RepairStateMachine(max_retries=2)
    assert sm.can_retry()

    sm.transition_to("CONTEXT_READY")
    sm.transition_to("PATCH_GENERATED")
    sm.transition_to("PATCH_VALIDATED")
    sm.transition_to("VERIFICATION_RUNNING")

    # Retry 1
    sm.record_retry("test failed on assertion")
    assert sm.attempt_number == 2
    assert sm.current_state == "PATCH_GENERATED"
    assert sm.can_retry()
    assert len(sm.retry_history) == 1
    assert sm.retry_history[0].attempt == 2

    # Advance again
    sm.transition_to("PATCH_VALIDATED")
    sm.transition_to("VERIFICATION_RUNNING")

    # Retry 2
    sm.record_retry("test failed on regression")
    assert sm.attempt_number == 3
    assert sm.current_state == "PATCH_GENERATED"
    assert not sm.can_retry()

    # Advance again
    sm.transition_to("PATCH_VALIDATED")
    sm.transition_to("VERIFICATION_RUNNING")

    # Attempting retry 3 must raise RetryExhaustedError
    with pytest.raises(RetryExhaustedError, match="Retry budget exhausted"):
        sm.record_retry("cannot retry again")


def test_negative_max_retries_rejected() -> None:
    with pytest.raises(ValueError, match="max_retries must be >= 0"):
        RepairStateMachine(max_retries=-1)


# ============================================================================
# Orchestrator Integration Tests
# ============================================================================


def test_orchestrator_successful_repair() -> None:
    diff_text = (
        "```diff\n"
        "diff --git a/requests/models.py b/requests/models.py\n"
        "--- a/requests/models.py\n"
        "+++ b/requests/models.py\n"
        "@@ -386,2 +386,2 @@\n"
        "- self.headers['Content-Length'] = '0'\n"
        "+ if self.method not in ('GET', 'HEAD'):\n"
        "+     self.headers['Content-Length'] = '0'\n"
        "```"
    )
    provider = MockModelProvider([diff_text])
    validator = MockPatchValidator([ValidationResult(is_valid=True)])
    verifier = MockSandboxVerifier(
        [
            VerificationResultSummary(
                status="VERIFIED",
                exit_code=0,
                passed_tests=["test_no_content_length"],
            )
        ]
    )

    orchestrator = RepairOrchestrator(provider, validator, verifier)
    request = RepairRequest(
        case_id="psf__requests-1142",
        base_revision="22623bd8c265b78b161542663ee980738441c307",
        bug_report="requests.get always sends content-length header",
    )

    result = orchestrator.run(request)
    assert result.final_state == "VERIFIED"
    assert result.candidate_patch is not None
    assert "requests/models.py" in result.candidate_patch.files_touched
    assert result.candidate_patch.lines_added == 2
    assert result.candidate_patch.lines_deleted == 1
    assert result.attempts_made == 1
    assert result.failure_reason is None
    assert result.duration_seconds >= 0.0


def test_orchestrator_safety_rejection() -> None:
    diff_text = (
        "diff --git a/../../etc/passwd b/../../etc/passwd\n"
        "--- a/../../etc/passwd\n"
        "+++ b/../../etc/passwd\n"
        "@@ -1,1 +1,1 @@\n"
        "+root::0:0:::\n"
    )
    provider = MockModelProvider([diff_text])
    validator = MockPatchValidator(
        [
            ValidationResult(
                is_valid=False,
                errors=["Path traversal detected: ../../etc/passwd"],
                prohibited_files=["../../etc/passwd"],
            )
        ]
    )
    verifier = MockSandboxVerifier([])

    orchestrator = RepairOrchestrator(provider, validator, verifier)
    request = RepairRequest(
        case_id="test-case-traversal",
        base_revision="abc12345",
        bug_report="security test",
    )

    result = orchestrator.run(request)
    assert result.final_state == "REJECTED"
    assert "Safety policy rejection" in (result.failure_reason or "")
    # verifier should never have been invoked
    assert len(verifier.calls) == 0


def test_orchestrator_retries_and_succeeds() -> None:
    diff1 = (
        "diff --git a/mod.py b/mod.py\n"
        "--- a/mod.py\n"
        "+++ b/mod.py\n"
        "@@ -1,1 +1,1 @@\n"
        "-bad\n+partial\n"
    )
    diff2 = (
        "diff --git a/mod.py b/mod.py\n"
        "--- a/mod.py\n"
        "+++ b/mod.py\n"
        "@@ -1,1 +1,1 @@\n"
        "-bad\n+perfect\n"
    )
    provider = MockModelProvider([diff1, diff2])
    validator = MockPatchValidator(
        [
            ValidationResult(is_valid=True),
            ValidationResult(is_valid=True),
        ]
    )
    verifier = MockSandboxVerifier(
        [
            VerificationResultSummary(
                status="TEST_FAILED", exit_code=1, failed_tests=["test_feature"]
            ),
            VerificationResultSummary(
                status="VERIFIED", exit_code=0, passed_tests=["test_feature"]
            ),
        ]
    )

    orchestrator = RepairOrchestrator(provider, validator, verifier)
    request = RepairRequest(
        case_id="test-retry",
        base_revision="commit1",
        bug_report="fix something",
        configuration=RepairConfig(max_retries=2),
    )

    result = orchestrator.run(request)
    assert result.final_state == "VERIFIED"
    assert result.attempts_made == 2
    assert len(result.retry_history) == 1
    assert "test_feature" in result.retry_history[0].reason


def test_orchestrator_exhausts_retries_and_fails() -> None:
    diff = "diff --git a/mod.py b/mod.py\n--- a/mod.py\n+++ b/mod.py\n@@ -1,1 +1,1 @@\n-a\n+b\n"
    provider = MockModelProvider([diff, diff, diff])
    validator = MockPatchValidator(
        [
            ValidationResult(is_valid=True),
            ValidationResult(is_valid=True),
            ValidationResult(is_valid=True),
        ]
    )
    verifier = MockSandboxVerifier(
        [
            VerificationResultSummary(status="TEST_FAILED", failed_tests=["test_1"]),
            VerificationResultSummary(status="TEST_FAILED", failed_tests=["test_1"]),
            VerificationResultSummary(status="TEST_FAILED", failed_tests=["test_1"]),
        ]
    )

    orchestrator = RepairOrchestrator(provider, validator, verifier)
    request = RepairRequest(
        case_id="test-exhaustion",
        base_revision="commit1",
        bug_report="fix something",
        configuration=RepairConfig(max_retries=2),
    )

    result = orchestrator.run(request)
    assert result.final_state == "FAILED"
    assert result.attempts_made == 3
    assert len(result.retry_history) == 2
    assert "retries exhausted" in (result.failure_reason or "")


def test_empty_bug_report_fails_immediately() -> None:
    with pytest.raises(ValueError, match="at least 1 character"):
        # Empty bug report violates Pydantic min_length=1
        RepairRequest(case_id="case1", base_revision="rev1", bug_report="")


def test_patch_parser_handles_fences_and_empty() -> None:
    parser = SimplePatchParser()
    raw = (
        "```diff\n"
        "diff --git a/a.py b/a.py\n"
        "--- a/a.py\n"
        "+++ b/a.py\n"
        "@@ -1,1 +1,2 @@\n"
        "-1\n"
        "+2\n"
        "+3\n"
        "```"
    )
    diff = parser.parse(raw)
    assert diff.files_touched == ["a.py"]
    assert diff.lines_added == 2
    assert diff.lines_deleted == 1
    assert diff.hunk_count == 1

    with pytest.raises(Exception, match="empty patch output"):
        parser.parse("   ")
