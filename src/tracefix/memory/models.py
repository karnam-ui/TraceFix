"""Incident memory models (Phase 4).

Complies with contracts/incident_memory.json (C7).
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

LifecycleStatus = Literal["OBSERVED", "ATTEMPTED", "VERIFIED", "REJECTED"]
EligibilityStatus = Literal["ELIGIBLE", "INELIGIBLE"]


class VerificationEvidence(BaseModel):
    """Audited evidence of sandbox test verification."""

    status: str
    test_suite: str = "pytest"
    exit_code: int = 0
    duration_seconds: float = 0.0
    passed_tests: list[str] = Field(default_factory=list)
    failed_tests: list[str] = Field(default_factory=list)
    executed_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ModelMetadata(BaseModel):
    """Metadata regarding the generative model used for repair."""

    provider: str = "mock"
    model: str = "mock-model"
    temperature: float = 0.0


class RootCauseExplanation(BaseModel):
    """Model-generated explanation of the defect and fix."""

    text: str
    confidence: float = 0.0
    verified: bool = False  # Strictly false unless formally proven


class IncidentRecord(BaseModel):
    """Auditable, immutable record of an observed bug and repair outcome."""

    incident_id: str
    case_id: str
    repo: str = ""
    revision: str
    bug_report: str
    retrieved_evidence_ids: list[str] = Field(default_factory=list)
    patch_diff: str
    patch_hash: str
    verification_evidence: VerificationEvidence
    model_metadata: ModelMetadata = Field(default_factory=ModelMetadata)
    root_cause_explanation: RootCauseExplanation | None = None
    lifecycle_status: LifecycleStatus
    eligibility_status: EligibilityStatus = "INELIGIBLE"
    rejection_reason: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    @classmethod
    def create(
        cls,
        case_id: str,
        revision: str,
        bug_report: str,
        patch_diff: str,
        verification_evidence: VerificationEvidence,
        repo: str = "",
        retrieved_evidence_ids: list[str] | None = None,
        model_metadata: ModelMetadata | None = None,
        root_cause_explanation: RootCauseExplanation | None = None,
        lifecycle_status: LifecycleStatus | None = None,
        created_at: str | None = None,
    ) -> IncidentRecord:
        """Factory creating a canonical incident record with deterministic hash id."""
        diff_bytes = patch_diff.encode("utf-8")
        patch_hash = hashlib.sha256(diff_bytes).hexdigest()
        digest = hashlib.sha256(f"{case_id}#{revision}#{patch_hash}".encode()).hexdigest()
        inc_id = f"inc_{digest[:16]}"

        if lifecycle_status is None:
            if verification_evidence.status == "VERIFIED" and verification_evidence.exit_code == 0:
                lifecycle_status = "VERIFIED"
            else:
                lifecycle_status = "REJECTED"

        return cls(
            incident_id=inc_id,
            case_id=case_id,
            repo=repo,
            revision=revision,
            bug_report=bug_report,
            retrieved_evidence_ids=retrieved_evidence_ids or [],
            patch_diff=patch_diff,
            patch_hash=patch_hash,
            verification_evidence=verification_evidence,
            model_metadata=model_metadata or ModelMetadata(),
            root_cause_explanation=root_cause_explanation,
            lifecycle_status=lifecycle_status,
            eligibility_status="INELIGIBLE",
            created_at=created_at or datetime.now(UTC).isoformat(),
        )

    @model_validator(mode="after")
    def _validate_explanation_and_rejection(self) -> IncidentRecord:
        if self.eligibility_status == "INELIGIBLE" and not self.rejection_reason:
            if self.lifecycle_status != "VERIFIED":
                self.rejection_reason = (
                    f"Lifecycle status '{self.lifecycle_status}' is not eligible"
                )
        return self
