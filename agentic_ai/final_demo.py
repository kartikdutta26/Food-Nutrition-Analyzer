"""Offline evaluation: SIMULATED vision/M1 and scripted DEMO USER confirmation;
real preprocessing, M3, M2 snapshot calculations and deterministic M4.
No model inference, live USDA, authentication or application services are used.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory


class FinalDemoError(Exception):
    """A demonstration failed its presentation checks; never expose raw errors."""


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's default error may echo private paths/untrusted arguments.
        raise FinalDemoError("invalid_arguments")


def _disclosure():
    # This literal remains available even when optional decoder imports fail.
    return {
        "image": "generated synthetic pixels, not a food photograph",
        "vision": "SIMULATED scripted food candidates and placeholder model identity; no recognition accuracy claim",
        "M1": "SIMULATED scripted extraction transport; real M1 validation/normalization",
        "confirmation": "explicit scripted DEMO USER choices, not an interactive human confirmation",
        "M2_M3": "real existing orchestration/calculations using authentic integrity-checked OFFLINE USDA snapshots",
        "M4": "real deterministic evidence-consistency checks and interpretation; not medical advice",
        "services": "NO network/model inference/live USDA/authentication/database/application services",
    }


def _checked_example(scenario, image_path):
    from agentic_ai.image_workflow_demo import DISCLOSURE, run_example
    from agentic_ai.schemas.image_workflow import ImageWorkflowSnapshot

    # Reuse the complete M5.5 scenario, including its explicit confirmation,
    # clarification replies, recommendation request and workflow cleanup.
    report = run_example(scenario, image_path)
    # The existing demo returns JSON-mode data: strict tuple fields must be
    # decoded through Pydantic's JSON path, not treated as Python-list inputs.
    state = ImageWorkflowSnapshot.model_validate_json(json.dumps(report["snapshot"]))
    session, handoff, guidance = state.session, state.handoff, state.recommendations
    if (report["scenario"] != scenario or report["disclosure"] != DISCLOSURE
            or session is None or session.nutrition is None or handoff is None
            or guidance is None or state.phase != "session_started"):
        raise FinalDemoError("invalid_demo_result")
    nutrition = session.nutrition
    expected = ("complete", "ready") if scenario == "complete" else ("partial", "limited")
    if (session.status != "completed" or (nutrition.status, guidance.status) != expected
            or not handoff.confirmation.user_confirmed
            or handoff.recognition != state.recognition
            or report["extraction_inputs"] != [handoff.confirmation.confirmed_meal_text]
            or report["transitions"][0] != {"phase": "awaiting_confirmation", "session": None}
            or guidance.input_ref.session_id != session.session_id
            or guidance.input_ref.revision != session.revision
            or guidance.complete_totals != nutrition.complete_totals
            or guidance.known_subtotals != nutrition.known_subtotals
            or guidance.coverage != nutrition.coverage
            or not guidance.citations
            or any(c.provenance.provider != "usda_snapshot" or not c.provenance.snapshot_sha256
                   for c in guidance.citations)):
        raise FinalDemoError("invalid_demo_result")
    if scenario == "partial" and any(
            value is not None for value in nutrition.complete_totals.model_dump().values()):
        raise FinalDemoError("invalid_demo_result")
    # Keep the original nested contracts, nulls, decimal strings and provenance.
    # This is a demo report, not a new production AI/API contract.
    return {
        "scenario": scenario,
        "transitions": report["transitions"],
        "recognition": state.recognition.model_dump(mode="json"),
        "confirmation": handoff.confirmation.model_dump(mode="json"),
        "session": session.model_dump(mode="json"),
        "recommendations": guidance.model_dump(mode="json"),
    }


def build_report(scenario="all"):
    """Run only the fixed offline cases; nutrition is never supplied by this file.

    IDs/timestamps vary by design. Nutrients, choices and outcomes are deterministic.
    Returns nothing on a failed case: callers cannot mistake a partial run for success.
    """
    if scenario not in ("complete", "partial", "all"):
        raise FinalDemoError("invalid_arguments")
    from PIL import Image

    root = Path(__file__).resolve().parent
    with TemporaryDirectory(prefix=".test-tmp-m56-demo-", dir=root) as temporary:
        directory = Path(temporary).resolve()
        if directory.parent != root or not directory.name.startswith(".test-tmp-m56-demo-"):
            raise FinalDemoError("local_io_failed")
        image_path = directory / "synthetic.png"
        with Image.new("RGBA", (24, 16), (30, 90, 140, 200)) as image:
            image.save(image_path, format="PNG")
        runs = [_checked_example(case, image_path) for case in
                (("complete", "partial") if scenario == "all" else (scenario,))]
    return {"demonstration": "NutriAI M5.6 OFFLINE evaluation", "status": "ok",
            "disclosure": _disclosure(), "runs": runs}


def _amounts(values):
    return ", ".join(f"{name}={'unknown' if value is None else value} "
                     f"{'kcal' if name == 'calories' else 'g'}" for name, value in values.items())


def render_text(report):
    """Render unknowns explicitly and retain source/coverage context."""
    lines = [report["demonstration"]]
    lines.extend(f"{key}: {value}" for key, value in report["disclosure"].items())
    for run in report["runs"]:
        session, guidance = run["session"], run["recommendations"]
        nutrition = session["nutrition"]
        lines.extend(["", f"--- {run['scenario'].upper()} offline scenario ---",
                      f"SIMULATED vision: {run['recognition']['status']}"])
        for group in run["recognition"]["groups"]:
            lines.append("Candidate alternatives (not confirmed): " +
                         " / ".join(c["label"] for c in group["candidates"]))
        lines.append("Explicit scripted DEMO USER confirmation: " +
                     run["confirmation"]["confirmed_meal_text"])
        lines.append("M3 clarification/revision transitions: " + json.dumps(run["transitions"]))
        for evidence in session["evidence"]:
            lines.append(f"Scripted DEMO USER reply at revision {evidence['revision']}: " +
                         json.dumps(evidence["action"]))
        lines.extend([f"Real M3 session: {session['session_id']} revision {session['revision']} "
                      f"status {session['status']}; nutrition {nutrition['status']}",
                      "Complete meal totals: " + _amounts(nutrition["complete_totals"]),
                      "Known subtotals (not a complete meal when partial): " +
                      _amounts(nutrition["known_subtotals"])])
        for name, coverage in nutrition["coverage"].items():
            lines.append(f"{name} coverage: {coverage['known_items']}/{coverage['total_items']} food items")
        for item in nutrition["items"]:
            lines.append(f"M2 item {item['food']['name']}: {item['status']}; " + _amounts(item["nutrition"]))
        lines.append(f"Real deterministic M4: {guidance['status']}; revision "
                     f"{guidance['input_ref']['revision']}; scope {guidance['validation_scope']}")
        for category in ("observations", "suggestions", "next_steps", "limitations"):
            for message in guidance[category]:
                lines.append(f"M4 {category}: {message['text']} [evidence: " +
                             ", ".join(message["evidence_refs"]) + "]")
        for citation in guidance["citations"]:
            source = citation["provenance"]
            lines.extend([f"OFFLINE USDA FDC {source['fdc_id']}: {source['description']}",
                          f"  {source['source_url']}; retrieved {source['retrieved_at']}",
                          f"  snapshot SHA-256 {source['snapshot_sha256']}"])
    lines.append("Offline evaluation only: no live visual accuracy, medical validity or deployment readiness established.")
    return "\n".join(lines)


def main(argv=None):
    parser = _Parser(description=__doc__)
    parser.add_argument("--scenario", choices=("all", "complete", "partial"), default="all")
    parser.add_argument("--json", action="store_true", help="emit full existing session/recommendation contracts as JSON")
    try:
        args = parser.parse_args(argv)
        report = build_report(args.scenario)
        output = json.dumps(report, ensure_ascii=True) if args.json else render_text(report)
    except Exception as exc:
        code = "demonstration_failed"
        if isinstance(exc, FinalDemoError) and str(exc) in {
                "invalid_arguments", "invalid_demo_result", "local_io_failed"}:
            code = str(exc)
        elif isinstance(exc, ImportError):
            code = "dependency_unavailable"
        elif isinstance(exc, OSError):
            code = "local_io_failed"
        print(json.dumps({"demonstration": "NutriAI M5.6 OFFLINE evaluation", "status": "error",
                          "disclosure": _disclosure(), "error": {"code": code}}), file=sys.stderr)
        return 2 if code == "invalid_arguments" else 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
