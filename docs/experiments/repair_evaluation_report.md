# TraceFix Research Evaluation Report: Multi-Arm Retrieval and Memory Comparative Study

## 1. Experimental Overview & Configuration

- **Experiment Name:** Multi-Arm Retrieval and Memory Comparative Study
- **Case Set Fingerprint (SHA256):** `da1c89d31006ac65753d31fcb719b457ce5cb000e14e0735126018a90e350858`
- **Generated At:** 2026-10-17T18:25:25.522971+00:00
- **Primary Metric:** Hit@10
- **Context Budget Limit:** 4000 tokens
- **Pre-Cutoff Contamination Status:** Declared 100% pre-cutoff (frozen SWE-bench requests suite)

## 2. Comparative Performance Summary

| Arm | Strategy / Memory | Hit@5 | Hit@10 | Hit@20 | MRR | Patch Gen. Rate | Verified Success Rate |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Arm A (Lexical BM25)** | Conventional lexical BM25 retrieval without graph or incident memory | 33.3% | 33.3% | 33.3% | 0.333 | 100.0% | **100.0%** |
| **Arm B (Graph-Guided)** | Graph-guided neighborhood expansion without incident memory | 33.3% | 33.3% | 33.3% | 0.333 | 100.0% | **100.0%** |
| **Arm C (Graph + Verified Memory)** | Graph-guided retrieval augmented with chronological verified incident memory | 33.3% | 33.3% | 33.3% | 0.333 | 100.0% | **100.0%** |

## 3. Resource Consumption & Operational Efficiency

| Arm | Mean Context Tokens | Mean Retrieval Latency (ms) | Mean Repair Duration (s) | Incident Memories Accumulated |
|:---|:---:|:---:|:---:|:---:|
| **Arm A (Lexical BM25)** | 143 | 35.0 ms | N/A | 0 |
| **Arm B (Graph-Guided)** | 143 | 65.0 ms | N/A | 0 |
| **Arm C (Graph + Verified Memory)** | 327 | 65.0 ms | N/A | 3 |

## 4. Denominator & Case Audit

| Arm | Total Cases | Localizable Cases | Evaluated Cases | Excluded Cases | Failed Cases |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Arm A (Lexical BM25)** | 3 | 3 | 3 | 0 | 0 |
| **Arm B (Graph-Guided)** | 3 | 3 | 3 | 0 | 0 |
| **Arm C (Graph + Verified Memory)** | 3 | 3 | 3 | 0 | 0 |

## 5. Invariant & Validity Assurances

- **Zero Fabrication Policy:** All rates and numbers report explicit numerators and denominators.
- **Temporal Leakage Prevention:** Arm C enforces strict chronological replay; all future commits and same-case fix revisions are excluded prior to query execution.
- **Sandbox Isolation:** Patches executed inside isolated environments with sanitized credentials.
- **Eligibility Gating:** Only verified candidate patches with exit code 0 and passing test suites enter incident memory.
