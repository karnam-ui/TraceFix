# A6c — Reproducible Graph Evaluation & Retrieval Pilot Report

**Status:** COMPLETE — Revision-specific graph ingestion, live FalkorDB persistence, 3-arm smoke test, and the controlled 5-case retrieval pilot have been fully executed, validated, and documented.

---

## 1. Environment & Services
- **FalkorDB Container:** `falkordb-a6c` active on `localhost:6379` (`falkordb/falkordb:latest`, Redis v8.10.2).
- **Python Driver:** FalkorDB 1.8.0 with `FalkorDBClient` in `src/tracefix/graph/client.py`.
- **Driver Compatibility Fix:** Resolved live-driver `_rows` row-mapping bug in `client.py` where `res.header` and `res.result_set` were previously unmapped in production execution.
- **Isolation:** Each historical revision is stored in an isolated FalkorDB named graph (`requests_<short_sha>`) with revision properties enforced on every node and relationship.

---

## 2. Frozen Outcome-Independent Subset
- **Dataset Fingerprint (SHA256):** `da1c89d31006ac65753d31fcb719b457ce5cb000e14e0735126018a90e350858`
- **Raw Rows SHA256:** `ab348fe92029fa3b5a2d52b1fa2e71916bb43ead7a84deb067cb2495f74ac589`
- **Selection Criteria:** Localizable, `len(gt_functions) == 1`, excluding `requests.packages.*` vendored code.
- **Selected Cases:**
  1. `psf__requests-1142` (`22623bd8c265b78b161542663ee980738441c307`) — GT: `requests.models.PreparedRequest.prepare_content_length`
  2. `psf__requests-1376` (`2aabb71dc8db434122c2e00c9d1313c6f368ce1c`) — GT: `requests.models.PreparedRequest.prepare_url`
  3. `psf__requests-1537` (`d8268fb7b44da7b8aa225eb1ca6fbdb4f9dc2457`) — GT: `requests.models.RequestEncodingMixin._encode_files`
  4. `psf__requests-1724` (`1ba83c47ce7b177efe90d5f51f7760680f72eda0`) — GT: `requests.sessions.Session.request`
  5. `psf__requests-1766` (`847735553aeda6e6633f2b32e14ba14ba86887a4`) — GT: `requests.auth.HTTPDigestAuth.build_digest_header`

---

## 3. Revision-Specific Ingestion & Graph Persistence
All 5 base revisions were checked out in `data/repos/requests`, ingested via AST and Git history analysis, and dual-persisted:
1. **Disk Artifacts:** `artifacts/graphs/requests_<short_sha>.json` containing full schema-validated node/edge payloads and SHA256 checksums.
2. **Live FalkorDB Graphs:** Populated with typed labels, properties, and indexed entity IDs.

| Case ID | Revision | Graph Name | Nodes | Edges | Artifact Checksum (SHA256) |
|---|---|---|---|---|---|
| `psf__requests-1142` | `22623bd8` | `requests_22623bd8` | 1,204 | 2,622 | `54aceb10d115...` |
| `psf__requests-1376` | `2aabb71d` | `requests_2aabb71d` | 1,293 | 5,972 | `b50f4168479b...` |
| `psf__requests-1537` | `d8268fb7` | `requests_d8268fb7` | 1,335 | 7,445 | `6ac08ddd172c...` |
| `psf__requests-1724` | `1ba83c47` | `requests_1ba83c47` | 1,378 | 8,688 | `61214313a732...` |
| `psf__requests-1766` | `84773555` | `requests_84773555` | 1,382 | 8,935 | `01ac31ddfd08...` |

Ingestion manifest saved to `artifacts/graphs/manifest.json`.

---

## 4. Live Smoke-Test Results (Arms A, B, C)
Verified on case `psf__requests-1142` at revision `22623bd8`:
- **Arm A (Lexical):** 10 items retrieved, elapsed 2.70 ms, top candidate `requests.adapters.HTTPAdapter.send`.
- **Arm B (Graph-Guided):** 10 items retrieved, elapsed 2.28 ms, queried FalkorDB live, correctly expanded neighbors.
- **Arm C (Fused RRF):** 10 items retrieved, elapsed 3.37 ms, combined Lexical + Graph rankings via Reciprocal Rank Fusion.

---

## 5. Controlled Five-Case Pilot Results
Executed via `scripts/run_retrieval_pilot.py` under an identical 4,000 token budget (`CharDiv4TokenCounter`) and candidate pool:

| Arm | Fn Hit@5 | Fn Hit@10 | Fn Hit@20 | File Hit@10 | Micro-Recall@10 | MRR | Mean Latency | Mean Tokens |
|---|---|---|---|---|---|---|---|---|
| **Arm A — Lexical (BM25)** | 0/5 (0.0%) | 2/5 (40.0%) | 4/5 (80.0%) | 4/5 (80.0%) | 40.0% | 0.087 | 10.67 ms | 3,764.6 (94.1%) |
| **Arm B — Graph-Guided (FalkorDB Live)** | 0/5 (0.0%) | 2/5 (40.0%) | 2/5 (40.0%) | 4/5 (80.0%) | 40.0% | 0.054 | 10.51 ms | 2,673.2 (66.8%) |
| **Arm C — Fused RRF (Lexical + Graph)** | 0/5 (0.0%) | 2/5 (40.0%) | 4/5 (80.0%) | 4/5 (80.0%) | 40.0% | 0.087 | 20.89 ms | 3,764.6 (94.1%) |

Full per-case rankings and raw data are recorded in:
- `docs/experiments/retrieval_pilot_report.json`
- `docs/experiments/retrieval_pilot_report.md`

---

## 6. Constraints & Research Integrity Respected
- **No Ground Truth Mutations:** The canonical ground truth in `eval/cases/requests_swe_bench_candidates.json` remained 100% untouched.
- **No Case Exclusions:** Denominators explicitly declare all 5 evaluated cases.
- **Honest Limitations:** Ground truth remains provisional (Q-B7), 100% pre-cutoff nature disclosed, sample size (N=5) explicitly noted as non-generalizable.
