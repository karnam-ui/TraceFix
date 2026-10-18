"""Adapter exposing eligible incident memories to retrieval pipelines (Phase 4).

Complies with contracts/context_manifest.json (C3) and contracts/retrieval.json (C2).
"""

from __future__ import annotations

from typing import Any

from tracefix.graph.models import Provenance
from tracefix.memory.models import IncidentRecord
from tracefix.memory.repository import IncidentMemoryRepository
from tracefix.retrieval.interfaces import EvidenceTarget, RankedItem


class IncidentMemoryRetrievalAdapter:
    """Exposes verified historical bug fixes as ranked evidence items."""

    def __init__(self, repository: IncidentMemoryRepository) -> None:
        self.repository = repository

    def retrieve_as_ranked_items(
        self,
        query_text: str,
        as_of_time: str,
        repo: str = "",
        top_k: int = 5,
    ) -> list[RankedItem]:
        """Query eligible records and convert to standard RankedItem instances."""
        records = self.repository.query_eligible(
            query_text=query_text,
            as_of_time=as_of_time,
            repo=repo,
            limit=top_k,
        )

        ranked: list[RankedItem] = []
        for rank, rec in enumerate(records, start=1):
            target_file = (
                rec.retrieved_evidence_ids[0] if rec.retrieved_evidence_ids else "incident_memory"
            )
            item = RankedItem(
                evidence_id=f"mem_{rec.incident_id}",
                strategy="incident_memory",
                rank=rank,
                score=round(1.0 / rank, 3),
                target=EvidenceTarget(file=target_file, symbol=rec.case_id),
                source_revision=rec.revision,
                provenance=Provenance.OBSERVED,
                source="verified_incident_memory",
            )
            ranked.append(item)

        return ranked

    def to_evidence_items(self, records: list[IncidentRecord]) -> list[dict[str, Any]]:
        """Format eligible records as context manifest evidence items."""
        evidence_items: list[dict[str, Any]] = []
        for rank, rec in enumerate(records, start=1):
            snippet = (
                f"# Prior Verified Fix for {rec.case_id}\n"
                f"# Base Revision: {rec.revision}\n"
                f"{rec.patch_diff}"
            )
            item = {
                "evidence_id": f"mem_{rec.incident_id}",
                "evidence_type": "incident_memory",
                "repo": rec.repo,
                "revision": rec.revision,
                "file_path": f"incident_memories/{rec.case_id}.patch",
                "symbol": rec.case_id,
                "strategy": "incident_memory",
                "rank": rank,
                "score": round(1.0 / rank, 3),
                "selection_reason": "prior_verified_fix",
                "content": snippet,
                "token_contribution": max(1, len(snippet) // 4),
                "provenance": "observed",
                "source": "verified_incident_memory",
            }
            evidence_items.append(item)
        return evidence_items
