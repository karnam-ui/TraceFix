"""Explicit deterministic repair state machine and orchestrator (Phase 1).

Implements the 8-state repair workflow specified in contracts/repair.json (C5):
RECEIVED -> CONTEXT_READY -> PATCH_GENERATED -> PATCH_VALIDATED
         -> VERIFICATION_RUNNING -> VERIFIED | FAILED | REJECTED.
"""

from __future__ import annotations

import hashlib
import time
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from tracefix.repair.interfaces import (
    TERMINAL_STATES,
    CandidatePatch,
    InvalidStateTransitionError,
    ModelProvider,
    PatchValidationError,
    PatchValidatorProtocol,
    RepairRequest,
    RepairResult,
    RepairState,
    RetryEvent,
    RetryExhaustedError,
    SandboxVerifierProtocol,
    ValidationResult,
    VerificationResultSummary,
)

# Directed graph of allowed transitions per contracts/repair.json
ALLOWED_TRANSITIONS: dict[RepairState, set[RepairState]] = {
    "RECEIVED": {"CONTEXT_READY", "FAILED"},
    "CONTEXT_READY": {"PATCH_GENERATED", "FAILED"},
    "PATCH_GENERATED": {"PATCH_VALIDATED", "FAILED", "REJECTED", "PATCH_GENERATED"},
    "PATCH_VALIDATED": {"VERIFICATION_RUNNING", "REJECTED", "FAILED"},
    "VERIFICATION_RUNNING": {"VERIFIED", "FAILED", "PATCH_GENERATED"},
    "VERIFIED": set(),
    "FAILED": set(),
    "REJECTED": set(),
}


class StateTransitionRecord(BaseModel):
    """Immutable audit record of a single state transition."""

    from_state: RepairState
    to_state: RepairState
    reason: str
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class RepairStateMachine:
    """Deterministic, auditable state machine for bug resolution."""

    def __init__(self, max_retries: int = 2) -> None:
        if max_retries < 0:
            raise ValueError(f"max_retries must be >= 0, got {max_retries}")
        self._current_state: RepairState = "RECEIVED"
        self._max_retries: int = max_retries
        self._attempt_number: int = 1
        self._history: list[StateTransitionRecord] = []
        self._retry_history: list[RetryEvent] = []
        self._start_monotonic: float = time.monotonic()

    @property
    def current_state(self) -> RepairState:
        return self._current_state

    @property
    def attempt_number(self) -> int:
        return self._attempt_number

    @property
    def max_retries(self) -> int:
        return self._max_retries

    @property
    def is_terminal(self) -> bool:
        return self._current_state in TERMINAL_STATES

    @property
    def history(self) -> list[StateTransitionRecord]:
        return list(self._history)

    @property
    def retry_history(self) -> list[RetryEvent]:
        return list(self._retry_history)

    def duration_seconds(self) -> float:
        return round(time.monotonic() - self._start_monotonic, 3)

    def can_retry(self) -> bool:
        """True if retry budget has not been exhausted."""
        return self._attempt_number <= self._max_retries

    def transition_to(self, target_state: RepairState, reason: str = "") -> None:
        """Execute and audit a state transition.

        Raises:
            InvalidStateTransitionError: if attempting to leave a terminal state
            or make an illegal jump in the state machine graph.
        """
        if self._current_state in TERMINAL_STATES:
            raise InvalidStateTransitionError(
                f"Cannot transition from terminal state '{self._current_state}' "
                f"to '{target_state}'. Terminal states are immutable."
            )

        allowed = ALLOWED_TRANSITIONS.get(self._current_state, set())
        if target_state not in allowed:
            raise InvalidStateTransitionError(
                f"Illegal state transition from '{self._current_state}' to '{target_state}'. "
                f"Allowed destinations: {sorted(allowed)}. Reason provided: '{reason}'."
            )

        record = StateTransitionRecord(
            from_state=self._current_state,
            to_state=target_state,
            reason=reason or f"Transition to {target_state}",
        )
        self._history.append(record)
        self._current_state = target_state

    def record_retry(self, reason: str) -> None:
        """Increment retry attempt counter and transition back to PATCH_GENERATED.

        Raises:
            RetryExhaustedError: if maximum retry attempts are exceeded.
            InvalidStateTransitionError: if current state does not allow retry.
        """
        if not self.can_retry():
            raise RetryExhaustedError(
                f"Retry budget exhausted: attempt {self._attempt_number} exceeds "
                f"max_retries ({self._max_retries}). Reason: {reason}"
            )

        self._attempt_number += 1
        event = RetryEvent(attempt=self._attempt_number, reason=reason)
        self._retry_history.append(event)
        self.transition_to("PATCH_GENERATED", reason=f"Retry #{self._attempt_number}: {reason}")


class SimplePromptBuilder:
    """Assembles prompt for patch generation with context and diff instructions."""

    def build_prompt(self, bug_report: str, context_manifest: dict[str, Any]) -> str:
        items = context_manifest.get("items", [])
        context_snippets: list[str] = []
        for item in items:
            path = item.get("file_path") or item.get("path") or ""
            symbol = item.get("symbol") or ""
            content = item.get("content") or ""
            context_snippets.append(
                f"### File: {path} (Symbol: {symbol})\n```python\n{content}\n```"
            )

        context_str = "\n\n".join(context_snippets) if context_snippets else "No prior context."

        return (
            "You are an automated software repair engine.\n"
            "Generate a precise bug fix in unified diff format (`diff --git a/... b/...`).\n"
            "Do NOT include conversational filler, reasoning, or markdown outside code blocks.\n\n"
            f"## Problem Statement\n{bug_report}\n\n"
            f"## Relevant Code Context\n{context_str}\n\n"
            "## Output Instructions\n"
            "Output ONLY the unified diff in a ```diff code block.\n"
        )


class SimplePatchParser:
    """Extracts unified diff and changed files from model output."""

    def parse(self, raw_output: str, source_model: str = "unknown") -> CandidatePatch:
        cleaned = raw_output.strip()
        # Strip markdown fences if present
        if "```diff" in cleaned:
            parts = cleaned.split("```diff", 1)[1].split("```", 1)
            diff_text = parts[0].strip()
        elif "```" in cleaned:
            parts = cleaned.split("```", 1)[1].split("```", 1)
            diff_text = parts[0].strip()
        else:
            diff_text = cleaned

        if not diff_text:
            raise PatchValidationError("Model produced empty patch output")

        files: list[str] = []
        hunk_count = 0
        lines_added = 0
        lines_deleted = 0

        for line in diff_text.splitlines():
            if line.startswith("+++ b/"):
                files.append(line[6:].strip())
            elif line.startswith("@@"):
                hunk_count += 1
            elif line.startswith("+") and not line.startswith("+++"):
                lines_added += 1
            elif line.startswith("-") and not line.startswith("---"):
                lines_deleted += 1

        patch_hash = hashlib.sha256(diff_text.encode("utf-8")).hexdigest()

        return CandidatePatch(
            patch_id=f"patch_{patch_hash[:16]}",
            raw_diff=diff_text,
            files_touched=sorted(set(files)),
            hunk_count=max(1, hunk_count),
            lines_added=lines_added,
            lines_deleted=lines_deleted,
            format="unified_diff",
            source_model=source_model,
        )


class RepairOrchestrator:
    """Coordinates bug report, patch generation, validation, and verification."""

    def __init__(
        self,
        model_provider: ModelProvider,
        patch_validator: PatchValidatorProtocol,
        sandbox_verifier: SandboxVerifierProtocol,
    ) -> None:
        self.model_provider = model_provider
        self.patch_validator = patch_validator
        self.sandbox_verifier = sandbox_verifier
        self.prompt_builder = SimplePromptBuilder()
        self.patch_parser = SimplePatchParser()

    def run(self, request: RepairRequest) -> RepairResult:
        """Execute the repair workflow against the state machine."""
        sm = RepairStateMachine(max_retries=request.configuration.max_retries)
        candidate: CandidatePatch | None = None
        last_verification: VerificationResultSummary | None = None
        failure_reason: str | None = None

        try:
            # 1. Received -> Context Ready
            if not request.bug_report:
                sm.transition_to("FAILED", "Bug report text is empty")
                return RepairResult(
                    case_id=request.case_id,
                    base_revision=request.base_revision,
                    final_state=sm.current_state,
                    attempts_made=sm.attempt_number,
                    retry_history=sm.retry_history,
                    duration_seconds=sm.duration_seconds(),
                    failure_reason="Bug report text is empty",
                )

            sm.transition_to("CONTEXT_READY", "Bug report and context manifest accepted")

            # 2. Repair loop bounded by retries
            while not sm.is_terminal:
                # Patch Generation
                if sm.current_state in {"CONTEXT_READY", "PATCH_GENERATED"}:
                    prompt = self.prompt_builder.build_prompt(
                        request.bug_report, request.context_manifest
                    )
                    try:
                        raw_completion = self.model_provider.generate_patch(
                            prompt, request.configuration
                        )
                        candidate = self.patch_parser.parse(
                            raw_completion, source_model=request.configuration.model_name
                        )
                        if sm.current_state != "PATCH_GENERATED":
                            sm.transition_to(
                                "PATCH_GENERATED",
                                f"Patch generated (attempt {sm.attempt_number})",
                            )
                    except Exception as exc:
                        if sm.can_retry():
                            sm.record_retry(f"Generation failure: {exc}")
                            continue
                        sm.transition_to("FAILED", f"Patch generation failed: {exc}")
                        failure_reason = f"Patch generation failed: {exc}"
                        break

                if candidate is None:
                    sm.transition_to("FAILED", "Candidate patch is missing")
                    failure_reason = "Candidate patch is missing"
                    break

                # Patch Validation
                val_result: ValidationResult = self.patch_validator.validate(
                    candidate, request.base_revision
                )
                if not val_result.is_valid:
                    # Check for safety violations (path traversal, prohibited files)
                    if val_result.prohibited_files or any(
                        "traversal" in err.lower() or "prohibited" in err.lower()
                        for err in val_result.errors
                    ):
                        reason = f"Safety policy rejection: {val_result.errors}"
                        sm.transition_to("REJECTED", reason)
                        failure_reason = reason
                        break
                    # Otherwise syntax or diff formatting error
                    if sm.can_retry():
                        sm.record_retry(f"Syntax validation failure: {val_result.errors}")
                        continue
                    reason = f"Validation failed and retries exhausted: {val_result.errors}"
                    sm.transition_to("FAILED", reason)
                    failure_reason = reason
                    break

                sm.transition_to("PATCH_VALIDATED", "Patch passed safety and bounds checks")

                # Sandbox Verification
                sm.transition_to("VERIFICATION_RUNNING", "Executing sandbox test verification")
                last_verification = self.sandbox_verifier.verify(
                    case_id=request.case_id,
                    base_revision=request.base_revision,
                    patch=candidate.raw_diff,
                    test_suite=request.test_suite,
                    timeout_seconds=request.configuration.timeout_seconds,
                )

                if last_verification.status == "VERIFIED":
                    sm.transition_to("VERIFIED", "All declared verification tests passed")
                    break
                elif last_verification.status == "TEST_FAILED":
                    if sm.can_retry():
                        sm.record_retry(f"Tests failed: {last_verification.failed_tests}")
                        continue
                    reason = (
                        f"Tests failed and retries exhausted. "
                        f"Failed tests: {last_verification.failed_tests}"
                    )
                    sm.transition_to("FAILED", reason)
                    failure_reason = reason
                    break
                else:
                    # SETUP_FAILED, TIMEOUT, ENVIRONMENT_ERROR
                    reason = (
                        f"Verification error ({last_verification.status}): "
                        f"{last_verification.stderr_tail or last_verification.stdout_tail}"
                    )
                    sm.transition_to("FAILED", reason)
                    failure_reason = reason
                    break

        except Exception as exc:
            if not sm.is_terminal:
                sm.transition_to("FAILED", f"Unhandled orchestrator exception: {exc}")
            failure_reason = f"Unhandled orchestrator exception: {exc}"

        return RepairResult(
            case_id=request.case_id,
            base_revision=request.base_revision,
            final_state=sm.current_state,
            candidate_patch=candidate if sm.current_state == "VERIFIED" else candidate,
            verification_result=last_verification,
            attempts_made=sm.attempt_number,
            retry_history=sm.retry_history,
            duration_seconds=sm.duration_seconds(),
            failure_reason=failure_reason,
        )
