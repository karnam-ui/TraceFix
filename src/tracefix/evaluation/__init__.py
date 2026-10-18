"""TraceFix Evaluation Package (Workstreams A & B).

Comprehensive research evaluation, metric accounting, single-arm retrieval testing,
chronological replay with leakage prevention, and multi-arm comparative experiment harnesses.
"""

from __future__ import annotations

from tracefix.evaluation.cases import CaseRecord, CaseSet, load_case_set
from tracefix.evaluation.experiment_runner import (
    ArmAggregate,
    ArmCaseResult,
    ExperimentArm,
    MultiArmExperimentResult,
    MultiArmExperimentRunner,
)
from tracefix.evaluation.replay import (
    ChronologicalReplayEngine,
    ReplayLeakageError,
    ReplaySessionSummary,
    ReplayStepResult,
)
from tracefix.evaluation.reports import (
    generate_json_report,
    generate_latex_table,
    generate_markdown_report,
    save_reports,
)
from tracefix.evaluation.runner import EvaluationReport, EvaluationRunner

__all__ = [
    "CaseRecord",
    "CaseSet",
    "load_case_set",
    "EvaluationRunner",
    "EvaluationReport",
    "ChronologicalReplayEngine",
    "ReplayLeakageError",
    "ReplaySessionSummary",
    "ReplayStepResult",
    "ExperimentArm",
    "ArmAggregate",
    "ArmCaseResult",
    "MultiArmExperimentRunner",
    "MultiArmExperimentResult",
    "generate_markdown_report",
    "generate_latex_table",
    "generate_json_report",
    "save_reports",
]
