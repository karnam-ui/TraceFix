"""Unit tests for patch safety validation and bounds enforcement (Phase 2)."""

from __future__ import annotations

import pytest

from tracefix.repair.interfaces import CandidatePatch
from tracefix.repair.patch_validator import PatchValidator


def _make_patch(
    files: list[str],
    lines_added: int = 1,
    lines_deleted: int = 1,
) -> CandidatePatch:
    return CandidatePatch(
        patch_id="test_patch",
        raw_diff="diff --git a/a b/b\n",
        files_touched=files,
        lines_added=lines_added,
        lines_deleted=lines_deleted,
    )


def test_valid_patch_passes_validation() -> None:
    validator = PatchValidator()
    patch = _make_patch(["src/tracefix/core.py", "src/tracefix/utils.py"])
    result = validator.validate(patch)
    assert result.is_valid
    assert len(result.errors) == 0
    assert len(result.prohibited_files) == 0


@pytest.mark.parametrize(
    "traversal_path",
    [
        "../secret.py",
        "../../etc/passwd",
        "src/../../danger.py",
        "nested/path/../forbidden.py",
    ],
)
def test_path_traversal_rejected(traversal_path: str) -> None:
    validator = PatchValidator()
    patch = _make_patch([traversal_path])
    result = validator.validate(patch)
    assert not result.is_valid
    assert any("traversal" in err.lower() for err in result.errors)


@pytest.mark.parametrize(
    "abs_path",
    [
        "/etc/shadow",
        "/var/run/docker.sock",
        "C:\\Windows\\System32\\cmd.exe",
        "D:/code/secrets.env",
    ],
)
def test_absolute_paths_rejected(abs_path: str) -> None:
    validator = PatchValidator()
    patch = _make_patch([abs_path])
    result = validator.validate(patch)
    assert not result.is_valid
    assert any("absolute" in err.lower() for err in result.errors)


@pytest.mark.parametrize(
    "prohibited_file",
    [
        ".git/config",
        ".github/workflows/ci.yml",
        ".circleci/config.yml",
        ".travis.yml",
        "tox.ini",
        ".env",
        ".env.local",
        "secrets.key",
        "private.pem",
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
    ],
)
def test_prohibited_files_rejected(prohibited_file: str) -> None:
    validator = PatchValidator()
    patch = _make_patch([prohibited_file])
    result = validator.validate(patch)
    assert not result.is_valid
    assert prohibited_file in result.prohibited_files
    assert any("prohibited" in err.lower() for err in result.errors)


def test_max_changed_files_bound_enforced() -> None:
    validator = PatchValidator(max_changed_files=3)
    patch = _make_patch(["f1.py", "f2.py", "f3.py", "f4.py"])
    result = validator.validate(patch)
    assert not result.is_valid
    assert any("exceeding maximum bound of 3" in err for err in result.errors)


def test_max_changed_lines_bound_enforced() -> None:
    validator = PatchValidator(max_changed_lines=50)
    patch = _make_patch(["f.py"], lines_added=30, lines_deleted=25)
    result = validator.validate(patch)
    assert not result.is_valid
    assert any("modifies 55 lines" in err for err in result.errors)


def test_empty_diff_rejected() -> None:
    validator = PatchValidator()
    patch = _make_patch(["f.py"], lines_added=0, lines_deleted=0)
    result = validator.validate(patch)
    assert not result.is_valid
    assert any("0 additions and 0 deletions" in err for err in result.errors)
