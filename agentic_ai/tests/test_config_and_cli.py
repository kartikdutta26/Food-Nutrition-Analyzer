import json

import pytest
from pydantic import ValidationError

from agentic_ai import demo
from agentic_ai.config import Settings
from agentic_ai.errors import ConfigurationError, OllamaTimeoutError
from agentic_ai.schemas.food import FoodUnderstandingResult


@pytest.mark.parametrize("url", ["file:///tmp/model", "http://u:p@localhost", "http://localhost/api", "http://localhost?key=x", "http://localhost:bad"])
def test_invalid_server_configuration_is_rejected(url):
    with pytest.raises(ValidationError):
        Settings(base_url=url)


def test_env_file_is_explicit_and_process_environment_wins(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    path.write_text("OLLAMA_MODEL=file-model\nOLLAMA_TIMEOUT_SECONDS=30\n", encoding="utf-8")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:4b-instruct")
    monkeypatch.delenv("OLLAMA_TIMEOUT_SECONDS", raising=False)
    settings = Settings.from_environment(path)
    assert settings.model == "qwen3:4b-instruct" and settings.timeout_seconds == 30


@pytest.mark.parametrize("value", ["0", "nan", "infinity", "wrong"])
def test_bad_env_settings_produce_friendly_error(tmp_path, monkeypatch, value):
    monkeypatch.setenv("OLLAMA_TIMEOUT_SECONDS", value)
    with pytest.raises(ConfigurationError):
        Settings.from_environment(tmp_path / "missing")


def test_cli_success_outputs_json(monkeypatch, capsys):
    class Agent:
        settings = Settings()
        def analyze(self, text):
            return FoodUnderstandingResult(status="no_food", foods=[])
    monkeypatch.setattr(demo, "FoodUnderstandingAgent", Agent)
    assert demo.main(["--text", "The library opens tomorrow"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["result"]["status"] == "no_food"
    assert output["model"] == "qwen3:4b-instruct"


def test_cli_model_error_has_nonzero_exit_and_error_code(monkeypatch, capsys):
    class Agent:
        def analyze(self, text):
            raise OllamaTimeoutError("Timed out")
    monkeypatch.setattr(demo, "FoodUnderstandingAgent", Agent)
    assert demo.main(["--text", "2 eggs"]) == 1
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "ollama_timeout"
