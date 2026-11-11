"""All final-demo tests reject real model transports and network connections."""
import socket

import pytest

from agentic_ai.clients.ollama_client import OllamaClient
from agentic_ai.clients.ollama_vision_client import OllamaVisionClient
from agentic_ai.final_demo import build_report


@pytest.fixture(autouse=True)
def offline_only(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Final demo must not use a network/model transport")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(OllamaClient, "chat", forbidden)
    monkeypatch.setattr(OllamaVisionClient, "analyze", forbidden)


@pytest.fixture
def report():
    return build_report()
