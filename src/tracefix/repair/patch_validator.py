"""Strict patch validation and safety policy enforcement (Phase 2).

Complies with contracts/repair.json (C5).
"""

from __future__ import annotations

import fnmatch
from pathlib import PurePath, PurePosixPath

from tracefix.repair.interfaces import CandidatePatch, ValidationResult

DEFAULT_PROHIBITED_PATTERNS = [
    ".git/*",
    ".git",
    ".github/*",
    ".circleci/*",
    ".travis.yml",
    "tox.ini",
    "*.env*",
    "*.pem",
    "*.key",
    "*.secret",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
]


class PatchValidator:
    """Validates candidate patches for safety, path containment, and size bounds."""

    def __init__(
        self,
        max_changed_files: int = 5,
        max_changed_lines: int = 200,
        max_hunks_per_file: int = 10,
        prohibited_patterns: list[str] | None = None,
    ) -> None:
        self.max_changed_files = max_changed_files
        self.max_changed_lines = max_changed_lines
        self.max_hunks_per_file = max_hunks_per_file
        self.prohibited_patterns = (
            prohibited_patterns
            if prohibited_patterns is not None
            else list(DEFAULT_PROHIBITED_PATTERNS)
        )

    def is_path_safe(self, file_path: str) -> tuple[bool, str | None]:
        """Check if file path is safe and stays within repository root."""
        clean = file_path.strip().replace("\\", "/")

        # Disallow empty or null paths
        if not clean or clean == "unknown":
            return False, "Empty or undefined file path"

        # Disallow absolute paths
        if clean.startswith("/") or (len(clean) >= 2 and clean[1] == ":"):
            return False, f"Absolute path prohibited: {clean}"

        # Disallow path traversal
        path_obj = PurePath(clean)
        parts = path_obj.parts
        if ".." in parts or "." in parts:
            return False, f"Path traversal sequence prohibited: {clean}"

        # Check against prohibited patterns
        posix_str = PurePosixPath(clean).as_posix()
        for pattern in self.prohibited_patterns:
            if fnmatch.fnmatch(posix_str, pattern) or fnmatch.fnmatch(path_obj.name, pattern):
                return False, f"Prohibited file modification: {clean} matches '{pattern}'"

        return True, None

    def validate(
        self, candidate_patch: CandidatePatch, base_revision: str = ""
    ) -> ValidationResult:
        """Execute strict safety and bounds checks on candidate patch."""
        errors: list[str] = []
        prohibited_files: list[str] = []
        warnings: list[str] = []

        # 1. Check path safety & prohibited files
        for path in candidate_patch.files_touched:
            safe, reason = self.is_path_safe(path)
            if not safe:
                errors.append(reason or f"Unsafe path: {path}")
                for pattern in self.prohibited_patterns:
                    if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(
                        PurePath(path).name, pattern
                    ):
                        prohibited_files.append(path)

        # 2. Check bounds on changed files
        if len(candidate_patch.files_touched) > self.max_changed_files:
            errors.append(
                f"Patch modifies {len(candidate_patch.files_touched)} files, "
                f"exceeding maximum bound of {self.max_changed_files}"
            )

        # 3. Check bounds on changed lines
        total_changed_lines = candidate_patch.lines_added + candidate_patch.lines_deleted
        if total_changed_lines > self.max_changed_lines:
            errors.append(
                f"Patch modifies {total_changed_lines} lines "
                f"({candidate_patch.lines_added} added, {candidate_patch.lines_deleted} deleted), "
                f"exceeding maximum bound of {self.max_changed_lines}"
            )

        # 4. Check for empty diff
        if total_changed_lines == 0:
            errors.append("Patch contains 0 additions and 0 deletions (empty diff)")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            prohibited_files=sorted(set(prohibited_files)),
            warnings=warnings,
        )
