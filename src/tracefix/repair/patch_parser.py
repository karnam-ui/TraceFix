"""Unified diff parser for candidate patch representations (Phase 2).

Complies with contracts/repair.json (C5).
"""

from __future__ import annotations

import hashlib
import re

from pydantic import BaseModel, Field

from tracefix.repair.interfaces import CandidatePatch, PatchValidationError

HUNK_HEADER_RE = re.compile(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@(.*)$")


class DiffHunk(BaseModel):
    """A single hunk within a file diff."""

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    header: str
    lines: list[str] = Field(default_factory=list)


class FileDiff(BaseModel):
    """Diff operations targeting a single file."""

    old_path: str
    new_path: str
    hunks: list[DiffHunk] = Field(default_factory=list)
    lines_added: int = 0
    lines_deleted: int = 0
    is_new: bool = False
    is_deleted: bool = False


class PatchParser:
    """Robust parser for model-generated unified diffs.

    Tolerates Markdown formatting, code fences, and introductory prose while
    extracting clean diff hunks.
    """

    def extract_diff_block(self, raw_output: str) -> str:
        """Extract the unified diff text from model output."""
        cleaned = raw_output.strip()

        # Check for code fences
        if "```diff" in cleaned:
            parts = cleaned.split("```diff", 1)[1].split("```", 1)
            diff_text = parts[0].strip()
        elif "```patch" in cleaned:
            parts = cleaned.split("```patch", 1)[1].split("```", 1)
            diff_text = parts[0].strip()
        elif "```" in cleaned:
            parts = cleaned.split("```", 1)[1].split("```", 1)
            diff_text = parts[0].strip()
        else:
            diff_text = cleaned

        # If diff starts after conversational text, find the first diff marker
        diff_markers = ("diff --git", "--- a/", "--- ")
        for marker in diff_markers:
            if marker in diff_text:
                idx = diff_text.index(marker)
                diff_text = diff_text[idx:].strip()
                break

        if not diff_text:
            raise PatchValidationError("Model output contains no unified diff")

        return diff_text

    def parse(self, raw_output: str, source_model: str = "unknown") -> CandidatePatch:
        """Parse raw model output into a structured CandidatePatch."""
        diff_text = self.extract_diff_block(raw_output)
        lines = diff_text.splitlines()

        file_diffs: list[FileDiff] = []
        current_file: FileDiff | None = None
        current_hunk: DiffHunk | None = None

        total_added = 0
        total_deleted = 0
        hunk_count = 0

        for line in lines:
            if line.startswith("diff --git"):
                # Save prior hunk and file
                if current_hunk and current_file:
                    current_file.hunks.append(current_hunk)
                    current_hunk = None
                if current_file:
                    file_diffs.append(current_file)

                # Parse git diff paths: diff --git a/path b/path
                parts = line.split(" ")
                if len(parts) >= 4:
                    old_p = parts[2].removeprefix("a/").removeprefix("b/")
                    new_p = parts[3].removeprefix("b/").removeprefix("a/")
                else:
                    old_p = "unknown"
                    new_p = "unknown"

                current_file = FileDiff(old_path=old_p, new_path=new_p)

            elif line.startswith("--- "):
                path = line[4:].strip().removeprefix("a/").removeprefix("b/")
                if current_file is None:
                    current_file = FileDiff(old_path=path, new_path=path)
                else:
                    current_file.old_path = path

            elif line.startswith("+++ "):
                path = line[4:].strip().removeprefix("b/").removeprefix("a/")
                if current_file is None:
                    current_file = FileDiff(old_path=path, new_path=path)
                else:
                    current_file.new_path = path

            elif line.startswith("@@"):
                if current_file is None:
                    current_file = FileDiff(old_path="unknown", new_path="unknown")

                if current_hunk:
                    current_file.hunks.append(current_hunk)

                match = HUNK_HEADER_RE.match(line)
                if not match:
                    raise PatchValidationError(f"Malformed hunk header: {line}")

                old_start = int(match.group(1))
                old_count = int(match.group(2)) if match.group(2) else 1
                new_start = int(match.group(3))
                new_count = int(match.group(4)) if match.group(4) else 1

                current_hunk = DiffHunk(
                    old_start=old_start,
                    old_count=old_count,
                    new_start=new_start,
                    new_count=new_count,
                    header=line,
                )
                hunk_count += 1

            elif current_hunk is not None:
                current_hunk.lines.append(line)
                if line.startswith("+") and not line.startswith("+++"):
                    total_added += 1
                    if current_file:
                        current_file.lines_added += 1
                elif line.startswith("-") and not line.startswith("---"):
                    total_deleted += 1
                    if current_file:
                        current_file.lines_deleted += 1

        if current_hunk and current_file:
            current_file.hunks.append(current_hunk)
        if current_file:
            file_diffs.append(current_file)

        if not file_diffs:
            raise PatchValidationError("Failed to parse any valid file diffs from model output")

        files_touched = sorted(
            {fd.new_path for fd in file_diffs if fd.new_path != "/dev/null"}
            | {fd.old_path for fd in file_diffs if fd.old_path != "/dev/null"}
        )

        patch_hash = hashlib.sha256(diff_text.encode("utf-8")).hexdigest()

        return CandidatePatch(
            patch_id=f"patch_{patch_hash[:16]}",
            raw_diff=diff_text,
            files_touched=files_touched,
            hunk_count=max(1, hunk_count),
            lines_added=total_added,
            lines_deleted=total_deleted,
            format="unified_diff",
            source_model=source_model,
        )
