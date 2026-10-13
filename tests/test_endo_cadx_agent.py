import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from endo_cadx_agent.models import FrontierPayload, ExecutionStatus
from endo_cadx_agent.engine import FrontierDomainEngine
from endo_cadx_agent.agents import VesselPatternClassifierAgent, SurfacePitAnalyzerAgent, NICECategoryMatcherAgent, EndoCADxCoordinator
from endo_cadx_agent.cli import main


def test_sub_agents():
    a1 = VesselPatternClassifierAgent()
    p1 = FrontierPayload("T1", "KEY-01", primary_metric=35.0, secondary_metric=4.0, status_descriptor="NOMINAL")
    alerts1 = a1.audit(p1)
    assert len(alerts1) == 1
    assert alerts1[0].status == ExecutionStatus.ELEVATED_RISK

    a2 = SurfacePitAnalyzerAgent()
    p2 = FrontierPayload("T2", "KEY-02", primary_metric=10.0, secondary_metric=15.0, status_descriptor="NOMINAL", is_critical_flag=True)
    alerts2 = a2.audit(p2)
    assert len(alerts2) == 1
    assert alerts2[0].status == ExecutionStatus.CRITICAL_INTERVENTION

    a3 = NICECategoryMatcherAgent()
    p3 = FrontierPayload("T3", "KEY-03", primary_metric=10.0, secondary_metric=4.0, status_descriptor="DISCORDANT_ANOMALY")
    alerts3 = a3.audit(p3)
    assert len(alerts3) == 1


def test_coordinator():
    coord = EndoCADxCoordinator()
    p_nominal = FrontierPayload("T4", "KEY-04", primary_metric=12.0, secondary_metric=4.0, status_descriptor="NOMINAL")
    dossier = coord.process(p_nominal)
    assert dossier["overall_status"] == ExecutionStatus.NOMINAL.value
    assert dossier["total_alerts"] == 0

    ans = coord.query_supervisory_chat("What standard is applied?")
    assert "ESGE / NICE Endoscopic Polyp Criteria" in ans or "specifications" in ans


def test_cli():
    assert main(["audit", "--task-id", "CLI-01"]) == 0
    assert main(["chat", "What", "is", "the", "system", "status?"]) == 0


def test_alternate_csv_false_flag_remains_noncritical(tmp_path):
    import csv
    from endo_cadx_agent.cli import main as alt_main

    source = tmp_path / "input.csv"
    target = tmp_path / "output.csv"
    source.write_text(
        "task_id,target_identifier,primary_metric,secondary_metric,is_critical_flag,status_descriptor\n"
        "DEMO-1,SAMPLE-1,12,4,False,NOMINAL\n",
        encoding="utf-8",
    )
    assert alt_main(["batch", "--input", str(source), "--output", str(target)]) == 0
    with target.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["overall_status"] == ExecutionStatus.NOMINAL.value
    assert rows[0]["critical_count"] == "0"


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_alternate_engine_rejects_nonfinite_metrics(bad):
    coord = EndoCADxCoordinator()
    for primary, secondary in [(bad, 0.0), (0.0, bad)]:
        payload = FrontierPayload("DEMO-1", "SAMPLE-1", primary, secondary, "NOMINAL")
        with pytest.raises(ValueError, match="finite"):
            coord.process(payload)
