"""Unit tests for comparative research reports (B6.3)."""

from __future__ import annotations

from pathlib import Path

from tracefix.evaluation.experiment_runner import (
    ArmAggregate,
    MultiArmExperimentResult,
)
from tracefix.evaluation.reports import (
    generate_json_report,
    generate_latex_table,
    generate_markdown_report,
    save_reports,
)


def _make_dummy_result() -> MultiArmExperimentResult:
    arm_a = ArmAggregate(
        arm_id="arm_a",
        arm_name="Arm A (Lexical)",
        description="Lexical baseline",
        cases_total=10,
        cases_localizable=9,
        cases_evaluated=9,
        cases_excluded=1,
        cases_failed=0,
        hit_at_k_macro={"5": 0.444, "10": 0.667, "20": 0.778},
        mrr_macro=0.550,
        patch_generated_rate=0.889,
        patch_validated_rate=0.778,
        verified_repair_rate=0.444,
        mean_context_tokens=3200.0,
        mean_retrieval_latency_ms=45.2,
        mean_repair_duration_seconds=12.4,
        memories_accumulated=0,
    )
    arm_b = ArmAggregate(
        arm_id="arm_b",
        arm_name="Arm B (Graph)",
        description="Graph-guided retrieval",
        cases_total=10,
        cases_localizable=9,
        cases_evaluated=9,
        cases_excluded=1,
        cases_failed=0,
        hit_at_k_macro={"5": 0.667, "10": 0.889, "20": 1.000},
        mrr_macro=0.750,
        patch_generated_rate=1.0,
        patch_validated_rate=0.889,
        verified_repair_rate=0.667,
        mean_context_tokens=3800.0,
        mean_retrieval_latency_ms=62.8,
        mean_repair_duration_seconds=14.1,
        memories_accumulated=0,
    )
    arm_c = ArmAggregate(
        arm_id="arm_c",
        arm_name="Arm C (Graph + Memory)",
        description="Graph-guided + verified incident memory",
        cases_total=10,
        cases_localizable=9,
        cases_evaluated=9,
        cases_excluded=1,
        cases_failed=0,
        hit_at_k_macro={"5": 0.778, "10": 1.000, "20": 1.000},
        mrr_macro=0.880,
        patch_generated_rate=1.0,
        patch_validated_rate=1.0,
        verified_repair_rate=0.889,
        mean_context_tokens=4100.0,
        mean_retrieval_latency_ms=75.4,
        mean_repair_duration_seconds=11.2,
        memories_accumulated=8,
    )

    return MultiArmExperimentResult(
        experiment_name="Retrieval and Memory Ablation Study",
        case_set_fingerprint="abc1234567890def",
        created_at="2026-10-17T23:00:00Z",
        k_values=[5, 10, 20],
        primary_k=10,
        token_budget=4000,
        arms={"arm_a": arm_a, "arm_b": arm_b, "arm_c": arm_c},
    )


def test_generate_markdown_report() -> None:
    result = _make_dummy_result()
    md = generate_markdown_report(result)
    assert "# TraceFix Research Evaluation Report" in md
    assert "abc1234567890def" in md
    assert "Arm A (Lexical)" in md
    assert "Arm B (Graph)" in md
    assert "Arm C (Graph + Memory)" in md
    assert "66.7%" in md
    assert "88.9%" in md
    assert "Zero Fabrication Policy" in md


def test_generate_latex_table() -> None:
    result = _make_dummy_result()
    tex = generate_latex_table(result)
    assert r"\begin{table*}" in tex
    assert r"\toprule" in tex
    assert "Arm A (Lexical)" in tex
    assert r"\bottomrule" in tex
    assert r"\end{table*}" in tex


def test_generate_json_report() -> None:
    result = _make_dummy_result()
    json_str = generate_json_report(result)
    assert "Retrieval and Memory Ablation Study" in json_str
    assert "arm_a" in json_str
    assert "arm_c" in json_str


def test_save_reports(tmp_path: Path) -> None:
    result = _make_dummy_result()
    out_dir = tmp_path / "reports"
    paths = save_reports(result, out_dir, basename="test_eval")
    assert paths["markdown"].exists()
    assert paths["latex"].exists()
    assert paths["json"].exists()

    content = paths["markdown"].read_text(encoding="utf-8")
    assert "TraceFix Research Evaluation Report" in content
