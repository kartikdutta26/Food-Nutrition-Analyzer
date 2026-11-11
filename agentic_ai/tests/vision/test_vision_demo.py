"""CLI paths are tested with scripted clients, never mocked live-accuracy claims."""
from types import SimpleNamespace

import pytest

from agentic_ai import vision_demo
from agentic_ai.vision_runtime_errors import VisionRuntimeError


def ready_client(monkeypatch):
    class Client:
        def __init__(self, settings): pass
        def check_ready(self):
            from agentic_ai.clients.ollama_vision_client import LocalVisionModel
            return LocalVisionModel("qwen3-vl:2b", "sha256:"+"a"*64, "0.40.16")
    monkeypatch.setattr(vision_demo, "OllamaVisionClient", Client)


def test_cli_check_only_never_invokes_recognition(monkeypatch, capsys):
    ready_client(monkeypatch)
    monkeypatch.setattr(vision_demo, "available_ram_bytes", lambda: 5*2**30)
    monkeypatch.setattr(vision_demo, "ImageFoodRecognitionAgent", lambda **kwargs: pytest.fail("check ran inference"))
    assert vision_demo.main(["--check"]) == 0
    captured = capsys.readouterr()
    assert '"inference_tested": false' in captured.out and '5.0' in captured.err


def test_cli_refuses_low_memory_without_terminating_apps(monkeypatch, capsys):
    ready_client(monkeypatch)
    monkeypatch.setattr(vision_demo, "available_ram_bytes", lambda: 2**30)
    monkeypatch.setattr(vision_demo, "ImageFoodRecognitionAgent", lambda **kwargs: pytest.fail("low-memory inference"))
    assert vision_demo.main(["--image", "PRIVATE_PATH.jpg"]) == 2
    captured = capsys.readouterr()
    assert "insufficient_memory" in captured.err
    assert "PRIVATE_PATH" not in captured.err + captured.out


@pytest.mark.parametrize("args", [["--unknown", "PRIVATE"], ["--base-url", "https://remote.invalid"], ["--check", "--image", "PRIVATE.png"]])
def test_cli_invalid_input_does_not_echo_private_arguments(args, capsys):
    assert vision_demo.main(args) == 2
    captured = capsys.readouterr()
    assert "invalid_configuration" in captured.err and "PRIVATE" not in captured.err+captured.out


def test_cli_service_failure_is_not_a_recognition_result(monkeypatch, capsys):
    monkeypatch.setattr(vision_demo, "available_ram_bytes", lambda: 5*2**30)
    class Client:
        def __init__(self, settings): pass
        def check_ready(self): raise VisionRuntimeError("model_missing")
    monkeypatch.setattr(vision_demo, "OllamaVisionClient", Client)
    assert vision_demo.main([]) == 2
    captured = capsys.readouterr()
    assert "model_missing" in captured.err and not captured.out


def test_cli_approved_image_path_passes_to_agent_without_printing_it(monkeypatch, capsys):
    ready_client(monkeypatch)
    monkeypatch.setattr(vision_demo, "available_ram_bytes", lambda: 5*2**30)
    calls = []
    class Agent:
        def __init__(self, **kwargs): pass
        def analyze(self, path):
            calls.append(path)
            return SimpleNamespace(model_dump_json=lambda **kwargs: '{"status":"uncertain"}')
    monkeypatch.setattr(vision_demo, "ImageFoodRecognitionAgent", Agent)
    assert vision_demo.main(["--image", "PRIVATE_PATH.jpg"]) == 0
    captured = capsys.readouterr()
    assert calls == ["PRIVATE_PATH.jpg"] and "PRIVATE_PATH" not in captured.out+captured.err


def test_memory_probe_failure_is_safe(monkeypatch, capsys):
    monkeypatch.setattr(vision_demo, "available_ram_bytes", lambda: (_ for _ in ()).throw(VisionRuntimeError("memory_unavailable")))
    assert vision_demo.main([]) == 2
    assert "memory_unavailable" in capsys.readouterr().err
