"""HIPAA compliance unit tests."""

import json
import tempfile
from pathlib import Path

import pytest

from src.hipaa.audit_logger import AuditAction, AuditLogger
from src.hipaa.phi_redactor import contains_phi, detect_phi, redact_phi


# ── PHI Redaction ─────────────────────────────────────────────────────────────

def test_redact_ssn():
    text = "Patient SSN is 123-45-6789."
    redacted, matches = redact_phi(text)
    assert "123-45-6789" not in redacted
    assert "[SSN]" in redacted
    assert len(matches) == 1


def test_redact_email():
    text = "Contact john.doe@hospital.com for follow-up."
    redacted, matches = redact_phi(text)
    assert "john.doe@hospital.com" not in redacted
    assert "[EMAIL]" in redacted


def test_redact_phone():
    text = "Call 555-867-5309 for appointment."
    redacted, matches = redact_phi(text)
    assert "555-867-5309" not in redacted


def test_no_phi():
    text = "Blood pressure is 120/80 mmHg, within normal limits."
    redacted, matches = redact_phi(text)
    assert matches == []
    assert redacted == text


def test_contains_phi_true():
    assert contains_phi("Patient email: test@example.com") is True


def test_contains_phi_false():
    assert contains_phi("Hemoglobin A1c: 7.2%") is False


# ── Audit Logger ──────────────────────────────────────────────────────────────

def test_audit_log_creates_entry():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        log_path = f.name

    logger = AuditLogger(log_path)
    entry_id = logger.log(
        AuditAction.READ,
        user_id="dr_smith",
        resource_type="Patient",
        resource_id="patient-123",
        patient_id="patient-123",
    )

    with open(log_path) as f:
        lines = f.readlines()

    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["entry_id"] == entry_id
    assert entry["action"] == "READ"
    assert entry["user_id"] == "dr_smith"
    assert "entry_hash" in entry


def test_audit_chain_integrity():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        log_path = f.name

    logger = AuditLogger(log_path)
    for i in range(5):
        logger.log(
            AuditAction.READ,
            user_id=f"user_{i}",
            resource_type="Patient",
            resource_id=f"patient-{i}",
        )

    assert logger.verify_chain() is True


def test_audit_tamper_detection():
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w") as f:
        log_path = f.name

    logger = AuditLogger(log_path)
    logger.log(AuditAction.READ, user_id="user_1", resource_type="Patient", resource_id="p1")
    logger.log(AuditAction.WRITE if hasattr(AuditAction, "WRITE") else AuditAction.CREATE,
               user_id="user_2", resource_type="Patient", resource_id="p2")

    # Tamper with the file
    with open(log_path) as f:
        lines = f.readlines()
    lines[0] = lines[0].replace("user_1", "attacker")
    with open(log_path, "w") as f:
        f.writelines(lines)

    assert logger.verify_chain() is False
