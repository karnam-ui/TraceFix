"""Verification sandboxes, test execution, and result parsing.

Workstream B component for TraceFix.
"""

from __future__ import annotations

from tracefix.verification.result_parser import ParsedOutput, TestResultParser
from tracefix.verification.sandbox import (
    DockerSandbox,
    PatchApplicationError,
    SandboxError,
    SandboxUnavailableError,
    SandboxVerifierAdapter,
    VerificationSandbox,
    WorktreeSandbox,
)
from tracefix.verification.test_runner import ExecutionResult, SubprocessTestRunner

__all__ = [
    "DockerSandbox",
    "ExecutionResult",
    "ParsedOutput",
    "PatchApplicationError",
    "SandboxError",
    "SandboxUnavailableError",
    "SandboxVerifierAdapter",
    "SubprocessTestRunner",
    "TestResultParser",
    "VerificationSandbox",
    "WorktreeSandbox",
]
