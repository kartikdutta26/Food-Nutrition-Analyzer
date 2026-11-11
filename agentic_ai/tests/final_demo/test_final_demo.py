"""Real offline pipeline acceptance; injected faults are not live service tests."""
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path

import pytest

from agentic_ai import final_demo, image_workflow_demo
from agentic_ai.providers.usda import SnapshotProvider


def test_both_scenarios_use_explicit_confirmation_and_revision_bound_m4(report):
    assert report["status"] == "ok"
    assert [r["scenario"] for r in report["runs"]] == ["complete", "partial"]
    for run, revision in zip(report["runs"], (4, 2)):
        confirmation, session, guidance = run["confirmation"], run["session"], run["recommendations"]
        assert confirmation["user_confirmed"] is True
        assert confirmation["expected_result_id"] == run["recognition"]["result_id"]
        assert run["transitions"][0] == {"phase": "awaiting_confirmation", "session": None}
        assert run["transitions"][1]["status"] == "awaiting_clarification"
        assert session["revision"] == revision
        assert guidance["input_ref"]["revision"] == revision
        assert guidance["input_ref"]["session_id"] == session["session_id"]
        assert guidance["generation_mode"] == "deterministic"
        assert guidance["validation_scope"] == "supplied_record_consistency_only"
        assert guidance["comparisons"] == []  # No invented goals/targets.
        assert guidance["complete_totals"] == session["nutrition"]["complete_totals"]
        assert guidance["known_subtotals"] == session["nutrition"]["known_subtotals"]
        assert guidance["coverage"] == session["nutrition"]["coverage"]


def test_no_photo_quantities_or_synthetic_nutrition_enter_the_output(report):
    provider = SnapshotProvider()  # Independently reads/checks the authentic catalog.
    directory = Path(__file__).resolve().parents[2] / "data" / "usda"
    manifest = json.loads((directory / "manifest.json").read_text())
    assert hashlib.sha256((directory / "foods.json").read_bytes()).hexdigest() == manifest["sha256"]
    for run in report["runs"]:
        recognition = run["recognition"]
        assert recognition["model_provenance"]["model_digest"] == "sha256:" + "0" * 64
        for group in recognition["groups"]:
            for candidate in group["candidates"]:
                # All numeric hypotheses are explicitly absent/null, never portions.
                for key in ("quantity", "edible_grams", "nutrition", "fdc_id", "confidence"):
                    assert candidate.get(key) is None
        for citation in run["recommendations"]["citations"]:
            record = provider.get(citation["provenance"]["fdc_id"])
            assert citation["provenance"] == record.provenance.model_dump(mode="json")
            assert citation["source_nutrients"] == record.nutrients.model_dump(mode="json")
            assert citation["nutrient_evidence"] == {
                key: value.model_dump(mode="json") for key, value in record.nutrient_evidence.items()}


def test_complete_and_partial_results_are_distinct_without_zero_filling(report):
    complete, partial = report["runs"]
    nutrition = complete["session"]["nutrition"]
    assert nutrition["status"] == "complete"
    assert nutrition["complete_totals"] == {"calories": "244.0000", "protein": "13.6700",
                                           "carbs": "23.9600", "fats": "10.9400", "fiber": "2.6000"}
    assert complete["recommendations"]["status"] == "ready"
    assert {c["provenance"]["fdc_id"] for c in complete["recommendations"]["citations"]} == {173944, 173424}
    nutrition = partial["session"]["nutrition"]
    assert nutrition["status"] == "partial"
    assert all(value is None for value in nutrition["complete_totals"].values())
    assert nutrition["known_subtotals"]["calories"] == "89.0000"
    assert all(c == {"known_items": 1, "total_items": 2, "complete": False} for c in nutrition["coverage"].values())
    curry = nutrition["items"][1]
    assert curry["record"] is None
    assert all(value is None for value in curry["nutrition"].values())
    assert partial["recommendations"]["status"] == "limited"
    assert {c["provenance"]["fdc_id"] for c in partial["recommendations"]["citations"]} == {173944}


@pytest.mark.parametrize("scenario,count", [("complete", 1), ("partial", 1), ("all", 2)])
@pytest.mark.parametrize("as_json", [False, True])
def test_command_reports_disclosures_unknowns_and_citations(scenario, count, as_json, capsys):
    assert final_demo.main(["--scenario", scenario] + (["--json"] if as_json else [])) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    for phrase in ("SIMULATED", "DEMO USER", "OFFLINE", "integrity-checked", "not medical advice"):
        assert phrase in captured.out
    assert "synthetic.png" not in captured.out
    assert "processed_bytes" not in captured.out
    assert "data:image" not in captured.out
    if as_json:
        assert len(json.loads(captured.out)["runs"]) == count
    else:
        assert "M3 session:" in captured.out and "M4:" in captured.out
        assert "snapshot SHA-256" in captured.out
        if scenario != "complete":
            assert "Complete meal totals: calories=unknown kcal" in captured.out
            assert "Known subtotals (not a complete meal when partial): calories=89.0000 kcal" in captured.out


def test_repeated_runs_keep_nutrition_but_do_not_reuse_sessions():
    first = final_demo.build_report("complete")["runs"][0]
    second = final_demo.build_report("complete")["runs"][0]
    assert first["session"]["session_id"] != second["session"]["session_id"]
    assert first["session"]["nutrition"] == second["session"]["nutrition"]
    assert first["confirmation"]["confirmed_meal_text"] == second["confirmation"]["confirmed_meal_text"]


def test_command_reuses_m55_functions_and_cleans_generated_images(monkeypatch):
    original = image_workflow_demo.run_example
    calls = []
    def recorded(scenario, path):
        assert path.is_file()
        calls.append((scenario, path))
        return original(scenario, path)
    monkeypatch.setattr(image_workflow_demo, "run_example", recorded)
    final_demo.build_report()
    assert [case for case, path in calls] == ["complete", "partial"]
    assert all(not path.exists() and not path.parent.exists() for case, path in calls)


@pytest.mark.parametrize("fault", ["stale_revision", "missing_confirmation", "fabricated_total", "wrong_provider", "wrong_disclosure"])
def test_presentation_guard_rejects_corrupted_demo_results(monkeypatch, fault, capsys):
    original = image_workflow_demo.run_example
    def corrupted(scenario, path):
        report = deepcopy(original(scenario, path))
        state = report["snapshot"]
        if fault == "stale_revision":
            state["recommendations"]["input_ref"]["revision"] += 1
        elif fault == "missing_confirmation":
            state["handoff"] = None
        elif fault == "fabricated_total":
            state["session"]["nutrition"]["complete_totals"]["calories"] = "9999"
        elif fault == "wrong_provider":
            state["recommendations"]["citations"][0]["provenance"]["provider"] = "usda_live"
        else:
            report["disclosure"] = {}
        return report
    monkeypatch.setattr(image_workflow_demo, "run_example", corrupted)
    assert final_demo.main(["--json"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err)["status"] == "error"


@pytest.mark.parametrize("exception,code", [
    (RuntimeError("private image path and raw model payload"), "demonstration_failed"),
    (OSError("private image path"), "local_io_failed"),
    (ModuleNotFoundError("private dependency location"), "dependency_unavailable"),
])
def test_failures_are_atomic_sanitized_and_cleaned(monkeypatch, exception, code, capsys):
    original = image_workflow_demo.run_example
    paths = []
    def failing(scenario, path):
        paths.append(path)
        if scenario == "partial":
            raise exception
        return original(scenario, path)
    monkeypatch.setattr(image_workflow_demo, "run_example", failing)
    assert final_demo.main([]) == 1
    captured = capsys.readouterr()
    assert not captured.out  # Complete case must not imply the whole evaluation passed.
    assert "private" not in captured.err
    error = json.loads(captured.err)
    assert error["error"]["code"] == code and error["disclosure"]["vision"].startswith("SIMULATED")
    assert all(not path.exists() and not path.parent.exists() for path in paths)


def test_corrupt_snapshot_fails_closed_without_changing_catalog(monkeypatch, tmp_path, capsys):
    directory = Path(__file__).resolve().parents[2] / "data" / "usda"
    # Deliberately corrupted COPY: production fixture is never edited.
    (tmp_path / "manifest.json").write_bytes((directory / "manifest.json").read_bytes())
    (tmp_path / "foods.json").write_bytes(b"[]")
    monkeypatch.setattr(image_workflow_demo, "SnapshotProvider", lambda: SnapshotProvider(tmp_path))
    assert final_demo.main([]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert json.loads(output.err)["error"]["code"] == "demonstration_failed"
    assert SnapshotProvider().get(173944).nutrients.calories == Decimal("89")


@pytest.mark.parametrize("args", [["--scenario", "private.jpg"], ["--image", "private.jpg"], ["--provider", "live"], ["--model", "qwen3-vl:2b"]])
def test_no_real_image_model_or_provider_options(args, capsys):
    assert final_demo.main(args) == 2
    captured = capsys.readouterr()
    assert not captured.out
    assert "private.jpg" not in captured.err
    assert json.loads(captured.err)["error"]["code"] == "invalid_arguments"


def test_help_explains_simulation_without_running_workflow(monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        pytest.fail("Help must not run a workflow")
    monkeypatch.setattr(final_demo, "build_report", forbidden)
    with pytest.raises(SystemExit) as exc:
        final_demo.main(["--help"])
    assert exc.value.code == 0
    output = capsys.readouterr().out
    assert "SIMULATED" in output and "scripted DEMO USER" in output
    assert "No model inference" in " ".join(output.split())
