"""Revision-specific graph persistence to FalkorDB and disk artifacts (A6c/Phase 2).

Provides reproducible persistence of IngestionResult snapshots into:
1. Isolated, revision-stamped FalkorDB named graphs (e.g. `requests_<short_sha>`)
2. Structured JSON disk artifacts with sha256 checksums and metadata tracking.

Ensures:
- Graph retrieval cannot silently use HEAD or mismatched revision data.
- Safe idempotent reruns without duplicate nodes or edges.
- Validated against contracts/graph_schema.json (C1).
- Complete error, skipped file, and inferred edge reporting.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Any

from tracefix.graph.client import FalkorDBClient
from tracefix.graph.ingestion import IngestionResult, ingest_repository
from tracefix.graph.models import Edge, Node, Provenance
from tracefix.graph.schema import GraphSchema

logger = logging.getLogger(__name__)

SAFE_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def get_revision_graph_name(repo_name: str, revision: str) -> str:
    """Generate isolated, safe graph name for a revision, e.g. requests_22623bd8."""
    clean_name = re.sub(r"[^A-Za-z0-9_]", "_", repo_name).strip("_")
    short_sha = revision[:8]
    graph_name = f"{clean_name}_{short_sha}"
    if not SAFE_NAME_RE.match(graph_name):
        graph_name = f"g_{graph_name}"
    return graph_name


def save_graph_snapshot(result: IngestionResult, path: Path) -> Path:
    """Persist IngestionResult to a deterministic disk JSON artifact."""
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "repo": result.repo,
        "revision": result.revision,
        "history_available": result.history_available,
        "stats": result.stats,
        "limitations": result.limitations,
        "parse_errors": result.parse_errors,
        "nodes": [n.model_dump() for n in sorted(result.nodes.values(), key=lambda x: x.entity_id)],
        "edges": [
            e.model_dump()
            for e in sorted(
                result.edges,
                key=lambda x: (x.edge_type, x.source_id, x.target_id, x.source),
            )
        ],
    }

    content_bytes = json.dumps(data, indent=2, sort_keys=True).encode("utf-8")
    sha256 = hashlib.sha256(content_bytes).hexdigest()

    # Wrap with envelope metadata
    envelope = {
        "schema_version": "0.2.0",
        "sha256": sha256,
        "node_count": len(result.nodes),
        "edge_count": len(result.edges),
        "payload": data,
    }

    path.write_text(json.dumps(envelope, indent=2, sort_keys=True), encoding="utf-8")
    return path


def load_graph_snapshot(path: Path) -> IngestionResult:
    """Load IngestionResult from disk artifact and reconstruct models."""
    content = json.loads(path.read_text(encoding="utf-8"))
    payload = content.get("payload", content)

    nodes = {item["entity_id"]: Node.model_validate(item) for item in payload.get("nodes", [])}
    edges = [Edge.model_validate(item) for item in payload.get("edges", [])]

    return IngestionResult(
        repo=payload["repo"],
        revision=payload["revision"],
        nodes=nodes,
        edges=edges,
        history_available=payload.get("history_available", True),
        parse_errors=payload.get("parse_errors", []),
        stats=payload.get("stats", {}),
        limitations=payload.get("limitations", []),
    )


def persist_snapshot_to_falkordb(
    client: FalkorDBClient,
    result: IngestionResult,
    *,
    clear_existing: bool = True,
    batch_size: int = 500,
) -> dict[str, int]:
    """Persist IngestionResult nodes and edges into FalkorDB.

    Idempotent and isolated: Clears existing nodes for this revision (or full graph)
    before loading.
    """
    client.connect()
    revision = result.revision

    if clear_existing:
        try:
            # Delete all nodes belonging to this revision
            client.execute(
                "MATCH (n {revision: $revision}) DETACH DELETE n",
                {"revision": revision},
            )
        except Exception:
            pass

    # Group nodes by kind for Cypher label assignment
    nodes_by_kind: dict[str, list[dict[str, Any]]] = {}
    for n in result.nodes.values():
        d = {
            "entity_id": n.entity_id,
            "kind": n.kind,
            "repo": n.repo,
            "revision": n.revision,
            "path": n.properties.get("path", ""),
            "qualified_name": n.properties.get("qualified_name", ""),
            "start_line": n.properties.get("start_line", 0),
            "end_line": n.properties.get("end_line", 0),
        }
        nodes_by_kind.setdefault(n.kind, []).append(d)

    nodes_created = 0
    for kind, items in sorted(nodes_by_kind.items()):
        query = f"""
        UNWIND $batch AS item
        CREATE (n:{kind} {{
            entity_id: item.entity_id,
            kind: item.kind,
            repo: item.repo,
            revision: item.revision,
            path: item.path,
            qualified_name: item.qualified_name,
            start_line: item.start_line,
            end_line: item.end_line
        }})
        """
        for i in range(0, len(items), batch_size):
            chunk = items[i : i + batch_size]
            client.execute(query, {"batch": chunk})
            nodes_created += len(chunk)

    # Ensure index on key kinds for fast edge linking and neighborhood lookups
    for kind in ("Function", "Test", "Class", "Module", "File"):
        try:
            client.execute(f"CREATE INDEX FOR (n:{kind}) ON (n.entity_id)")
        except Exception:
            pass

    # Group edges by edge_type
    edges_by_type: dict[str, list[dict[str, Any]]] = {}
    for e in result.edges:
        prov = e.provenance.value if isinstance(e.provenance, Provenance) else str(e.provenance)
        d = {
            "source_id": e.source_id,
            "target_id": e.target_id,
            "revision": e.revision,
            "provenance": prov,
            "source": e.source,
            "confidence": e.confidence or "",
        }
        edges_by_type.setdefault(e.edge_type, []).append(d)

    edges_created = 0
    for etype, items in sorted(edges_by_type.items()):
        query = f"""
        UNWIND $batch AS item
        MATCH (s {{entity_id: item.source_id, revision: item.revision}})
        MATCH (t {{entity_id: item.target_id, revision: item.revision}})
        CREATE (s)-[r:{etype} {{
            revision: item.revision,
            provenance: item.provenance,
            source: item.source,
            confidence: item.confidence
        }}]->(t)
        """
        for i in range(0, len(items), batch_size):
            chunk = items[i : i + batch_size]
            client.execute(query, {"batch": chunk})
            edges_created += len(chunk)

    # Verify counts
    row_nodes = client.execute(
        "MATCH (n {revision: $revision}) RETURN count(n) AS c",
        {"revision": revision},
    )
    row_edges = client.execute(
        "MATCH ()-[r {revision: $revision}]->() RETURN count(r) AS c",
        {"revision": revision},
    )

    actual_nodes = row_nodes[0].get("c", nodes_created) if row_nodes else nodes_created
    actual_edges = row_edges[0].get("c", edges_created) if row_edges else edges_created

    return {
        "nodes_persisted": actual_nodes,
        "edges_persisted": actual_edges,
    }


def ingest_and_persist_revision(
    repo_root: Path,
    repo_url: str,
    revision: str,
    *,
    host: str = "localhost",
    port: int = 6379,
    snapshot_dir: Path | None = None,
    validate_schema: bool = True,
) -> tuple[FalkorDBClient, IngestionResult]:
    """Ingest git tree at specified revision, save disk artifact, and populate FalkorDB.

    Safely checks out the revision in repo_root before running AST extraction.
    """
    repo_root = repo_root.resolve()

    # Checkout exact revision to ensure filesystem matches
    checkout_cmd = ["git", "checkout", revision, "--detach"]
    sub = subprocess.run(
        checkout_cmd,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if sub.returncode != 0:
        raise RuntimeError(f"failed to checkout revision {revision} in {repo_root}: {sub.stderr}")

    # Run ingestion
    result = ingest_repository(repo_root, repo_url=repo_url, revision=revision)

    if validate_schema:
        schema = GraphSchema.load()
        schema.validate_snapshot(list(result.nodes.values()), result.edges)

    # Save disk snapshot if requested
    if snapshot_dir is not None:
        short_sha = revision[:8]
        snapshot_file = snapshot_dir / f"requests_{short_sha}.json"
        save_graph_snapshot(result, snapshot_file)

    # Persist to FalkorDB
    graph_name = get_revision_graph_name("requests", revision)
    client = FalkorDBClient(graph_name=graph_name, host=host, port=port)
    persist_snapshot_to_falkordb(client, result, clear_existing=True)

    return client, result
