"""Parser for pytest and unittest execution output (Phase 3).

Complies with contracts/verification.json (C6).
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

PASSED_RE = re.compile(r"(\d+)\s+passed")
FAILED_RE = re.compile(r"(\d+)\s+failed")
SKIPPED_RE = re.compile(r"(\d+)\s+skipped")
ERRORS_RE = re.compile(r"(\d+)\s+error")
DURATION_RE = re.compile(r"in\s+([0-9\.]+)s")

PYTEST_FAILED_LINE_RE = re.compile(r"^FAILED\s+([^\s]+)")
PYTEST_ERROR_LINE_RE = re.compile(r"^ERROR\s+([^\s]+)")


class ParsedOutput(BaseModel):
    """Structured extraction of test runner output."""

    passed_tests: list[str] = Field(default_factory=list)
    failed_tests: list[str] = Field(default_factory=list)
    skipped_tests: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    passed_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    total_count: int = 0
    duration_seconds: float = 0.0
    is_setup_failure: bool = False
    setup_error_details: str = ""


class TestResultParser:
    """Parses standard test execution logs into structured test counts."""

    def parse_pytest(self, stdout: str, stderr: str, exit_code: int) -> ParsedOutput:
        passed_tests: list[str] = []
        failed_tests: list[str] = []
        skipped_tests: list[str] = []
        errors: list[str] = []

        is_setup_failure = False
        setup_error_details = ""

        # Check for syntax or collection errors
        has_error_token = (
            "ERRORS" in stdout
            or "ModuleNotFoundError" in stderr
            or "SyntaxError" in stderr
            or "SyntaxError" in stdout
        )
        if exit_code != 0 and has_error_token:
            if "= ERRORS =" in stdout or "SyntaxError" in stdout or "SyntaxError" in stderr:
                is_setup_failure = True
                setup_error_details = "Syntax or collection error prevented test execution"

        for line in stdout.splitlines():
            line_s = line.strip()
            fail_m = PYTEST_FAILED_LINE_RE.match(line_s)
            if fail_m:
                failed_tests.append(fail_m.group(1))
            err_m = PYTEST_ERROR_LINE_RE.match(line_s)
            if err_m:
                errors.append(err_m.group(1))

        passed_count = 0
        failed_count = len(failed_tests)
        skipped_count = 0
        error_count = len(errors)
        duration_s = 0.0

        for line in reversed(stdout.splitlines()):
            if line.startswith("=") and line.endswith("=") and "in " in line:
                pm = PASSED_RE.search(line)
                if pm:
                    passed_count = int(pm.group(1))
                fm = FAILED_RE.search(line)
                if fm:
                    failed_count = int(fm.group(1))
                sm = SKIPPED_RE.search(line)
                if sm:
                    skipped_count = int(sm.group(1))
                em = ERRORS_RE.search(line)
                if em:
                    error_count = int(em.group(1))
                dm = DURATION_RE.search(line)
                if dm:
                    duration_s = float(dm.group(1))
                break

        if is_setup_failure and error_count > 0 and (passed_count + failed_count) == 0:
            is_setup_failure = True

        total = passed_count + failed_count + skipped_count + error_count

        return ParsedOutput(
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            skipped_tests=skipped_tests,
            errors=errors,
            passed_count=passed_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
            error_count=error_count,
            total_count=total,
            duration_seconds=duration_s,
            is_setup_failure=is_setup_failure,
            setup_error_details=setup_error_details,
        )
