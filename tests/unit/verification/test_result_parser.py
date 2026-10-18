"""Unit tests for test execution output parser (Phase 3)."""

from __future__ import annotations

from tracefix.verification.result_parser import TestResultParser

PYTEST_SAMPLE_PASS = """
tests/unit/test_calc.py .                                                [ 50%]
tests/unit/test_core.py .                                                [100%]

============================== 2 passed in 0.12s ==============================
"""

PYTEST_SAMPLE_FAIL = """
tests/unit/test_calc.py .                                                [ 50%]
tests/unit/test_core.py F                                                [100%]

=================================== FAILURES ===================================
__________________________________ test_fail ___________________________________
    def test_fail():
>       assert False
E       assert False

tests/unit/test_core.py:5: AssertionError
=========================== short test summary info ===========================
FAILED tests/unit/test_core.py::test_fail - assert False
========================= 1 failed, 1 passed in 0.25s =========================
"""

PYTEST_SAMPLE_SETUP_ERROR = """
==================================== ERRORS ====================================
___________________ ERROR collecting tests/unit/test_broken.py __________________
ImportError while importing test module 'tests/unit/test_broken.py'.
E   ModuleNotFoundError: No module named 'nonexistent'
=========================== short test summary info ===========================
ERROR tests/unit/test_broken.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
=============================== 1 error in 0.05s ===============================
"""


def test_parse_successful_pytest_output() -> None:
    parser = TestResultParser()
    parsed = parser.parse_pytest(PYTEST_SAMPLE_PASS, "", exit_code=0)
    assert parsed.passed_count == 2
    assert parsed.failed_count == 0
    assert parsed.error_count == 0
    assert not parsed.is_setup_failure
    assert parsed.duration_seconds == 0.12


def test_parse_failing_pytest_output() -> None:
    parser = TestResultParser()
    parsed = parser.parse_pytest(PYTEST_SAMPLE_FAIL, "", exit_code=1)
    assert parsed.passed_count == 1
    assert parsed.failed_count == 1
    assert len(parsed.failed_tests) == 1
    assert "tests/unit/test_core.py::test_fail" in parsed.failed_tests[0]
    assert not parsed.is_setup_failure
    assert parsed.duration_seconds == 0.25


def test_parse_collection_error_as_setup_failure() -> None:
    parser = TestResultParser()
    parsed = parser.parse_pytest(PYTEST_SAMPLE_SETUP_ERROR, "", exit_code=2)
    assert parsed.is_setup_failure
    assert parsed.error_count == 1
    assert "Syntax or collection error" in parsed.setup_error_details
