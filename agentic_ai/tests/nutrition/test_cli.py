import json

import pytest

from agentic_ai import nutrition_demo
from agentic_ai.clients import usda_client
from agentic_ai.nutrition_errors import NutritionInputError


def test_offline_examples_use_no_network_or_model(monkeypatch,capsys):
    monkeypatch.setattr(usda_client,"urlopen",lambda *a,**k:pytest.fail("unexpected network"))
    monkeypatch.setattr(nutrition_demo,"FoodUnderstandingAgent",lambda *a,**k:pytest.fail("unexpected model"))
    assert nutrition_demo.main(["--offline-examples"])==0
    results=[json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [r["nutrition"]["status"] for r in results]==["complete","complete","complete","needs_clarification","partial","needs_clarification"]
    assert all("no model inference" in r["extraction_mode"] for r in results)
    assert results[0]["nutrition"]["complete_totals"]["calories"]=="350.0000"


def test_input_json_can_resolve_id_and_portion(tmp_path,meal,item,capsys):
    path=tmp_path/"extraction.json"
    path.write_text(meal(item(name="banana",quantity=2,unit="piece",preparation=None,source_text="2 bananas")).model_dump_json(),encoding="utf-8")
    assert nutrition_demo.main(["--input-json",str(path),"--select","0:173944:93515"])==0
    result=json.loads(capsys.readouterr().out)["nutrition"]
    assert result["items"][0]["portion"]["requested_grams"]=="236.0"
    assert result["complete_totals"]["calories"]=="210.0400"


def test_invalid_input_file_is_clear(tmp_path,capsys):
    path=tmp_path/"bad.json"
    path.write_text("not json")
    assert nutrition_demo.main(["--input-json",str(path)])==1
    assert json.loads(capsys.readouterr().out)["error"]["code"]=="invalid_input_file"


@pytest.mark.parametrize("selection",["bad","0:bad","0:1:2:3","-1:2"])
def test_cli_selection_syntax_errors_are_clear(selection):
    with pytest.raises(NutritionInputError): nutrition_demo.parse_selections([selection],[])


def test_live_provider_missing_key_is_not_replaced_by_snapshot(tmp_path,meal,item,capsys,monkeypatch):
    from agentic_ai.nutrition_config import NutritionSettings
    monkeypatch.setattr(NutritionSettings,"from_environment",classmethod(lambda cls:cls()))
    path=tmp_path/"meal.json"
    path.write_text(meal(item()).model_dump_json(),encoding="utf-8")
    assert nutrition_demo.main(["--input-json",str(path),"--provider","live"])==1
    result=json.loads(capsys.readouterr().out)
    assert result["nutrition_provider"]=="live"
    assert result["nutrition"]["items"][0]["issues"][0]["code"]=="usda_credentials_missing"
