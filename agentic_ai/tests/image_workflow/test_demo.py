import json

import pytest

from agentic_ai.image_workflow_demo import main


@pytest.mark.parametrize("scenario", ["complete", "partial", "all"])
def test_real_offline_cli_discloses_simulation_and_snapshot_provenance(scenario, capsys):
    assert main(["--scenario", scenario]) == 0
    captured = capsys.readouterr()
    assert not captured.err
    reports = [json.loads(line) for line in captured.out.splitlines()]
    assert len(reports) == (2 if scenario == "all" else 1)
    for report in reports:
        assert "SIMULATED" in report["disclosure"]["vision"]
        assert "SIMULATED" in report["disclosure"]["M1"]
        assert "DEMO USER" in report["disclosure"]["confirmation"]
        assert "authentic" in report["disclosure"]["M2_M3"]
        assert "no live USDA" in report["disclosure"]["network"]
        assert report["vision_calls"] == 1
        state = report["snapshot"]
        assert report["extraction_inputs"] == [state["handoff"]["confirmation"]["confirmed_meal_text"]]
        assert state["recognition"]["status"] == "uncertain"
        assert state["session"]["status"] == "completed"
        nutrition, recommendations = state["session"]["nutrition"], state["recommendations"]
        assert recommendations["input_ref"]["revision"] == state["session"]["revision"]
        assert all(c["provenance"]["provider"] == "usda_snapshot" and c["provenance"]["snapshot_sha256"] for c in recommendations["citations"])
        assert "synthetic.png" not in captured.out and "processed_bytes" not in captured.out
        if report["scenario"] == "complete":
            assert nutrition["status"] == "complete" and recommendations["status"] == "ready"
            assert nutrition["complete_totals"]["calories"] == "244.0000"
            assert {c["provenance"]["fdc_id"] for c in recommendations["citations"]} == {173944, 173424}
        else:
            assert nutrition["status"] == "partial" and recommendations["status"] == "limited"
            assert nutrition["complete_totals"]["calories"] is None
            assert nutrition["known_subtotals"]["calories"] == "89.0000"
