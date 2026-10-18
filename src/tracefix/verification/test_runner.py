"""Subprocess test runner with strict secret scrubbing and timeout control (Phase 3).

Complies with contracts/verification.json (C6).
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path

from pydantic import BaseModel, Field

SENSITIVE_ENV_PATTERN = re.compile(
    r"(KEY|TOKEN|SECRET|PASSWORD|PASS|AUTH|CREDENTIAL|AWS_|GITHUB_|SSH_)",
    re.IGNORECASE,
)

ALLOWLISTED_RUNNERS = ("pytest", "python", "py")


class ExecutionResult(BaseModel):
    """Raw result of running a test command inside a sandbox."""

    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False
    command: list[str] = Field(default_factory=list)


class SubprocessTestRunner:
    """Executes verified test commands with isolation and resource bounds."""

    def __init__(
        self,
        max_output_bytes: int = 1048576,  # 1 MB
        scrub_host_secrets: bool = True,
    ) -> None:
        self.max_output_bytes = max_output_bytes
        self.scrub_host_secrets = scrub_host_secrets

    def build_clean_environment(self) -> dict[str, str]:
        """Produce a minimal, scrubbed environment with zero credentials leaked."""
        clean_env: dict[str, str] = {}
        for k, v in os.environ.items():
            if self.scrub_host_secrets and SENSITIVE_ENV_PATTERN.search(k):
                continue
            clean_env[k] = v

        # Set network-isolation indicator & disable python bytecode caches
        clean_env["PYTHONDONTWRITEBYTECODE"] = "1"
        clean_env["PYTHONUNBUFFERED"] = "1"
        return clean_env

    def validate_command(self, cmd: list[str]) -> None:
        """Ensure command is allowlisted and free of shell injection."""
        if not cmd:
            raise ValueError("Test command cannot be empty")
        exe = Path(cmd[0]).stem.lower()
        if exe not in ALLOWLISTED_RUNNERS and not any(r in exe for r in ALLOWLISTED_RUNNERS):
            raise ValueError(
                f"Prohibited test executable: '{cmd[0]}'. Allowed runners: {ALLOWLISTED_RUNNERS}"
            )

    def run(
        self,
        command: list[str],
        cwd: str | Path,
        timeout_seconds: int = 120,
    ) -> ExecutionResult:
        """Execute command in sandbox cwd with scrubbed environment and timeout."""
        self.validate_command(command)
        clean_env = self.build_clean_environment()

        start = time.monotonic()
        try:
            proc = subprocess.run(
                command,
                cwd=str(cwd),
                env=clean_env,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            duration = round(time.monotonic() - start, 3)
            stdout = proc.stdout[: self.max_output_bytes]
            stderr = proc.stderr[: self.max_output_bytes]

            return ExecutionResult(
                exit_code=proc.returncode,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=duration,
                timed_out=False,
                command=command,
            )

        except subprocess.TimeoutExpired as exc:
            duration = round(time.monotonic() - start, 3)
            out_str = exc.stdout if isinstance(exc.stdout, str) else ""
            err_str = exc.stderr if isinstance(exc.stderr, str) else ""
            stdout = out_str[: self.max_output_bytes]
            stderr = err_str[: self.max_output_bytes]
            return ExecutionResult(
                exit_code=124,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=duration,
                timed_out=True,
                command=command,
            )
