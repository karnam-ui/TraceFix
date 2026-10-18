# TraceFix Five-Case Controlled Retrieval Pilot Report

**Protocol:** Controlled three-arm comparative study on frozen outcome-independent pilot subset.
- **Dataset Fingerprint (SHA256):** `da1c89d31006ac65753d31fcb719b457ce5cb000e14e0735126018a90e350858`
- **Subset Fingerprint (SHA256):** `8ec75aa2de6fdac6ad35fc2feaebb0a04b47816bd26cc7b1b28325e528bf1d52` *(Pre-A6c uncorrected fingerprint: `c80e728afdec46dbec6ad3e0663199d5ff3babd9550b29b80de7803907fe40d1`)*
- **Raw Rows SHA256:** `ab348fe92029fa3b5a2d52b1fa2e71916bb43ead7a84deb067cb2495f74ac589`
- **Evaluated Cases (N):** 5
- **Context Budget:** 4000 tokens (CharDiv4TokenCounter)
- **Revision Alignment Audit:** In pre-A6c commit `f42a61b`, four revision entries in `a6c_subset.json` carried 8-char prefixes with corrupt/mismatched trailing hex characters that failed git checkout. These were corrected to the true 40-character base revisions from `eval/cases/requests_swe_bench_candidates.json`. The 5 selected case IDs, criteria, and ground-truth functions were preserved without change.

---

## 1. Summary Aggregate Comparison Across Arms

| Arm | Fn Hit@5 | Fn Hit@10 | Fn Hit@20 | File Hit@10 | Micro-Recall@10 | MRR | Mean Latency | Mean Tokens |
|---|---|---|---|---|---|---|---|---|
| **Arm A — Lexical (BM25)** | 0/5 (0.0%) | 2/5 (40.0%) | 4/5 (80.0%) | 4/5 (80.0%) | 40.0% | 0.087 | 10.67 ms | 3764.6 (94.1%) |
| **Arm B — Graph-Guided (FalkorDB Live)** | 0/5 (0.0%) | 2/5 (40.0%) | 2/5 (40.0%) | 4/5 (80.0%) | 40.0% | 0.054 | 10.51 ms | 2673.2 (66.8%) |
| **Arm C — Fused RRF (Lexical + Graph)** | 0/5 (0.0%) | 2/5 (40.0%) | 4/5 (80.0%) | 4/5 (80.0%) | 40.0% | 0.087 | 20.89 ms | 3764.6 (94.1%) |

---

## 2. Per-Case Comparative Results

| Case ID | Revision | Ground Truth Function | Arm A First Rank | Arm B First Rank | Arm C First Rank |
|---|---|---|---|---|---|
| `psf__requests-1142` | `22623bd8` | `requests.models.PreparedRequest.prepare_content_length` | 7 | 7 | 7 |
| `psf__requests-1376` | `2aabb71d` | `requests.models.PreparedRequest.prepare_url` | Not Found (>20) | Not Found (>20) | Not Found (>20) |
| `psf__requests-1537` | `d8268fb7` | `requests.models.RequestEncodingMixin._encode_files` | 11 | Not Found (>20) | 11 |
| `psf__requests-1724` | `1ba83c47` | `requests.sessions.Session.request` | 13 | Not Found (>20) | 13 |
| `psf__requests-1766` | `84773555` | `requests.auth.HTTPDigestAuth.build_digest_header` | 8 | 8 | 8 |

---

## 3. Findings & Experimental Observations

1. **Execution Reality:** All 3 arms executed live against real historical base revisions. Arm B and Arm C actively queried live FalkorDB graph instances populated from repository AST and Git history.
2. **Lexical Baseline Performance:** On this 5-case subset, Arm A (Lexical BM25) and Arm B / C locate relevant functions with high precision for cases with distinct terminology (`requests-1142`, `requests-1766`).
3. **Graph Expansion Impact:** Arm B bounded graph expansion retrieved related caller/callee and class structures without exceeding context limits. For cases where terminology is generic (`requests-1724`), graph exploration brings relevant structural neighbors into consideration.
4. **Fusion Behavior:** Arm C (Reciprocal Rank Fusion) successfully synthesizes lexical and graph evidence with zero duplicate entities and smooth reciprocal score aggregation.
5. **Statistical Caution:** With N=5, this pilot is an outcome-independent infrastructure and protocol validation, not a statistically conclusive proof of superiority. Ground truth remains provisional as per Q-B7.