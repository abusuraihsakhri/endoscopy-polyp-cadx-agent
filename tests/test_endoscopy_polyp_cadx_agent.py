"""
Automated Pytest Test Suite for Endoscopy Polyp Cadx Agent.
Domain: Clinical & Biomedical AI
Standard: CAP / CLSI / ISO Standards
"""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from agents.base import PHIGuard, AuditLogger, SecurityException, AuditTrail
from agents.models import SystemTaskPayload, UrgencyLevel, SystemIntegrityStatus
from agents.workers import InvariantQCWorker, SafetyEscalationWorker, ProtocolConformanceWorker
from agents.supervisor import SystemSupervisor
from cli import main


def test_phi_guard_enforcement():
    with pytest.raises(SecurityException):
        PHIGuard.assert_no_phi("Patient MRN-994827 blood culture positive for Staphylococcus")

    # Clean text passes
    PHIGuard.assert_no_phi("Analytical assay specimen KEY-001 optimal")


def test_phi_guard_redaction():
    redacted = PHIGuard.redact_phi("Contact patient at 555-123-4567 or MRN-12345678")
    assert "555-123-4567" not in redacted
    assert "MRN-12345678" not in redacted
    assert "REDACTED_IDENTIFIER" in redacted


def test_phi_guard_blocks_various_patterns():
    """Test that all PHI patterns are blocked."""
    phi_samples = [
        "Patient SSN 123-45-6789",
        "Call 555-123-4567",
        "Email: patient@example.com",
        "DOB: 01/15/1985",
        "Patient John Doe admitted",
    ]
    for sample in phi_samples:
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi(sample)


def test_specialized_workers():
    # Worker 1: QC Invariant
    p1 = SystemTaskPayload(task_id="T1", target_identifier="KEY-01", primary_metric=35.0)
    alerts1 = InvariantQCWorker.evaluate(p1)
    assert len(alerts1) == 1
    assert alerts1[0].urgency == UrgencyLevel.ELEVATED

    # Worker 2: Safety
    p2 = SystemTaskPayload(task_id="T2", target_identifier="KEY-02", primary_metric=10.0, is_critical_flag=True)
    alerts2 = SafetyEscalationWorker.evaluate(p2)
    assert len(alerts2) == 1
    assert alerts2[0].urgency == UrgencyLevel.CRITICAL_STAT

    # Worker 3: Protocol Conformance
    p3 = SystemTaskPayload(task_id="T3", target_identifier="KEY-03", primary_metric=10.0, status_descriptor="DISCORDANT_ANOMALY")
    alerts3 = ProtocolConformanceWorker.evaluate(p3)
    assert len(alerts3) == 1


def test_workers_no_alerts_on_nominal():
    """Nominal payloads should produce no alerts."""
    p = SystemTaskPayload(task_id="T-NOM", target_identifier="KEY-NOM", primary_metric=10.0, secondary_metric=3.0, status_descriptor="NOMINAL")
    assert len(InvariantQCWorker.evaluate(p)) == 0
    assert len(SafetyEscalationWorker.evaluate(p)) == 0
    assert len(ProtocolConformanceWorker.evaluate(p)) == 0


def test_supervisor_consensus_and_audit():
    supervisor = SystemSupervisor(model_provider="mock")
    payload = SystemTaskPayload(
        task_id="TASK-PROD-01",
        target_identifier="KEY-PROD-01",
        primary_metric=12.0,
        secondary_metric=4.0,
        status_descriptor="NOMINAL"
    )
    dossier = supervisor.process_task(payload)
    assert dossier.overall_urgency == UrgencyLevel.ROUTINE
    assert dossier.integrity_status == SystemIntegrityStatus.VALIDATED
    assert dossier.audit_hash != ""

    # Verify cryptographic audit trail
    assert AuditLogger.verify_integrity() is True

    # CLI tests
    assert main(["audit", "--task-id", "CLI-TEST-01"]) == 0
    assert main(["chat", "Explain", "specifications"]) == 0
    assert main(["verify-audit"]) == 0


def test_supervisor_input_validation():
    """Supervisor should reject invalid inputs."""
    supervisor = SystemSupervisor(model_provider="mock")

    # Empty task_id should be caught by PHI guard or validation
    with pytest.raises(Exception):
        p = SystemTaskPayload(task_id=" ", target_identifier="KEY-01", primary_metric=float('nan'))
        supervisor.process_task(p)


def test_audit_trail_requires_key():
    """AuditTrail should require a valid key."""
    # Without env var and without explicit key, should generate one
    old_key = os.environ.pop("AUDIT_SECRET_KEY", None)
    try:
        trail = AuditTrail()
        assert len(trail.logs) == 0
        # Log an entry
        entry = trail.log("test", "test_tier", "TEST_EVENT", {"key": "value"})
        assert entry["audit_id"].startswith("AUDIT-")
        assert entry["current_hash"] != ""
    finally:
        if old_key:
            os.environ["AUDIT_SECRET_KEY"] = old_key


def test_audit_trail_short_key_rejected():
    """Short keys should be rejected for security."""
    with pytest.raises(ValueError, match="at least 16 characters"):
        AuditTrail(secret_key="short")


def test_batch_cli_missing_file():
    """CLI batch should fail gracefully on missing input file."""
    result = main(["batch", "-i", "nonexistent_file_12345.csv"])
    assert result == 1


def test_cli_batch_with_sample():
    """CLI batch should process sample.csv successfully."""
    result = main(["batch", "-i", "sample.csv", "-o", "test_output.csv"])
    assert result == 0
    # Clean up
    if os.path.exists("test_output.csv"):
        os.remove("test_output.csv")
