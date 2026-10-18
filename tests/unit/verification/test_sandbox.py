"""Unit tests for disposable worktree and Docker sandboxes (Phase 3)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tracefix.repair.interfaces import VerificationResultSummary
from tracefix.verification.sandbox import (
    DockerSandbox,
    PatchApplicationError,
    SandboxUnavailableError,
    SandboxVerifierAdapter,
    WorktreeSandbox,
)


def test_worktree_sandbox_lifecycle() -> None:
    sandbox = WorktreeSandbox()
    try:
        # 1. Setup disposable worktree at HEAD
        sandbox.setup("HEAD")
        assert sandbox.temp_dir is not None
        assert sandbox.temp_dir.exists()
        assert (sandbox.temp_dir / ".git").exists()

        # 2. Apply a clean in-memory patch to README.md
        patch_diff = (
            "diff --git a/README.md b/README.md\n"
            "--- a/README.md\n"
            "+++ b/README.md\n"
            "@@ -1,3 +1,4 @@\n"
            " # TraceFix\n"
            "+<!-- Sandboxed verification test line -->\n"
            " \n"
            " TraceFix is a graph-native bug-resolution agent. This repository contains\n"
        )
        assert sandbox.apply_patch(patch_diff)

        # Confirm patch applied inside sandbox worktree
        sandbox_readme = (sandbox.temp_dir / "README.md").read_text(encoding="utf-8")
        assert "<!-- Sandboxed verification test line -->" in sandbox_readme

        # Crucial check: confirm host repository was NEVER modified
        host_readme = (Path.cwd() / "README.md").read_text(encoding="utf-8")
        assert "<!-- Sandboxed verification test line -->" not in host_readme

    finally:
        # 3. Cleanup
        temp_dir = sandbox.temp_dir
        sandbox.cleanup()
        assert sandbox.temp_dir is None
        if temp_dir is not None:
            assert not temp_dir.exists()

    # Confirm worktree list no longer contains the temp dir
    res = subprocess.run(["git", "worktree", "list"], capture_output=True, text=True, check=True)
    if temp_dir is not None:
        assert str(temp_dir) not in res.stdout


def test_worktree_sandbox_invalid_patch_raises() -> None:
    sandbox = WorktreeSandbox()
    try:
        sandbox.setup("HEAD")
        invalid_patch = (
            "diff --git a/nonexistent.py b/nonexistent.py\n"
            "--- a/nonexistent.py\n"
            "+++ b/nonexistent.py\n"
            "@@ -1,1 +1,1 @@\n"
            "-wrong\n+right\n"
        )
        with pytest.raises(PatchApplicationError):
            sandbox.apply_patch(invalid_patch)
    finally:
        sandbox.cleanup()


def test_docker_sandbox_raises_when_daemon_unavailable() -> None:
    docker_sb = DockerSandbox()
    # On this machine, Docker daemon is down
    if not docker_sb.check_daemon_alive():
        with pytest.raises(SandboxUnavailableError, match="Docker daemon is not available"):
            docker_sb.setup("HEAD")


class MockFailingSandbox:
    def setup(self, base_revision: str) -> None:
        pass

    def apply_patch(self, patch_diff: str) -> bool:
        raise PatchApplicationError("Corrupt patch")

    def run_tests(self, test_suite: dict, timeout_seconds: int = 120) -> VerificationResultSummary:
        return VerificationResultSummary(status="VERIFIED")

    def cleanup(self) -> None:
        pass


def test_verifier_adapter_maps_patch_failure_to_rejected() -> None:
    adapter = SandboxVerifierAdapter(sandbox=MockFailingSandbox())  # type: ignore[arg-type]
    res = adapter.verify(
        case_id="case1",
        base_revision="HEAD",
        patch="bad patch",
        test_suite={},
    )
    assert res.status == "PATCH_REJECTED"
    assert "Corrupt patch" in res.stderr_tail
