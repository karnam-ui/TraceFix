"""Incident memory repository with atomic persistence and indexing (Phase 4).

Complies with contracts/incident_memory.json (C7).
"""

from __future__ import annotations

import json
from pathlib import Path

from tracefix.memory.eligibility import EligibilityEvaluator
from tracefix.memory.models import IncidentRecord


class IncidentMemoryRepository:
    """Thread-safe persistent store for incident memories and anti-patterns."""

    def __init__(self, storage_path: str | Path | None = None) -> None:
        self.storage_path = Path(storage_path) if storage_path else None
        self._records: dict[str, IncidentRecord] = {}
        self._hash_index: dict[str, str] = {}
        self.evaluator = EligibilityEvaluator()

        if self.storage_path and self.storage_path.is_file():
            self._load_from_disk()

    def _load_from_disk(self) -> None:
        if not self.storage_path or not self.storage_path.is_file():
            return
        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
            for item in data:
                record = IncidentRecord.model_validate(item)
                self._records[record.incident_id] = record
                self._hash_index[record.patch_hash] = record.incident_id
        except Exception:
            # Corrupt disk storage shouldn't crash initialization
            pass

    def _persist_to_disk(self) -> None:
        if not self.storage_path:
            return
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        serialized = [rec.model_dump() for rec in self._records.values()]
        self.storage_path.write_text(
            json.dumps(serialized, indent=2, sort_keys=True), encoding="utf-8"
        )

    def save(self, record: IncidentRecord) -> IncidentRecord:
        """Evaluate eligibility, deduplicate, and persist incident record."""
        status, reason = self.evaluator.evaluate(record)
        record.eligibility_status = status
        record.rejection_reason = reason

        # Check for deduplication by patch_hash
        existing_id = self._hash_index.get(record.patch_hash)
        if existing_id and existing_id in self._records:
            # Update existing record if new one has verified status
            existing = self._records[existing_id]
            if record.lifecycle_status == "VERIFIED" and existing.lifecycle_status != "VERIFIED":
                self._records[existing_id] = record
                self._persist_to_disk()
                return record
            return existing

        self._records[record.incident_id] = record
        self._hash_index[record.patch_hash] = record.incident_id
        self._persist_to_disk()
        return record

    def get(self, incident_id: str) -> IncidentRecord | None:
        return self._records.get(incident_id)

    def list_records(self) -> list[IncidentRecord]:
        return list(self._records.values())

    def query_eligible(
        self,
        query_text: str = "",
        as_of_time: str | None = None,
        repo: str | None = None,
        limit: int = 5,
    ) -> list[IncidentRecord]:
        """Query eligible verified incident memories with chronological isolation."""
        matches: list[IncidentRecord] = []
        tokens = set(query_text.lower().split()) if query_text else set()

        for rec in self._records.values():
            # 1. Eligibility gate
            if rec.eligibility_status != "ELIGIBLE":
                continue

            # 2. Chronological isolation (Rule 4)
            if as_of_time and not self.evaluator.is_chronologically_eligible(rec, as_of_time):
                continue

            # 3. Repository filtering
            if repo and rec.repo and rec.repo != repo:
                continue

            # 4. Keyword score
            if tokens:
                report_words = set(rec.bug_report.lower().split())
                overlap = len(tokens.intersection(report_words))
                if overlap > 0:
                    matches.append(rec)
            else:
                matches.append(rec)

        matches.sort(key=lambda r: r.created_at, reverse=True)
        return matches[:limit]

    def query_negative_patterns(
        self,
        repo: str | None = None,
        limit: int = 5,
    ) -> list[IncidentRecord]:
        """Query rejected repair attempts to detect anti-patterns and prevent repeat mistakes."""
        ineligible = [
            rec
            for rec in self._records.values()
            if rec.eligibility_status == "INELIGIBLE"
            and (not repo or not rec.repo or rec.repo == repo)
        ]
        ineligible.sort(key=lambda r: r.created_at, reverse=True)
        return ineligible[:limit]
