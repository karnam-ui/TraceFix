# TraceFix: Graph-Native Bug Resolution & Verified Repair Engine

TraceFix is an automated software repair and repository intelligence system designed to answer a central research question:

> **Does graph-guided retrieval combined with verified incident memory improve localization and verified repair success compared with conventional retrieval under comparable context budgets?**

The system is organized into two cooperating workstreams:
- **Workstream A — Graph Intelligence & Retrieval:** Repository AST ingestion, FalkorDB property graph, typed query layer, lexical baseline, graph-guided neighborhood expansion, dense retrieval adapter, RRF fusion, and token-budgeted context selection.
- **Workstream B — Repair Engine, Sandbox Verification & Evaluation:** Explicit repair state machine, provider-independent model adapters, unified diff parsing and safety validation, isolated sandbox verification (Tier 1 `git worktree` and Tier 2 Docker), verified incident memory repository, chronological replay engine with automated future leakage prevention, and a multi-arm research evaluation harness.

---

## Architecture & Repository Layout

```text
contracts/                     # Versioned JSON contract specifications
  graph_schema.json            # C1: FalkorDB node/edge definitions
  retrieval.json               # C2: Retrieval query/result and strategy interface
  context_manifest.json        # C3: Evidence item packaging & token accounting
  evaluation.json              # C4: Evaluation case schema and metric definitions
  repair.json                  # C5: Repair state machine and request/result schema
  verification.json            # C6: Sandbox lifecycle and verification result schema
  incident_memory.json         # C7: Incident record schema & eligibility rules

src/tracefix/
  graph/                       # Node/Edge models, schema, AST ingestion, graph query
  retrieval/                   # Lexical BM25, graph-guided, dense, fusion, context selector
  repair/                      # State machine, model adapters, diff parser, safety validator
  verification/                # Disposable git worktree sandbox, Docker sandbox, test runner
  memory/                      # Incident memory models, strict eligibility gatekeeper, repository
  evaluation/                  # Case loader, pure metrics, chronological replay, experiment runner, reports

tests/                         # 327 service-free unit, contract, and integration tests
eval/cases/                    # Frozen candidate evaluation case set (44 cases, read-only)
scripts/
  run_case.py                  # CLI to execute a single bug case end-to-end
  run_evaluation.py            # CLI to run multi-arm comparative research evaluations
  validate_cases.py            # AST ground-truth validation for evaluation pools
docs/
  workstreams/                 # Audit reports and implementation plans for Workstreams A & B
  experiments/                 # Generated Markdown, LaTeX, and JSON comparative evaluation reports
```

---

## Installation & Setup

TraceFix requires Python 3.12+ and is managed via `uv` or standard virtual environments:

```sh
# Clone and setup environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies in editable mode with development tools
pip install -e ".[dev]"

# Optional: install exact tiktoken tokenizer
pip install -e ".[tiktoken]"
```

---

## Quality Gates & Verification

Every pull request and checkpoint must pass all automated quality gates:

```sh
# Run entire test suite (327 tests)
uv run --extra dev pytest

# Check code formatting and style
uv run --extra dev ruff check src tests scripts

# Type check across all modules
uv run --extra dev mypy src scripts/run_case.py scripts/run_evaluation.py
```

Tests are **service-free** by default:
- Tier 1 sandbox operates using disposable `git worktree` directories in temporary storage.
- Model adapters support deterministic canned mock providers for zero-cost offline regression.
- Live FalkorDB or Docker container tests are marked with `@pytest.mark.integration` and execute only when environment services are running.

---

## Running Single-Case Repair

You can run an individual bug case end-to-end through the complete repair workflow:

```sh
# Offline mock mode (deterministic gold diff & mock sandbox)
python scripts/run_case.py --case-id psf__requests-1142 --mock

# Live repair with LLM and disposable worktree sandbox
export ANTHROPIC_API_KEY="your-api-key"
python scripts/run_case.py --case-id psf__requests-1142 --strategy memory
```

The repair pipeline executes the following explicit state sequence:
`RECEIVED → CONTEXT_READY → PATCH_GENERATED → PATCH_VALIDATED → VERIFICATION_RUNNING → VERIFIED / FAILED / REJECTED`

---

## Running Multi-Arm Research Evaluations

Run comparative experiments across defined experimental arms under identical context budgets and dataset fingerprints:

```sh
# Run comparative evaluation on anchor cases (Arm A vs Arm B vs Arm C)
python scripts/run_evaluation.py --mock --cases psf__requests-1142,psf__requests-1327,psf__requests-1339

# Run context budget ablation (e.g. 8k token budget)
python scripts/run_evaluation.py --mock --budget 8000 --basename budget_8k_evaluation_report
```

Output reports are saved automatically in `docs/experiments/`:
- `*.md`: Comprehensive Markdown report with comparative tables and denominator audits.
- `*.tex`: Academic publication-ready LaTeX `booktabs` table.
- `*.json`: Fully reproducible JSON serialization for programmatic analysis.

---

## Methodological Invariants & Research Integrity

1. **Zero Metric Fabrication:** All rates (Hit@k, Recall@k, Patch Generated Rate, Verified Success Rate) explicitly report numerators and denominators. Excluded cases are tracked with explicit reasons and never silently dropped.
2. **Strict Chronological Replay:** When incident memory is enabled, cases are processed in strict temporal order. Future commits, future memories, and target fix commits are blocked by automated leakage assertions before prompt construction.
3. **Execution Isolation:** Untrusted model-generated patches are applied only inside disposable `git worktree` sandboxes or ephemeral Docker containers with `--network none`. Production credentials and environment secrets are scrubbed before test execution.
4. **Strict Eligibility Gating:** Only patches that pass 100% of the verification test suite with exit code 0 are eligible for incident memory storage. Model-generated explanations are flagged as unverified and excluded from reuse.
