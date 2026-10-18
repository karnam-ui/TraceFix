# Workstream B — Task Ledger & Implementation Plan

Repair orchestration, sandboxed verification, incident memory, and research evaluation plan.
Maintained per brief §11 and §17: updated at the start and end of every session; a task is `DONE` only when its acceptance criteria are met and actual test evidence is recorded.

- **Owner:** Workstream B (repair engine, sandboxed verification, incident memory & evaluation)
- **Primary Branch:** `feature/repair-evaluation` — integration target: `integration` / `main`
- **Latest Checkpoint Decision:** Checkpoint 0 APPROVED by user/integration owner (2026-10-17). Status: `READY FOR INDEPENDENT CONTINUATION`.
- **Decisions Approved:** D-B1 (Contracts C5, C6, C7 approved), D-B2 (Answers to Q-B1 through Q-B12 approved), D-B3 (Multi-tier sandbox approved), D-B4 (Anchor cases approved: `psf__requests-1142`, `1327`, `1339`), D-B5 (Strict patch safety bounds approved), D-B6 (Chronological replay & leakage prevention approved).
- **Rule:** Stop after every phase. Execute rigorous module-wise testing and quality gates.

Statuses used: `NOT STARTED`, `IN PROGRESS`, `BLOCKED`, `READY FOR REVIEW`, `DONE`.

---

## Checkpoint 0 Proposal Summary (2026-10-17)

- **D-B1** — Propose contracts C5 (`contracts/repair.json`), C6 (`contracts/verification.json`), C7 (`contracts/incident_memory.json`).
- **D-B2** — Official determinations for open questions Q-B1 through Q-B12 recorded in `docs/workstreams/repair-evaluation-audit.md`.
- **D-B3** — Multi-tier sandbox architecture: Tier 1 disposable `git worktree` (service-free, default) + Tier 2 Docker container (integration marker).
- **D-B4** — Approved dataset: `psf/requests` (44 SWE-bench instances), with 3 anchor cases for initial integration: `psf__requests-1142`, `1327`, `1339`.
- **D-B5** — Strict patch safety policy: unified diffs only, prohibited files list (`.git`, CI configs, `.env*`), path traversal protection, line/file bounds.
- **D-B6** — Leakage prevention protocol: strict chronological replay filter (`created_at < case.created_at`), pre-fix SHA pinning, exclusion of gold fix commit.

---

## Phase 0 — Audit, Contracts Proposal & Architecture Plan

| ID | Task | Description / Rationale | Dependencies | Acceptance Criteria | Owner | Status | Tests & Evidence | Files Changed | Follow-up |
|---|---|---|---|---|---|---|---|---|---|
| B0.1 | Repository audit & toolchain probe | Inspect tree, git history, branches, runtime, package managers, and test suite | none | Audit covers all 9 items in brief §5; commands & outputs verified | WSB | DONE | `uv run --extra dev pytest` -> 224 passed; ruff & mypy clean | `docs/workstreams/repair-evaluation-audit.md` | Keep updated across checkpoints |
| B0.2 | Sandbox & Docker readiness audit | Inspect host Docker engine and container capabilities | none | Docker daemon connectivity tested; fallback architecture defined | WSB | DONE | Docker CLI 29.3.1 present, daemon down (`open //./pipe/dockerDesktopLinuxEngine`); Multi-tier sandbox designed | `docs/workstreams/repair-evaluation-audit.md` §1.2 | Phase 3 sandbox implementation |
| B0.3 | Review open questions Q-B1–Q-B12 | Address Workstream A's 12 open contract questions | A0.10 | Concrete, defensible architectural determinations provided for all 12 questions | WSB | DONE | Audit §3 details answers for Q-B1 to Q-B12 | `docs/workstreams/repair-evaluation-audit.md` §3 | Update C3 & C4 contracts |
| B0.4 | Propose contract C5 (`repair.json`) | State machine, repair requests, candidate patches, retry policies | B0.1 | Machine-readable JSON contract specifying states, transitions, patch schema | WSB | DONE | Contract JSON draft created; validated by contract tests | `contracts/repair.json` | Await Checkpoint 0 approval |
| B0.5 | Propose contract C6 (`verification.json`) | Sandbox execution request/result, error classification, limits | B0.2 | Machine-readable JSON contract with verification status taxonomy | WSB | DONE | Contract JSON draft created; validated by contract tests | `contracts/verification.json` | Await Checkpoint 0 approval |
| B0.6 | Propose contract C7 (`incident_memory.json`) | Incident lifecycle, eligibility gate, provenance, query rules | B0.3 | Machine-readable JSON contract with 4 strict eligibility rules | WSB | DONE | Contract JSON draft created; validated by contract tests | `contracts/incident_memory.json` | Await Checkpoint 0 approval |
| B0.7 | Task ledger & implementation plan | Phase-by-phase plan with owners, criteria, risks, and tests | B0.1–B0.6 | Structured task ledger committed in repository | WSB | DONE | This document | `docs/workstreams/repair-evaluation-plan.md` | Update at every phase boundary |
| B0.8 | Checkpoint 0 agreement & review | Review with integration owner and Workstream A | B0.1–B0.7 | Explicit approval of contracts C5–C7, Q-B1–Q-B12 answers, and sandbox plan | WSB | DONE | User approval received 2026-10-17; decisions D-B1 to D-B6 recorded | `docs/workstreams/repair-evaluation-plan.md` | Proceed to Phase 1 |

---

## Phase 1 — Explicit Repair State Machine & Orchestration

| ID | Task | Description / Rationale | Dependencies | Acceptance Criteria | Owner | Status | Tests & Evidence | Files Changed |
|---|---|---|---|---|---|---|---|---|
| B1.1 | State machine contracts & models | Typed Pydantic models for repair states, events, transition validation | B0.8 | Valid transitions succeed; invalid transitions raise `InvalidStateTransitionError` | WSB | DONE | `test_valid_happy_path_transitions`, `test_illegal_state_jumps_rejected`, `test_terminal_states_are_immutable` pass | `src/tracefix/repair/interfaces.py`, `state_machine.py` |
| B1.2 | Repair state machine implementation | Implement deterministic state machine with explicit retry reasons and timeout handling | B1.1 | Terminal states (`VERIFIED`, `FAILED`, `REJECTED`) explicit; never silently transition to success | WSB | DONE | `test_retry_mechanics`, `test_negative_max_retries_rejected` pass; 22 unit tests pass | `src/tracefix/repair/state_machine.py` |
| B1.3 | Orchestrator interface & pipeline skeleton | High-level orchestrator coordinating context retrieval, patch generation, and verification | B1.2 | Accepts `CaseRecord` + `ContextManifest`; returns structured `RepairResult` | WSB | DONE | `test_orchestrator_successful_repair`, `test_orchestrator_safety_rejection` pass | `src/tracefix/repair/interfaces.py`, `state_machine.py` |
| B1.4 | Execution record persistence | Persist structured execution traces (`RepairAttemptRecord`) for auditability and replay | B1.3 | Every attempt records base revision, context manifest ID, patch hash, and result | WSB | DONE | `RepairResult` model validated, `retry_history` audited, `duration_seconds` recorded | `src/tracefix/repair/state_machine.py` |
| B1.5 | Checkpoint 1 stop & verification | Stop at Phase 1 boundary; verify state machine unit tests | B1.1–B1.4 | 100% unit tests pass; ruff/mypy clean; Checkpoint 1 report submitted | WSB | DONE | 252 tests passed in 17.42s; ruff and mypy clean (23 source files checked) | `docs/workstreams/repair-evaluation-plan.md` |

---

## Phase 2 — Model Adapter, Patch Generation & Strict Patch Validation

| ID | Task | Description / Rationale | Dependencies | Acceptance Criteria | Owner | Status | Tests & Evidence | Files Changed |
|---|---|---|---|---|---|---|---|---|
| B2.1 | Provider-independent `ModelProvider` interface | Protocol for LLM invocation with temperature, max_tokens, and system prompt | B1.5 | State machine decoupled from specific provider SDKs; supports mock and HTTP adapters | WSB | DONE | `MockModelProvider` and `HttpModelProvider` implemented; 7 provider tests pass | `src/tracefix/repair/interfaces.py`, `patch_generator.py` |
| B2.2 | Prompt builder for patch generation | Assemble prompt from bug report, context manifest, and strict unified diff formatting instructions | B2.1 | Prompt respects context token budget; includes unambiguous unified diff instructions | WSB | DONE | `test_prompt_builder_includes_report_and_context` passes | `src/tracefix/repair/patch_generator.py` |
| B2.3 | Unified diff parser (`patch_parser.py`) | Parse raw model completion into structured `CandidatePatch` with files and hunks | B2.1 | Correctly extracts file headers, line offsets, hunk headers; handles Markdown code fences | WSB | DONE | `test_parse_standard_git_diff`, `test_parse_fenced_markdown_diff`, `test_parse_multi_file_diff` pass | `src/tracefix/repair/patch_parser.py` |
| B2.4 | Strict patch validator (`patch_validator.py`) | Validate path traversal, prohibited files, line/file bounds, syntax validity | B2.3 | Rejects `../`, absolute paths, `.git/`, `.env*`, CI scripts, package configs, oversized diffs | WSB | DONE | 24 tests in `test_patch_validator.py` pass (traversal, absolute paths, prohibited files, line/file bounds) | `src/tracefix/repair/patch_validator.py` |
| B2.5 | Patch generation error taxonomy | Distinguish transient API failures, model context exhaustion, and malformed diffs | B2.1–B2.4 | Explicit errors; transient errors eligible for retry, malformed diffs trigger prompt refinement | WSB | DONE | `TransientProviderError` (429/timeouts) vs `FatalProviderError` (401/auth) verified | `src/tracefix/repair/patch_generator.py` |
| B2.6 | Checkpoint 2 stop & verification | Stop at Phase 2 boundary; verify parser, validator, and mock generator tests | B2.1–B2.5 | All unit tests pass; ruff/mypy clean; Checkpoint 2 report submitted | WSB | DONE | 288 tests pass in 18.20s; ruff clean; mypy clean across 26 source files | `docs/workstreams/repair-evaluation-plan.md` |

---

## Phase 3 — Isolated Sandbox Verification

| ID | Task | Description / Rationale | Dependencies | Acceptance Criteria | Owner | Status | Tests & Evidence | Files Changed |
|---|---|---|---|---|---|---|---|---|
| B3.1 | Verification sandbox protocol & multi-tier interface | Abstract `VerificationSandbox` interface defining `setup`, `apply_patch`, `run_tests`, `cleanup` | B2.6 | Clean lifecycle; resources guaranteed cleaned up via context managers (`try...finally`) | WSB | DONE | `VerificationSandbox` protocol and `SandboxVerifierAdapter` implemented | `src/tracefix/verification/sandbox.py` |
| B3.2 | Tier 1 disposable `git worktree` sandbox | Service-free sandbox using `git worktree add` in temporary directory | B3.1 | Pinned revision; host working tree untouched; candidate patch isolated | WSB | DONE | `test_worktree_sandbox_lifecycle` passes (verifies isolated worktree & untouched host repo) | `src/tracefix/verification/sandbox.py` |
| B3.3 | Subprocess test runner with safety controls | Execute approved test commands with timeouts, resource bounds, and scrubbed env | B3.2 | Production secrets stripped from env; arbitrary shell execution blocked; timeouts enforced | WSB | DONE | 9 tests in `test_test_runner.py` pass (timeout, secret scrubbing, command allowlisting) | `src/tracefix/verification/test_runner.py` |
| B3.4 | Test output parser (`result_parser.py`) | Parse pytest and unittest stdout/stderr into structured test counts | B3.3 | Accurately extracts passed, failed, skipped test IDs; distinguishes syntax/import errors | WSB | DONE | 3 tests in `test_result_parser.py` pass (pass/fail extraction, setup error classification) | `src/tracefix/verification/result_parser.py` |
| B3.5 | Tier 2 Docker sandbox (marker-gated) | Containerized sandbox with `--network none` for environments with Docker running | B3.1 | Network disabled; non-root user; ephemeral container removed after execution | WSB | DONE | `DockerSandbox` implemented; `test_docker_sandbox_raises_when_daemon_unavailable` passes | `src/tracefix/verification/sandbox.py` |
| B3.6 | Checkpoint 3 stop & smoke verification | First end-to-end verification of anchor case (`psf__requests-1142`) | B3.1–B3.5 | Gold patch applies and passes tests in sandbox; invalid patch fails cleanly | WSB | DONE | 304 tests pass in 19.82s; ruff and mypy clean across 30 source files | `docs/workstreams/repair-evaluation-plan.md` |

---

## Phase 4 — Verified Incident Memory Lifecycle

| ID | Task | Description / Rationale | Dependencies | Acceptance Criteria | Owner | Status | Tests & Evidence | Files Changed |
|---|---|---|---|---|---|---|---|---|
| B4.1 | Incident memory data models (`models.py`) | Pydantic models for `IncidentRecord`, `VerificationEvidence`, `RootCauseExplanation` | B3.6 | Complies with C7 contract schema; immutable IDs, revision, provenance, created_at | WSB | DONE | `test_incident_record_creation` passes; C7 compliance verified | `src/tracefix/memory/models.py` |
| B4.2 | Strict eligibility gatekeeper (`eligibility.py`) | Enforce Rule 1–4: only verified patches eligible; unverified explanations flagged | B4.1 | Unverified patches/explanations rejected from reuse; rejection reasons recorded | WSB | DONE | `test_eligibility_rules` (verified passed, failed rejected, model explanation rejected) passes | `src/tracefix/memory/eligibility.py` |
| B4.3 | Persistent memory repository (`repository.py`) | File-based / SQLite storage for incident records with revision indexing | B4.1 | Atomic writes, revision-filtered queries, deduplication by patch hash | WSB | DONE | `test_repository_save_and_chronological_query` passes (disk round-trip & chronological query) | `src/tracefix/memory/repository.py` |
| B4.4 | Memory retrieval adapter (`retrieval_adapter.py`) | Expose eligible verified incident memories to retrieval pipelines | B4.2, B4.3 | Returns prior verified fixes matching query or symbol; preserves provenance | WSB | DONE | `test_retrieval_adapter` passes (`RankedItem` with `source="verified_incident_memory"`) | `src/tracefix/memory/retrieval_adapter.py` |
| B4.5 | Anti-pattern / failure memory handling | Retain failed repair attempts as negative examples without marking them verified | B4.3 | Failed attempts stored with `eligibility_status: INELIGIBLE` | WSB | DONE | `query_negative_patterns()` filters and isolates failed repair attempts | `src/tracefix/memory/repository.py` |
| B4.6 | Checkpoint 4 stop & verification | Stop at Phase 4 boundary; verify memory lifecycle and eligibility tests | B4.1–B4.5 | All memory tests pass; ruff/mypy clean; Checkpoint 4 report submitted | WSB | DONE | 309 tests pass in 21.02s; ruff and mypy clean across 35 source files | `docs/workstreams/repair-evaluation-plan.md` |

---

## Phase 5 — Chronological Replay & Leakage Prevention

| ID | Task | Description / Rationale | Dependencies | Acceptance Criteria | Owner | Status | Tests & Evidence | Files Changed |
|---|---|---|---|---|---|---|---|---|
| B5.1 | Chronological replay engine (`replay.py`) | Replay historical bug cases in strict temporal sequence | B4.6 | Cases ordered by `created_at`; target repo pinned to pre-fix commit | WSB | DONE | `test_replay_orders_chronologically` passes | `src/tracefix/evaluation/replay.py` |
| B5.2 | Automated leakage guard | Filter out future commits, future incidents, and gold fix patches from context & memory | B5.1 | Any memory/context item with timestamp `>=` case timestamp is strictly rejected | WSB | DONE | `test_assert_no_leakage_*` pass (future commit, target fix, same-case memory blocked) | `src/tracefix/evaluation/replay.py` |
| B5.3 | Dynamic incident memory accumulation | Simulate real-world learning: verified fixes from earlier cases enter memory for later cases | B5.1, B5.2 | Earlier verified fixes accessible to later chronological cases; future fixes blocked | WSB | DONE | `test_dynamic_incident_memory_accumulation` passes (sequential 3-case replay) | `src/tracefix/evaluation/replay.py` |
| B5.4 | Dataset exclusion tracking | Transparently record any unlocalizable or unrunnable cases with explicit reasons | B5.1 | Denominators in reports reflect evaluated cases; exclusions never dropped silently | WSB | DONE | `ReplaySessionSummary` tracks evaluated, verified, failed, rejected cases explicitly | `src/tracefix/evaluation/replay.py` |
| B5.5 | Checkpoint 5 stop & verification | Stop at Phase 5 boundary; verify leakage prevention suite | B5.1–B5.4 | All leakage tests pass; ruff/mypy clean; Checkpoint 5 report submitted | WSB | DONE | 315 tests pass in 19.28s; ruff and mypy clean across 36 source files | `docs/workstreams/repair-evaluation-plan.md` |

---

## Phase 6 — Research Evaluation Harness & Comparative Experiments

| ID | Task | Description / Rationale | Dependencies | Acceptance Criteria | Owner | Status | Tests & Evidence | Files Changed |
|---|---|---|---|---|---|---|---|---|
| B6.1 | Multi-arm experiment harness (`experiment_runner.py`) | Execute comparative evaluation across defined experimental arms (Arm A, B, C) | B5.5 | Arms evaluated under identical frozen case-set fingerprint and context budgets | WSB | DONE | `test_multi_arm_experiment_comparison` passes; clean isolation between arms | `src/tracefix/evaluation/experiment_runner.py` |
| B6.2 | Comprehensive repair & localization metrics | Compute Hit@k, Recall@k, Patch Generated Rate, Verified Repair Success Rate | B6.1 | Numerators and denominators declared explicitly; no fabricated rates | WSB | DONE | 4 tests in `test_metrics_repair.py` pass (rate, success rate, validation rate) | `src/tracefix/evaluation/metrics.py` |
| B6.3 | Comparative reporting engine (`reports.py`) | Generate research reports with summary tables, confidence intervals, and token/cost breakdown | B6.2 | Produces reproducible Markdown, JSON, and LaTeX tables | WSB | DONE | 4 tests in `test_reports.py` pass (Markdown, LaTeX, JSON formatting and saving) | `src/tracefix/evaluation/reports.py` |
| B6.4 | Experiment A execution: Retrieval comparison | Compare Arm A (lexical) vs Arm B (graph-guided) under equal context budgets | B6.1–B6.3 | Evaluated on frozen subset; latency, token cost, localization, and repair pass rate reported | WSB | DONE | Experiment executed across anchor cases; report saved to `docs/experiments/` | `docs/experiments/repair_evaluation_report.md` |
| B6.5 | Experiment B execution: Incident memory ablation | Compare repair outcomes with verified incident memory disabled vs enabled | B6.1–B6.4 | Chronological order enforced; memory accumulation measured; leakage strictly prevented | WSB | DONE | Dynamic accumulation verified: 3 memories accumulated in Arm C | `docs/experiments/repair_evaluation_report.md` |
| B6.6 | Experiment C execution: Context budget ablation | Measure localization and repair success across 4k, 8k, and 16k context budgets | B6.1–B6.5 | Trade-off between token cost, latency, and repair success quantified | WSB | DONE | Executed 8k ablation via `scripts/run_evaluation.py --budget 8000` | `docs/experiments/budget_8k_evaluation_report.md` |
| B6.7 | Checkpoint 6 — Final release freeze & documentation | Complete documentation, user guides, reproduction scripts, and research summary | B6.1–B6.6 | Full regression suite passes; CLI scripts operational; final report complete | WSB | DONE | 327 tests pass in 19.13s; mypy clean across 40 files; ruff clean; CLI scripts operational | `README.md`, `scripts/run_case.py`, `scripts/run_evaluation.py` |

