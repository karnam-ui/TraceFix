"""Unit tests for TraceFix FastAPI endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tracefix.api.app import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_endpoint(client: TestClient) -> None:
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("ok", "degraded")
    assert data["version"] == "0.0.1"
    assert "falkordb_connected" in data
    assert "active_cases_count" in data
    assert data["active_cases_count"] >= 5


def test_list_cases_endpoint(client: TestClient) -> None:
    res = client.get("/api/cases")
    assert res.status_code == 200
    cases = res.json()
    assert isinstance(cases, list)
    assert len(cases) >= 5
    first = cases[0]
    assert "case_id" in first
    assert "revision" in first
    assert "localizable" in first
    assert "bug_report_preview" in first


def test_list_graphs_endpoint(client: TestClient) -> None:
    res = client.get("/api/graphs")
    assert res.status_code == 200
    graphs = res.json()
    assert isinstance(graphs, list)
    assert len(graphs) >= 5
    first = graphs[0]
    assert "graph_name" in first
    assert "node_count" in first
    assert "edge_count" in first


def test_investigate_endpoint(client: TestClient) -> None:
    payload = {
        "case_id": "psf__requests-1142",
        "strategy": "graph",
        "budget": 4000,
        "mock": True,
        "execute_repair": True,
    }
    res = client.post("/api/investigate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["case_id"] == "psf__requests-1142"
    assert data["strategy_used"] == "graph"
    assert len(data["stages"]) >= 6
    assert len(data["retrieval"]) > 0
    assert "tokens_used" in data["context_budget"]
    assert data["proposed_patch"] is not None
    assert data["verification"]["status"] == "VERIFIED"


def test_list_evaluations_endpoint(client: TestClient) -> None:
    res = client.get("/api/evaluations")
    assert res.status_code == 200
    evals = res.json()
    assert isinstance(evals, list)
    assert len(evals) > 0
    assert any("retrieval_pilot_report" in e["file_name"] for e in evals)


def test_neighborhood_endpoint(client: TestClient) -> None:
    res = client.get("/api/graphs/requests_22623bd8/neighborhood")
    assert res.status_code == 200
    data = res.json()
    assert data["graph_name"] == "requests_22623bd8"
    assert "nodes" in data
    assert "edges" in data


def test_memory_endpoint(client: TestClient) -> None:
    res = client.get("/api/memory")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
