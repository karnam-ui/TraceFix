"""Unit tests for unified diff parsing (Phase 2)."""

from __future__ import annotations

import pytest

from tracefix.repair.interfaces import PatchValidationError
from tracefix.repair.patch_parser import PatchParser


def test_parse_standard_git_diff() -> None:
    diff_text = (
        "diff --git a/requests/models.py b/requests/models.py\n"
        "--- a/requests/models.py\n"
        "+++ b/requests/models.py\n"
        "@@ -386,2 +386,3 @@\n"
        "- self.headers['Content-Length'] = '0'\n"
        "+ if self.method not in ('GET', 'HEAD'):\n"
        "+     self.headers['Content-Length'] = '0'\n"
    )
    parser = PatchParser()
    patch = parser.parse(diff_text, source_model="claude-3.5")
    assert patch.files_touched == ["requests/models.py"]
    assert patch.lines_added == 2
    assert patch.lines_deleted == 1
    assert patch.hunk_count == 1
    assert patch.source_model == "claude-3.5"
    assert patch.patch_id.startswith("patch_")


def test_parse_fenced_markdown_diff() -> None:
    raw = (
        "Here is the candidate patch for the issue:\n\n"
        "```diff\n"
        "diff --git a/calc/core.py b/calc/core.py\n"
        "--- a/calc/core.py\n"
        "+++ b/calc/core.py\n"
        "@@ -10,3 +10,3 @@\n"
        "-    return a - b\n"
        "+    return a + b\n"
        "```\n\n"
        "Hope this helps!"
    )
    parser = PatchParser()
    patch = parser.parse(raw)
    assert patch.files_touched == ["calc/core.py"]
    assert patch.lines_added == 1
    assert patch.lines_deleted == 1
    assert "Hope this helps" not in patch.raw_diff


def test_parse_multi_file_diff() -> None:
    raw = (
        "diff --git a/a.py b/a.py\n"
        "--- a/a.py\n"
        "+++ b/a.py\n"
        "@@ -1,1 +1,2 @@\n"
        "-x = 1\n"
        "+x = 2\n"
        "+y = 3\n"
        "diff --git a/b.py b/b.py\n"
        "--- a/b.py\n"
        "+++ b/b.py\n"
        "@@ -5,2 +5,1 @@\n"
        "-old1\n"
        "-old2\n"
        "+new\n"
    )
    parser = PatchParser()
    patch = parser.parse(raw)
    assert patch.files_touched == ["a.py", "b.py"]
    assert patch.lines_added == 3
    assert patch.lines_deleted == 3
    assert patch.hunk_count == 2


def test_empty_diff_raises_error() -> None:
    parser = PatchParser()
    with pytest.raises(PatchValidationError, match="Failed to parse any valid file diffs"):
        parser.parse("Just some random text with no diff block.")


def test_malformed_hunk_header_raises_error() -> None:
    raw = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ malformed header @@\n+new\n"
    parser = PatchParser()
    with pytest.raises(PatchValidationError, match="Malformed hunk header"):
        parser.parse(raw)
