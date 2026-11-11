import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from agentic_ai.recommendation_demo import main


def test_offline_cli_is_explicit_about_snapshot_and_no_inference(capsys):
    assert main(["--offline-examples"])==0
    rows=[json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert len(rows)==6
    assert [r["result"]["status"] for r in rows]==["ready","limited","ready","unavailable","limited","unavailable"]
    assert all("no model inference" in r["extraction_mode"] for r in rows)
    assert all("no live USDA request" in r["nutrition_provider"] for r in rows)
    assert all("no Qwen ranking" in r["recommendation_mode"] for r in rows)
    assert rows[4]["result"]["known_subtotals"]["calories"]=="89.0000"


def test_real_cli_subprocess():
    env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"}
    result=subprocess.run([sys.executable,"-B","-m","agentic_ai.recommendation_demo","--offline-examples"],
        cwd=Path(__file__).parents[3],capture_output=True,text=True,timeout=30,env=env)
    assert result.returncode==0 and not result.stderr
    assert len(result.stdout.splitlines())==6

@pytest.mark.parametrize("kind",["nutrition","session","request"])
def test_existing_json_input_cli(complete,session_factory,tmp_path,capsys,kind):
    source=complete.model_dump(mode="json") if kind!="session" else session_factory()[1].model_dump(mode="json")
    if kind=="request":source={"source":{"kind":"nutrition","result":source}}
    path=tmp_path/"input.json";path.write_text(json.dumps(source))
    args=["--input-json",str(path),"--kind",kind]
    if kind=="session":args += ["--expected-revision",str(source["revision"])]
    assert main(args)==0
    output=json.loads(capsys.readouterr().out)
    assert output["status"]==("unavailable" if kind=="session" else "ready")
    assert output["generation_mode"]=="deterministic"
    if kind=="session":assert output["input_ref"]["expired"]


def test_cli_context_targets(complete,tmp_path,capsys):
    source=tmp_path/"source.json";source.write_text(complete.model_dump_json())
    context=tmp_path/"context.json";context.write_text(json.dumps({"targets":[{"nutrient":"protein","value":"20","unit":"g","scope":"daily"}]}))
    assert main(["--input-json",str(source),"--context-json",str(context)])==0
    output=json.loads(capsys.readouterr().out)
    assert output["comparisons"][0]["reason"]=="scope_mismatch"

@pytest.mark.parametrize("content",['{"token":"secret-sensitive-value", broken','{"x":1,"x":2}','NaN','[]',' '*4_194_305])
def test_cli_safe_failure(tmp_path,capsys,content):
    path=tmp_path/"private-input.json";path.write_text(content)
    assert main(["--input-json",str(path)])==1
    output=capsys.readouterr().out
    assert "secret-sensitive-value" not in output and str(path) not in output
    assert json.loads(output)["status"]=="error"


def test_missing_file_cli(tmp_path,capsys):
    assert main(["--input-json",str(tmp_path/"absent-secret.json")])==1
    output=capsys.readouterr().out
    assert "absent-secret" not in output

@pytest.mark.parametrize("args",[["--offline-examples","--expected-revision","1"],["--offline-examples","--kind","session"]])
def test_cli_invalid_mode_combinations(capsys,args):
    assert main(args)==1
    assert json.loads(capsys.readouterr().out)["error"]["code"]=="invalid_input"
