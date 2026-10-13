"""Regression tests for audit authenticity, input validation, CSV output, and browser syntax."""
import csv
import shutil
import subprocess
import re
from pathlib import Path

import pytest

from agents.base import AuditTrail, GLOBAL_AUDIT, SecurityException
from agents.models import SystemTaskPayload
from agents.supervisor import SystemSupervisor
from cli import main


def test_hmac_detects_modified_signed_field_and_digest():
    trail = AuditTrail(secret_key="a sufficiently long test signing key")
    trail.log("operator", "test", "EVALUATION", {"count": 1})
    trail.log("operator", "test", "EVALUATION", {"count": 2})
    assert trail.verify_integrity()
    trail.logs[0]["event_type"] = "FORGED"
    assert not trail.verify_integrity()
    trail.logs[0]["event_type"] = "EVALUATION"
    assert trail.verify_integrity()
    trail.logs[-1]["current_hash"] = "0" * 64
    assert not trail.verify_integrity()


def test_audit_trail_snapshot_is_not_mutable_reference():
    trail = AuditTrail(secret_key="a sufficiently long test signing key")
    trail.log("operator", "test", "EVALUATION", {"count": 1})
    snapshot = trail.get_trail()
    snapshot[0]["event_type"] = "FORGED"
    snapshot.clear()
    assert len(trail.logs) == 1
    assert trail.verify_integrity()


def test_critical_fields_reject_phi_and_blank_identifiers():
    supervisor = SystemSupervisor()
    with pytest.raises(SecurityException):
        supervisor.process_task(SystemTaskPayload(
            task_id="T-1", target_identifier="S-1", primary_metric=1,
            attributes={"nested": {"email": "person@example.com"}}))
    for task, target in [("   ", "S-1"), ("T-1", "   ")]:
        with pytest.raises(ValueError):
            supervisor.process_task(SystemTaskPayload(
                task_id=task, target_identifier=target, primary_metric=1))


def test_cli_verify_returns_nonzero_on_forgery():
    previous = list(GLOBAL_AUDIT.logs)
    try:
        GLOBAL_AUDIT.logs.clear()
        GLOBAL_AUDIT.log("test", "operator", "EVALUATION", {"count": 1})
        assert main(["verify-audit"]) == 0
        GLOBAL_AUDIT.logs[0]["event_type"] = "FORGED"
        assert main(["verify-audit"]) == 1
    finally:
        GLOBAL_AUDIT.logs[:] = previous


def test_csv_formula_export_and_existing_result_columns(tmp_path):
    source = tmp_path / "cases.csv"
    dest = tmp_path / "results.csv"
    with source.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "task_id", "target_identifier", "primary_metric", "overall_urgency"])
        writer.writeheader()
        writer.writerow({"task_id": "DEMO-1", "target_identifier": "=1+1",
                         "primary_metric": "10", "overall_urgency": "old"})
    assert main(["batch", "-i", str(source), "-o", str(dest)]) == 0
    with dest.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["target_identifier"] == "'=1+1"
    assert rows[0]["overall_urgency"] == "ROUTINE"


def test_csv_missing_header_fails_gracefully(tmp_path):
    source = tmp_path / "empty.csv"
    source.write_text("", encoding="utf-8")
    assert main(["batch", "-i", str(source), "-o", str(tmp_path / "out.csv")]) == 1


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is unavailable")
def test_static_browser_script_has_valid_javascript():
    html = (Path(__file__).parent.parent / "web" / "index.html").read_text(encoding="utf-8")
    match = re.search(r"<script>(.*?)</script>", html, flags=re.S)
    assert match
    subprocess.run(["node", "--check"], input=match.group(1), text=True, check=True)


def test_audit_log_route_requires_opt_in_token(monkeypatch):
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    from agents.api import app

    client = TestClient(app)
    monkeypatch.delenv("AUDIT_LOGS_TOKEN", raising=False)
    assert client.get("/api/audit/logs").status_code == 403
    monkeypatch.setenv("AUDIT_LOGS_TOKEN", "dedicated-secret-token-for-tests")
    assert client.get("/api/audit/logs").status_code == 403
    response = client.get("/api/audit/logs",
                          headers={"X-Audit-Token": "dedicated-secret-token-for-tests"})
    assert response.status_code == 200
    assert response.json()["verified"] is True
