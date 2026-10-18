"""Ingest and persist graph artifacts for the frozen five-case subset (A6c/Phase 2).

Builds disk snapshots in artifacts/graphs/ and populates isolated FalkorDB graphs
(requests_<short_sha>) for all 5 subset revisions.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from tracefix.graph.persistence import (
    get_revision_graph_name,
    ingest_and_persist_revision,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest_subset")

SUBSET_PATH = Path("docs/experiments/a6c_subset.json")
REPO_ROOT = Path("data/repos/requests")
REPO_URL = "https://github.com/psf/requests"
SNAPSHOT_DIR = Path("artifacts/graphs")


def main() -> None:
    subset_data = json.loads(SUBSET_PATH.read_text(encoding="utf-8"))
    selected = subset_data.get("selected", [])
    logger.info("Found %d cases to ingest and persist", len(selected))

    manifest_entries = []

    for item in selected:
        case_id = item["case_id"]
        rev = item["revision"]
        logger.info("Processing %s at revision %s", case_id, rev)

        client, result = ingest_and_persist_revision(
            repo_root=REPO_ROOT,
            repo_url=REPO_URL,
            revision=rev,
            snapshot_dir=SNAPSHOT_DIR,
            validate_schema=True,
        )

        graph_name = get_revision_graph_name("requests", rev)
        snapshot_file = SNAPSHOT_DIR / f"requests_{rev[:8]}.json"

        # Read envelope for sha256
        envelope = json.loads(snapshot_file.read_text(encoding="utf-8"))
        sha256 = envelope["sha256"]

        entry = {
            "case_id": case_id,
            "revision": rev,
            "graph_name": graph_name,
            "snapshot_file": str(snapshot_file),
            "sha256": sha256,
            "node_count": len(result.nodes),
            "edge_count": len(result.edges),
            "parse_errors": result.parse_errors,
            "nodes_by_kind": result.stats.get("nodes_by_kind", {}),
            "edges_by_type": result.stats.get("edges_by_type", {}),
            "edges_by_provenance": result.stats.get("edges_by_provenance", {}),
        }
        manifest_entries.append(entry)
        logger.info(
            "Persisted %s: %d nodes, %d edges -> graph %s (sha256: %s...)",
            case_id,
            len(result.nodes),
            len(result.edges),
            graph_name,
            sha256[:12],
        )

    # Save manifest
    manifest_path = SNAPSHOT_DIR / "manifest.json"
    manifest_data = {
        "dataset_fingerprint": subset_data.get("dataset_fingerprint"),
        "raw_rows_sha256": subset_data.get("raw_rows_sha256"),
        "revisions_count": len(manifest_entries),
        "graphs": manifest_entries,
    }
    manifest_path.write_text(json.dumps(manifest_data, indent=2, sort_keys=True), encoding="utf-8")
    logger.info("Saved ingestion manifest to %s", manifest_path)


if __name__ == "__main__":
    main()
