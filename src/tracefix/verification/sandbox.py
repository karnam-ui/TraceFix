"""Isolated sandbox verification environments (Phase 3).

Complies with contracts/verification.json (C6).
Supports:
- Tier 1: Disposable git worktree sandbox (default, service-free)
- Tier 2: Docker container sandbox with network isolation (marker-gated)
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Protocol

from tracefix.repair.interfaces import VerificationResultSummary
from tracefix.verification.result_parser import TestResultParser
from tracefix.verification.test_runner import SubprocessTestRunner


class SandboxError(Exception):
    """Base exception for sandbox execution errors."""


class PatchApplicationError(SandboxError):
    """Raised when candidate patch fails to apply to the repository."""


class SandboxUnavailableError(SandboxError):
    """Raised when the requested sandbox tier is unavailable on the host."""


class VerificationSandbox(Protocol):
    """Abstract interface for disposable execution environments."""

    def setup(self, base_revision: str) -> None:
        """Create disposable environment checked out at base_revision."""
        ...

    def apply_patch(self, patch_diff: str) -> bool:
        """Apply patch inside the sandbox."""
        ...

    def run_tests(
        self,
        test_suite: dict[str, Any],
        timeout_seconds: int = 120,
    ) -> VerificationResultSummary:
        """Execute tests against the patched repository."""
        ...

    def cleanup(self) -> None:
        """Dispose of sandbox resources and working directories."""
        ...


class WorktreeSandbox:
    """Tier 1: Disposable git worktree sandbox.

    Guarantees that untrusted patches are never applied to the main checkout.
    Operates without external services or container daemons.
    """

    def __init__(self, repo_dir: str | Path | None = None) -> None:
        self.repo_dir = Path(repo_dir).resolve() if repo_dir else Path.cwd().resolve()
        self.temp_dir: Path | None = None
        self.runner = SubprocessTestRunner()
        self.parser = TestResultParser()
        self.base_revision: str = "HEAD"

    def setup(self, base_revision: str) -> None:
        """Create a disposable worktree detached at base_revision."""
        self.base_revision = base_revision
        temp_path = Path(tempfile.mkdtemp(prefix="tracefix_sandbox_"))
        self.temp_dir = temp_path

        cmd = [
            "git",
            "worktree",
            "add",
            str(self.temp_dir),
            base_revision,
            "--detach",
        ]
        res = subprocess.run(
            cmd,
            cwd=str(self.repo_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0:
            self.cleanup()
            raise SandboxError(
                f"Failed to create disposable git worktree for revision {base_revision}: "
                f"{res.stderr or res.stdout}"
            )

    def apply_patch(self, patch_diff: str) -> bool:
        """Apply candidate unified diff inside the disposable worktree."""
        if not self.temp_dir or not self.temp_dir.exists():
            raise SandboxError("Sandbox worktree is not initialized")

        # Use git apply --whitespace=fix
        cmd = ["git", "apply", "--whitespace=fix", "-"]
        res = subprocess.run(
            cmd,
            cwd=str(self.temp_dir),
            input=patch_diff,
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0:
            raise PatchApplicationError(
                f"Patch application failed inside sandbox: {res.stderr or res.stdout}"
            )
        return True

    def run_tests(
        self,
        test_suite: dict[str, Any],
        timeout_seconds: int = 120,
    ) -> VerificationResultSummary:
        """Execute test suite and evaluate verification criteria."""
        if not self.temp_dir or not self.temp_dir.exists():
            raise SandboxError("Sandbox worktree is not initialized")

        fail_to_pass: list[str] = test_suite.get("fail_to_pass", [])
        pass_to_pass: list[str] = test_suite.get("pass_to_pass", [])
        all_tests = fail_to_pass + pass_to_pass

        # If specific test identifiers are given, run only those to stay bounded
        test_args = all_tests if all_tests else []
        command = ["pytest", "-q"] + test_args

        exec_res = self.runner.run(
            command=command,
            cwd=self.temp_dir,
            timeout_seconds=timeout_seconds,
        )

        if exec_res.timed_out:
            return VerificationResultSummary(
                status="TIMEOUT",
                exit_code=124,
                duration_seconds=exec_res.duration_seconds,
                stdout_tail=exec_res.stdout[-1000:],
                stderr_tail=exec_res.stderr[-1000:],
                timed_out=True,
            )

        parsed = self.parser.parse_pytest(exec_res.stdout, exec_res.stderr, exec_res.exit_code)

        if parsed.is_setup_failure:
            return VerificationResultSummary(
                status="SETUP_FAILED",
                exit_code=exec_res.exit_code,
                duration_seconds=exec_res.duration_seconds,
                stdout_tail=exec_res.stdout[-1000:],
                stderr_tail=exec_res.stderr[-1000:],
            )

        # Verification logic:
        # 1. Exit code must be 0
        # 2. No test failures or collection errors
        is_verified = (
            exec_res.exit_code == 0 and parsed.failed_count == 0 and parsed.error_count == 0
        )

        status = "VERIFIED" if is_verified else "TEST_FAILED"

        return VerificationResultSummary(
            status=status,
            exit_code=exec_res.exit_code,
            passed_tests=parsed.passed_tests,
            failed_tests=parsed.failed_tests,
            duration_seconds=exec_res.duration_seconds,
            stdout_tail=exec_res.stdout[-1000:],
            stderr_tail=exec_res.stderr[-1000:],
        )

    def cleanup(self) -> None:
        """Prune and remove disposable git worktree."""
        if self.temp_dir and self.temp_dir.exists():
            # Prune worktree from git tracking
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(self.temp_dir)],
                cwd=str(self.repo_dir),
                capture_output=True,
                check=False,
            )
            # Remove directory if still on filesystem
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            self.temp_dir = None

    def __enter__(self) -> WorktreeSandbox:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.cleanup()


class DockerSandbox:
    """Tier 2: Containerized sandbox with network disabled (integration marker)."""

    def __init__(self, image: str = "python:3.11-slim") -> None:
        self.image = image
        self.worktree_sandbox = WorktreeSandbox()

    def check_daemon_alive(self) -> bool:
        """Check if Docker daemon is responsive."""
        try:
            res = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=5,
                check=False,
            )
            return res.returncode == 0
        except Exception:
            return False

    def setup(self, base_revision: str) -> None:
        if not self.check_daemon_alive():
            raise SandboxUnavailableError(
                "Docker daemon is not available on this host. Use Tier 1 WorktreeSandbox."
            )
        self.worktree_sandbox.setup(base_revision)

    def apply_patch(self, patch_diff: str) -> bool:
        return self.worktree_sandbox.apply_patch(patch_diff)

    def run_tests(
        self,
        test_suite: dict[str, Any],
        timeout_seconds: int = 120,
    ) -> VerificationResultSummary:
        if not self.check_daemon_alive():
            raise SandboxUnavailableError("Docker daemon is not available")

        # Delegate execution inside container with --network none
        workspace = self.worktree_sandbox.temp_dir
        if not workspace:
            raise SandboxError("Workspace not initialized")

        cmd = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--memory",
            "2g",
            "-v",
            f"{workspace}:/app",
            "-w",
            "/app",
            self.image,
            "pytest",
            "-q",
        ]
        runner = SubprocessTestRunner()
        exec_res = runner.run(cmd, cwd=Path.cwd(), timeout_seconds=timeout_seconds)
        parser = TestResultParser()
        parsed = parser.parse_pytest(exec_res.stdout, exec_res.stderr, exec_res.exit_code)
        is_verified = exec_res.exit_code == 0 and parsed.failed_count == 0

        return VerificationResultSummary(
            status="VERIFIED" if is_verified else "TEST_FAILED",
            exit_code=exec_res.exit_code,
            passed_tests=parsed.passed_tests,
            failed_tests=parsed.failed_tests,
            duration_seconds=exec_res.duration_seconds,
            stdout_tail=exec_res.stdout[-1000:],
            stderr_tail=exec_res.stderr[-1000:],
        )

    def cleanup(self) -> None:
        self.worktree_sandbox.cleanup()


class SandboxVerifierAdapter:
    """Adapter implementing SandboxVerifierProtocol from tracefix.repair.interfaces."""

    def __init__(self, sandbox: VerificationSandbox | None = None) -> None:
        self.sandbox = sandbox or WorktreeSandbox()

    def verify(
        self,
        case_id: str,
        base_revision: str,
        patch: str,
        test_suite: dict[str, Any],
        timeout_seconds: int = 120,
    ) -> VerificationResultSummary:
        try:
            self.sandbox.setup(base_revision)
            try:
                self.sandbox.apply_patch(patch)
            except PatchApplicationError as err:
                return VerificationResultSummary(
                    status="PATCH_REJECTED",
                    exit_code=1,
                    stderr_tail=str(err),
                )

            return self.sandbox.run_tests(test_suite=test_suite, timeout_seconds=timeout_seconds)
        except SandboxError as err:
            return VerificationResultSummary(
                status="ENVIRONMENT_ERROR",
                exit_code=1,
                stderr_tail=str(err),
            )
        finally:
            self.sandbox.cleanup()
