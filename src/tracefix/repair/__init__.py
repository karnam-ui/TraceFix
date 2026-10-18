"""Repair orchestration, state machine, patch generation, and validation.

Workstream B component for TraceFix.
"""

from __future__ import annotations

from tracefix.repair.interfaces import (
    CandidatePatch,
    InvalidStateTransitionError,
    ModelProvider,
    PatchValidationError,
    RepairConfig,
    RepairError,
    RepairRequest,
    RepairResult,
    RepairState,
    RetryEvent,
    RetryExhaustedError,
    ValidationResult,
    VerificationResultSummary,
)
from tracefix.repair.patch_generator import (
    FatalProviderError,
    HttpModelProvider,
    MockModelProvider,
    PatchPromptBuilder,
    TransientProviderError,
)
from tracefix.repair.patch_parser import DiffHunk, FileDiff, PatchParser
from tracefix.repair.patch_validator import PatchValidator
from tracefix.repair.state_machine import RepairOrchestrator, RepairStateMachine

__all__ = [
    "CandidatePatch",
    "DiffHunk",
    "FatalProviderError",
    "FileDiff",
    "HttpModelProvider",
    "InvalidStateTransitionError",
    "MockModelProvider",
    "ModelProvider",
    "PatchParser",
    "PatchPromptBuilder",
    "PatchValidationError",
    "PatchValidator",
    "RepairConfig",
    "RepairError",
    "RepairOrchestrator",
    "RepairRequest",
    "RepairResult",
    "RepairState",
    "RepairStateMachine",
    "RetryEvent",
    "RetryExhaustedError",
    "TransientProviderError",
    "ValidationResult",
    "VerificationResultSummary",
]
