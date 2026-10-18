"""Contract integrity tests for Workstream B proposed contracts (Checkpoint 0).

Validates that contracts/repair.json, contracts/verification.json, and
contracts/incident_memory.json adhere to naming, semver, and schema rules.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "contracts"
WSB_CONTRACT_FILES = (
    "repair.json",
    "verification.json",
    "incident_memory.json",
)
SEMVER = re.compile(r"^\d+\.\d+\.\d+")


def _load(name: str) -> dict:
    path = CONTRACTS_DIR / name
    assert path.is_file(), f"missing contract file: {path}"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


@pytest.mark.contract
@pytest.mark.parametrize("name", WSB_CONTRACT_FILES)
def test_wsb_contract_file_parses_with_required_fields(name: str) -> None:
    data = _load(name)
    assert data["contract"].startswith("tracefix.")
    assert SEMVER.match(data["version"]), data["version"]
    assert "draft" in data["status"]
    assert data["checkpoint"] == "0-D-B1"


@pytest.mark.contract
def test_repair_contract_declares_state_machine_and_safety_bounds() -> None:
    data = _load("repair.json")
    sm = data["state_machine"]
    assert "RECEIVED" in sm["states"]
    assert "VERIFIED" in sm["terminal_states"]
    assert "FAILED" in sm["terminal_states"]
    assert "REJECTED" in sm["terminal_states"]
    assert sm["invariants"], "state machine must declare invariants"

    policy = data["patch_validation_policy"]
    assert policy["path_rules"], "validation policy must declare path rules"
    assert policy["prohibited_files"], "validation policy must declare prohibited files"
    assert policy["bounds"]["max_changed_files"] > 0
    assert policy["bounds"]["max_changed_lines"] > 0


@pytest.mark.contract
def test_verification_contract_declares_status_taxonomy_and_tiers() -> None:
    data = _load("verification.json")
    statuses = set(data["verification_status"])
    assert "VERIFIED" in statuses
    assert "TEST_FAILED" in statuses
    assert "SETUP_FAILED" in statuses
    assert "TIMEOUT" in statuses
    assert "PATCH_REJECTED" in statuses
    assert "ENVIRONMENT_ERROR" in statuses

    req = data["verification_request"]
    assert "timeout_seconds" in req["limits"]
    assert "fail_to_pass" in req["test_suite"]
    assert "pass_to_pass" in req["test_suite"]
    assert data["safety_controls"], "verification contract must specify safety controls"


@pytest.mark.contract
def test_incident_memory_contract_declares_lifecycle_and_eligibility_rules() -> None:
    data = _load("incident_memory.json")
    states = set(data["lifecycle_states"])
    assert states == {"OBSERVED", "ATTEMPTED", "VERIFIED", "REJECTED"}

    rules = data["eligibility_rules"]
    assert len(rules) >= 4, "must define at least 4 eligibility rules"
    assert any("VERIFIED" in r for r in rules), "Rule 1 must mandate verification"
    assert any("chronological" in r.lower() or "created_at" in r for r in rules), (
        "Rule 4 must mandate chronological isolation"
    )

    rec = data["incident_record"]
    assert rec["explanation_verified"] == (
        "bool; strictly false by default unless verified by independent proof"
    )
