import json

import pytest


class ScriptedClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def chat(self, messages, schema):
        self.calls.append((list(messages), schema))
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response if isinstance(response, str) else json.dumps(response)


@pytest.fixture
def food():
    def make(source_text="2 boiled eggs", **changes):
        return {
            "name": "egg", "quantity_text": "2", "unit": "piece",
            "preparation": "boiled", "source_text": source_text, **changes,
        }
    return make


@pytest.fixture
def client_factory():
    return lambda *responses: ScriptedClient(responses)
