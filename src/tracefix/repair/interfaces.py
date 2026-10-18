"""Interfaces and typed models for the repair state machine (Phase 1).

Complies with contract contracts/repair.json (C5).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field, model_validator

RepairState = Literal[
    "RECEIVED",
    "CONTEXT_READY",
    "PATCH_GENERATED",
    "PATCH_VALIDATED",
    "VERIFICATION_RUNNING",
    "VERIFIED",
    "FAILED",
    "REJECTED",
]

TERMINAL_STATES: frozenset[RepairState] = frozenset({"VERIFIED", "FAILED", "REJECTED"})
ACTIVE_STATES: frozenset[RepairState] = frozenset(
    {"RECEIVED", "CONTEXT_READY", "PATCH_GENERATED", "PATCH_VALIDATED", "VERIFICATION_RUNNING"}
)


class RepairError(Exception):
    """Base exception for repair engine errors."""


class InvalidStateTransitionError(RepairError):
    """Raised when an invalid state transition is attempted."""


class RetryExhaustedError(RepairError):
    """Raised when maximum retry attempts have been reached."""


class PatchValidationError(RepairError):
    """Raised when a patch fails safety or syntax validation."""


class PatchGenerationError(RepairError):
    """Raised when patch generation fails fatally."""


class RepairConfig(BaseModel):
    """Configuration for repair orchestration."""

    model_provider: str = Field(default="mock", min_length=1)
    model_name: str = Field(default="mock-fixer-v1", min_length=1)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, gt=0)
    max_retries: int = Field(default=2, ge=0)
    timeout_seconds: int = Field(default=120, gt=0)
    max_changed_files: int = Field(default=5, gt=0)
    max_changed_lines: int = Field(default=200, gt=0)


class CandidatePatch(BaseModel):
    """Structured representation of a parsed candidate patch."""

    patch_id: str = Field(min_length=1)
    raw_diff: str = Field(min_length=1)
    files_touched: list[str] = Field(default_factory=list)
    hunk_count: int = Field(default=1, ge=1)
    lines_added: int = Field(default=0, ge=0)
    lines_deleted: int = Field(default=0, ge=0)
    format: str = "unified_diff"
    source_model: str = "unknown"
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ValidationResult(BaseModel):
    """Outcome of patch safety and syntax validation."""

    is_valid: bool
    errors: list[str] = Field(default_factory=list)
    prohibited_files: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class VerificationResultSummary(BaseModel):
    """Summary of sandbox verification outcome."""

    status: str
    exit_code: int = 0
    passed_tests: list[str] = Field(default_factory=list)
    failed_tests: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
    stdout_tail: str = ""
    stderr_tail: str = ""
    timed_out: bool = False


class RetryEvent(BaseModel):
    """Record of a retry attempt."""

    attempt: int = Field(ge=1)
    reason: str = Field(min_length=1)
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class RepairRequest(BaseModel):
    """Input request to the repair engine."""

    case_id: str = Field(min_length=1)
    repo: str = Field(default="")
    base_revision: str = Field(min_length=1)
    bug_report: str = Field(min_length=1)
    context_manifest: dict[str, Any] = Field(default_factory=dict)
    test_suite: dict[str, Any] = Field(default_factory=dict)
    configuration: RepairConfig = Field(default_factory=RepairConfig)


class RepairResult(BaseModel):
    """Structured final outcome of repair execution."""

    case_id: str
    base_revision: str
    final_state: RepairState
    candidate_patch: CandidatePatch | None = None
    verification_result: VerificationResultSummary | None = None
    attempts_made: int = Field(default=1, ge=1)
    retry_history: list[RetryEvent] = Field(default_factory=list)
    duration_seconds: float = Field(default=0.0, ge=0.0)
    failure_reason: str | None = None

    @model_validator(mode="after")
    def _validate_terminal_state(self) -> RepairResult:
        if self.final_state not in TERMINAL_STATES:
            raise ValueError(f"final_state must be a terminal state, got {self.final_state}")
        if self.final_state in {"FAILED", "REJECTED"} and not self.failure_reason:
            raise ValueError(f"{self.final_state} result must carry an explicit failure_reason")
        if self.final_state == "VERIFIED" and not self.candidate_patch:
            raise ValueError("VERIFIED result must carry candidate_patch")
        return self


class ModelProvider(Protocol):
    """Interface for patch-generation model providers."""

    def generate_patch(self, prompt: str, config: RepairConfig) -> str:
        """Generate a raw unified diff patch from the prompt."""
        ...


class PatchValidatorProtocol(Protocol):
    """Interface for patch validators."""

    def validate(self, candidate_patch: CandidatePatch, base_revision: str) -> ValidationResult:
        """Validate patch safety and syntax."""
        ...


class SandboxVerifierProtocol(Protocol):
    """Interface for sandbox execution environments."""

    def verify(
        self,
        case_id: str,
        base_revision: str,
        patch: str,
        test_suite: dict[str, Any],
        timeout_seconds: int = 120,
    ) -> VerificationResultSummary:
        """Execute candidate patch inside isolated sandbox."""
        ...
