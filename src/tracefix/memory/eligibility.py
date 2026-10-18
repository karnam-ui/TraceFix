"""Strict eligibility gatekeeper and chronological leakage guards (Phase 4).

Complies with contracts/incident_memory.json (C7).
Enforces Rules 1–4:
- Rule 1: Only records with lifecycle_status='VERIFIED' and verification_evidence.status='VERIFIED'
  are eligible for reuse.
- Rule 2: Unverified root-cause explanations must never be presented as verified facts.
- Rule 3: Negative attempts are retained as negative patterns, but never marked eligible.
- Rule 4: Memory records created_at >= query time are strictly excluded (chronological isolation).
"""

from __future__ import annotations

from datetime import datetime

from tracefix.memory.models import EligibilityStatus, IncidentRecord


class EligibilityEvaluator:
    """Enforces audit rules for incident memory reuse."""

    def evaluate(self, record: IncidentRecord) -> tuple[EligibilityStatus, str | None]:
        """Evaluate an IncidentRecord against Rules 1–3."""
        # Rule 1: Verification requirement
        if record.lifecycle_status != "VERIFIED":
            return (
                "INELIGIBLE",
                f"Rule 1 violation: lifecycle status '{record.lifecycle_status}' is not 'VERIFIED'",
            )

        v_status = record.verification_evidence.status
        if v_status != "VERIFIED":
            return (
                "INELIGIBLE",
                f"Rule 1 violation: verification evidence status '{v_status}' is not 'VERIFIED'",
            )

        exit_code = record.verification_evidence.exit_code
        if exit_code != 0:
            return (
                "INELIGIBLE",
                f"Rule 1 violation: verification execution exit code {exit_code} != 0",
            )

        # Rule 2: Explanation integrity
        if record.root_cause_explanation is not None and record.root_cause_explanation.verified:
            # Model generated explanations cannot claim verified without external formal proof
            return (
                "INELIGIBLE",
                "Rule 2 violation: explanation cannot claim verified=True without proof",
            )

        # Passed all eligibility criteria
        return ("ELIGIBLE", None)

    def is_chronologically_eligible(self, record: IncidentRecord, as_of_time: str) -> bool:
        """Enforce Rule 4: Chronological isolation.

        Returns True only if record was created strictly before as_of_time.
        Prevents future information leakage during historical replay.
        """
        try:
            record_dt = datetime.fromisoformat(record.created_at)
            as_of_dt = datetime.fromisoformat(as_of_time)
            return record_dt < as_of_dt
        except Exception:
            # If timestamps cannot be compared reliably, fail-safe to exclusion
            return False
