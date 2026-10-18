"""Unit tests for repair and evaluation rate metrics (B6.2)."""

from __future__ import annotations

import pytest

from tracefix.evaluation.metrics import (
    patch_generation_rate,
    patch_validation_rate,
    rate,
    repair_success_rate,
)


def test_rate_computation() -> None:
    assert rate(5, 10) == 0.5
    assert rate(0, 10) == 0.0
    assert rate(10, 10) == 1.0


def test_rate_zero_denominator_is_none() -> None:
    # Zero denominator is undefined, never coerced to 0.0
    assert rate(0, 0) is None
    assert rate(5, 0) is None


def test_rate_negative_values_raise_value_error() -> None:
    with pytest.raises(ValueError, match="numerator must be >= 0"):
        rate(-1, 10)
    with pytest.raises(ValueError, match="denominator must be >= 0"):
        rate(5, -2)


def test_repair_rates_semantics() -> None:
    assert repair_success_rate(3, 10) == 0.3
    assert repair_success_rate(0, 0) is None

    assert patch_generation_rate(8, 10) == 0.8
    assert patch_generation_rate(0, 0) is None

    assert patch_validation_rate(6, 10) == 0.6
    assert patch_validation_rate(0, 0) is None
