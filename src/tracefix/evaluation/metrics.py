"""Pure evaluation metrics (A6a).

Every function is deterministic and side-effect free, takes already-computed
ranks/counts, and keeps denominator policy in the caller. Undefined rates are
returned as ``None`` and never silently coerced to ``0.0``: an empty
denominator is *undefined*, not a successful zero.

Provisional defaults
--------------------
``DEFAULT_K_VALUES = (5, 10, 20)`` and ``DEFAULT_PRIMARY_K = 10`` are
**provisional** placeholders echoing the audit's proposal. They are configurable
and are **not** approved C4 choices (Q-B8); callers must not present them as
final.

Averages
--------
- macro: mean of per-case values, over the cases where the metric is *defined*
  (undefined cases are skipped and counted, never treated as zero).
- micro: pooled aggregation over a shared denominator (``micro_recall``).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

# Provisional, configurable, NOT approved (Q-B8).
DEFAULT_K_VALUES: tuple[int, ...] = (5, 10, 20)
DEFAULT_PRIMARY_K: int = 10


@dataclass(frozen=True)
class MetricsConfig:
    """Metric configuration. Defaults are provisional placeholders (Q-B8/Q-B11)."""

    k_values: tuple[int, ...] = DEFAULT_K_VALUES
    primary_k: int = DEFAULT_PRIMARY_K
    multi_function_policy: str = "any-hit-provisional"  # Q-B11 undecided

    def __post_init__(self) -> None:
        if not self.k_values:
            raise ValueError("k_values must not be empty")
        if any(k <= 0 for k in self.k_values):
            raise ValueError("k_values must all be > 0")
        if self.primary_k not in self.k_values:
            raise ValueError("primary_k must be one of k_values")

    def to_dict(self) -> dict[str, Any]:
        return {
            "k_values": list(self.k_values),
            "primary_k": self.primary_k,
            "multi_function_policy": self.multi_function_policy,
        }


def hit_at_k(ranks: list[int], k: int) -> bool:
    """``True`` if any relevance rank is ``<= k``."""
    if k <= 0:
        raise ValueError("k must be > 0")
    return any(rank <= k for rank in ranks)


def recall_at_k(ranks: list[int], k: int, n_relevant: int) -> float | None:
    """Fraction of relevant items within top ``k``; ``None`` when undefined."""
    if k <= 0:
        raise ValueError("k must be > 0")
    if n_relevant < 0:
        raise ValueError("n_relevant must be >= 0")
    if n_relevant == 0:
        return None
    found = sum(1 for rank in ranks if rank <= k)
    return found / n_relevant


def first_relevant_rank(ranks: list[int]) -> int | None:
    """Smallest rank, or ``None`` when no relevant item was found."""
    return min(ranks) if ranks else None


def reciprocal_rank(ranks: list[int]) -> float:
    """``1 / rank-of-first-relevant``; ``0.0`` when nothing was found.

    ``0.0`` here is a genuine zero (rank is defined as "not found"), not an
    undefined denominator.
    """
    rank = first_relevant_rank(ranks)
    return 0.0 if rank is None else 1.0 / rank


def mean(values: Sequence[float]) -> float | None:
    """Arithmetic mean, or ``None`` for an empty input (undefined)."""
    if not values:
        return None
    return sum(values) / len(values)


def macro_average(values: Sequence[float | None]) -> float | None:
    """Mean over defined (non-``None``) values; ``None`` when none are defined."""
    return mean([v for v in values if v is not None])


def micro_recall(
    per_case_ranks: list[list[int]], k: int, per_case_relevant: list[int]
) -> float | None:
    """Micro-averaged Recall@k: total found / total relevant (``None`` if 0)."""
    if len(per_case_ranks) != len(per_case_relevant):
        raise ValueError("per_case_ranks and per_case_relevant must align")
    total_relevant = sum(per_case_relevant)
    if total_relevant == 0:
        return None
    found = 0
    for ranks, n_relevant in zip(per_case_ranks, per_case_relevant, strict=True):
        if n_relevant == 0:
            continue
        found += sum(1 for rank in ranks if rank <= k)
    return found / total_relevant


def count_undefined(values: Sequence[float | None]) -> int:
    """How many entries were undefined (``None``) — the reported denominator gap."""
    return sum(1 for v in values if v is None)


def sum_tokens(token_counts: list[int]) -> int:
    """Total tokens across items (``0`` for empty input, which is well-defined)."""
    return sum(token_counts)


def count_duplicates(evidence_ids: list[str]) -> int:
    """Number of repeated ids beyond the first occurrence."""
    return len(evidence_ids) - len(set(evidence_ids))


def percentile(values: list[float], q: float) -> float | None:
    """Nearest-rank percentile (``q`` in ``[0, 100]``); ``None`` if empty."""
    if not 0.0 <= q <= 100.0:
        raise ValueError("q must be within [0, 100]")
    if not values:
        return None
    ordered = sorted(values)
    index = math.ceil(q / 100.0 * len(ordered)) - 1
    index = max(0, min(index, len(ordered) - 1))
    return float(ordered[index])


@dataclass(frozen=True)
class LatencyStats:
    """Aggregate latency in milliseconds; fields are ``None`` for empty input."""

    count: int
    total_ms: float
    mean_ms: float | None
    p50_ms: float | None
    p95_ms: float | None
    max_ms: float | None


def latency_stats(latencies_ms: list[float]) -> LatencyStats:
    """Aggregate latency; the empty input yields all-``None`` derivations."""
    if not latencies_ms:
        return LatencyStats(
            count=0, total_ms=0.0, mean_ms=None, p50_ms=None, p95_ms=None, max_ms=None
        )
    return LatencyStats(
        count=len(latencies_ms),
        total_ms=float(sum(latencies_ms)),
        mean_ms=sum(latencies_ms) / len(latencies_ms),
        p50_ms=percentile(latencies_ms, 50.0),
        p95_ms=percentile(latencies_ms, 95.0),
        max_ms=float(max(latencies_ms)),
    )


def to_jsonable(value: Any) -> Any:
    """Best-effort conversion of metric containers to JSON-serializable data."""
    if isinstance(value, LatencyStats):
        return {
            "count": value.count,
            "total_ms": value.total_ms,
            "mean_ms": value.mean_ms,
            "p50_ms": value.p50_ms,
            "p95_ms": value.p95_ms,
            "max_ms": value.max_ms,
        }
    if isinstance(value, MetricsConfig):
        return {
            "k_values": list(value.k_values),
            "primary_k": value.primary_k,
            "multi_function_policy": value.multi_function_policy,
        }
    return value


def rate(numerator: int, denominator: int) -> float | None:
    """Bounded rate computation; None when denominator is 0 (undefined, not zero)."""
    if numerator < 0:
        raise ValueError("numerator must be >= 0")
    if denominator < 0:
        raise ValueError("denominator must be >= 0")
    if denominator == 0:
        return None
    return numerator / denominator


def repair_success_rate(verified_count: int, evaluated_count: int) -> float | None:
    """Fraction of evaluated cases that achieved verified repair status."""
    return rate(verified_count, evaluated_count)


def patch_generation_rate(generated_count: int, evaluated_count: int) -> float | None:
    """Fraction of evaluated cases where a candidate patch was generated."""
    return rate(generated_count, evaluated_count)


def patch_validation_rate(validated_count: int, evaluated_count: int) -> float | None:
    """Fraction of evaluated cases where a candidate patch passed validation."""
    return rate(validated_count, evaluated_count)
