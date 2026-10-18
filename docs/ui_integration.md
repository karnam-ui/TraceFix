# TraceFix — UI Architecture & Backend Integration Contract

**Document Version:** 1.0.0  
**Status:** Implemented & Verified  
**Date:** 2026-10-18  

---

## 1. System Overview

TraceFix provides a professional developer workspace for investigating bug reports, localizing relevant code via graph-guided and lexical retrieval, budgeting context, strictly validating proposed patches, verifying fixes in isolated sandboxes, and accumulating verified repair knowledge into incident memory (Part B).

The user interface connects directly to a typed FastAPI service (`tracefix.api.app:app`), which orchestrates real Python engine components (`tracefix.graph`, `tracefix.retrieval`, `tracefix.repair`, `tracefix.verification`, `tracefix.memory`, and `tracefix.evaluation`).

```
┌────────────────────────────────────────────────────────┐
│             TraceFix React/TS Workspace                │
│ (AppHeader, Form, Timeline, Evidence, Diff, Memory)    │
└───────────────────────────┬────────────────────────────┘
                            │ HTTP / JSON (REST)
┌───────────────────────────▼────────────────────────────┐
│              FastAPI Backend (tracefix.api)            │
│  /api/health, /api/cases, /api/investigate, /api/memory│
└──────┬────────────────────┬────────────────────┬───────┘
       │                    │                    │
┌──────▼───────┐     ┌──────▼───────┐     ┌──────▼───────┐
│  FalkorDB    │     │ AST & Git    │     │ Incident     │
│  (port 6379) │     │ Worktree     │     │ Memory Repo  │
│  Named Graph │     │ Sandbox      │     │ (Part B)     │
└──────────────┘     └──────────────┘     └──────────────┘
```

---

## 2. API Contract & Endpoints

### `GET /api/health`
Probes live environment services and returns system connectivity.
- **Request:** None
- **Response:**
  ```json
  {
    "status": "ok",
    "version": "0.0.1",
    "falkordb_connected": true,
    "redis_endpoint": "localhost:6379",
    "active_cases_count": 44,
    "persisted_graphs_count": 5,
    "incident_memory_count": 0
  }
  ```

### `GET /api/cases`
Returns the frozen benchmark evaluation cases from `eval/cases/requests_swe_bench_candidates.json`.
- **Response:** Array of `CaseSummary` objects (`case_id`, `repo`, `revision`, `short_sha`, `localizable`, `bug_report_preview`, `ground_truth_files`, `ground_truth_functions`).

### `GET /api/graphs`
Returns metadata of historical base-revision graphs persisted in FalkorDB and disk snapshots.
- **Response:** Array of `GraphSummary` (`graph_name`, `revision`, `node_count`, `edge_count`, `sha256`).

### `GET /api/graphs/{graph_name}/neighborhood?entity_id=...`
Queries the live FalkorDB Cypher database for 1-hop and 2-hop graph relationships around a selected function, class, or module.
- **Response:** `NeighborhoodResponse` (`nodes`: list of `NodeDetail`, `edges`: list of `EdgeDetail`).

### `POST /api/investigate`
Executes an end-to-end investigation across all lifecycle stages.
- **Request:**
  ```json
  {
    "case_id": "psf__requests-1142",
    "repo": "requests",
    "revision": "22623bd8c265b78b161542663ee980738441c307",
    "bug_report": "Optional custom description or derived from case_id",
    "strategy": "graph",
    "budget": 4000,
    "mock": true,
    "execute_repair": true
  }
  ```
- **Lifecycle Stages Executed:**
  1. `stage_1_parse`: Bug report accepted & query formed.
  2. `stage_2_retrieval`: Codebase localization via chosen strategy (Graph-Guided, Fused RRF, Lexical BM25, or Incident Memory).
  3. `stage_3_context`: Context manifest selection & strict token budget accounting.
  4. `stage_4_memory_read`: Incident memory query with chronological isolation (Rule 4: no future leakage).
  5. `stage_5_repair`: Candidate patch generation & AST safety validation (`is_valid`, prohibited patterns, traversal bounds).
  6. `stage_6_verify`: Test execution in isolated sandbox.
  7. `stage_7_memory_write`: Storage of verified patch diff and test evidence into `IncidentMemoryRepository` (Part B).
- **Response:** `InvestigateResponse` containing stages, ranked evidence items, context budget utilization, unified diff patch, verification summary, and memory matches.

### `GET /api/memory`
Returns all verified incident records stored in Part B's incident memory.

### `GET /api/evaluations` & `GET /api/evaluations/{report_name}`
Exposes stored research experiment reports (`retrieval_pilot_report.json`, `repair_evaluation_report.json`, `budget_8k_evaluation_report.json`).

---

## 3. UI Component Architecture

The frontend is structured in `frontend/src/`:
- `App.tsx`: Top-level application coordinator managing active tab, health polling, and investigation state.
- `components/AppHeader.tsx`: Identity banner, tab navigation, and live FalkorDB connection status badge.
- `components/BugInvestigationForm.tsx`: Case selector, strategy picker, budget configuration, and duplicate-submit prevention.
- `components/InvestigationTimeline.tsx`: Real-time lifecycle stage cards with elapsed milliseconds and status icons.
- `components/EvidenceExplorer.tsx`: Filterable table of retrieved evidence items with ground truth hit markers.
- `components/ContextBudgetPanel.tsx`: Compact budget utilization bar, itemized inclusions, and explicit exclusion reasons.
- `components/PatchVerificationPanel.tsx`: Unified diff syntax highlighter, AST safety checks, and sandbox verification test outcomes.
- `components/IncidentMemoryView.tsx`: Part B incident memory browser with chronological isolation metrics.
- `components/GraphExplorerView.tsx`: Live SVG node-link graph visualizer and interactive property inspector.
- `components/EvaluationBenchmarksView.tsx`: Publication-grade benchmark tables with exact denominators ($N=5$).

---

## 4. Local Startup & Commands

### Prerequisites
- Node.js $\ge 18$
- Python $\ge 3.11$ with `uv`
- Docker running FalkorDB on port 6379

### Production / Unified Server (Single Command)
FastAPI automatically serves both the compiled React frontend and the API:
```bash
# 1. Build the frontend
npm --prefix frontend run build

# 2. Launch the unified FastAPI server
uv run uvicorn tracefix.api.app:app --host 0.0.0.0 --port 8000
```
Open [http://localhost:8000](http://localhost:8000) in your browser.

### Development Mode (Hot-Reload)
Run the backend and frontend separately with Vite proxying:
```bash
# Terminal 1: Backend
uv run uvicorn tracefix.api.app:app --reload --port 8000

# Terminal 2: Frontend
npm --prefix frontend run dev
```
Open [http://localhost:5173](http://localhost:5173).

---

## 5. Verification & Testing

```bash
# Run backend pytest suite (335 tests)
uv run pytest

# Run Python linter & type checker
uv run ruff check .
uv run mypy src/

# Build and lint frontend
npm --prefix frontend run build
npm --prefix frontend run lint
```

---

## 6. Supported vs Unavailable Capabilities

| Capability | Status | Implementation Details |
|---|---|---|
| Frozen Benchmark Case Selection | **Supported** | 44 cases loaded from canonical dataset; 5 pilot cases preconfigured. |
| Graph-Guided Retrieval (Arm B) | **Supported** | Live Cypher queries against historical FalkorDB base-revision graphs (`requests_<short_sha>`). |
| Lexical BM25 Retrieval (Arm A) | **Supported** | AST function corpus built from historical commit revision snapshots. |
| Reciprocal Rank Fusion (Arm C) | **Supported** | True RRF ranking combining Lexical and Graph scores. |
| Context Budgeting | **Supported** | Strict token accounting with `CharDiv4TokenCounter`; explicit exclusion reasons. |
| AST Patch Safety Validation | **Supported** | Checks prohibited paths, traversal, and diff boundaries. |
| Sandbox Verification | **Supported** | Deterministic sandbox in mock mode; disposable Git worktree in live mode. |
| Part B Incident Memory Read/Write | **Supported** | Historical incident lookup with chronological isolation; write on `VERIFIED`. |
| Live Graph Visualization | **Supported** | SVG node-link graph querying live FalkorDB neighborhood. |
| Dense Embedding Retrieval (Arm D) | *Unavailable* | Dense model unselected pending licensing review (documented limitation). |
