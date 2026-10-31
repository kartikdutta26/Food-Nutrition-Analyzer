import hashlib
import io
import json
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from agentic_ai.clients import usda_client
from agentic_ai.clients.usda_client import USDAClient
from agentic_ai.nutrition_config import NutritionSettings
from agentic_ai.nutrition_errors import (FoodNotFoundError, MissingCredentialsError, SnapshotError, USDAAuthenticationError, USDAConnectionError, USDARateLimitError, USDAResponseError, USDATimeoutError)
from agentic_ai.providers.usda import LiveUSDAProvider, SnapshotProvider


@pytest.fixture
def client():
    return USDAClient(NutritionSettings(api_key="unit-test-secret",retries=0))


def reply(monkeypatch,payload):
    body=payload if isinstance(payload,bytes) else json.dumps(payload).encode()
    monkeypatch.setattr(usda_client,"urlopen",lambda *args,**kwargs:io.BytesIO(body))


def test_snapshot_integrity_and_manifest_are_traceable(snapshot):
    assert len(snapshot.records)==10
    assert snapshot.get(168878).provenance.snapshot_sha256
    assert snapshot.get(173424).provenance.source_url.endswith("173424/nutrients")
    assert snapshot.get(2707713).provenance.data_type=="Survey (FNDDS)"
    assert "not the complete USDA catalog" in snapshot.search("rice").scope


def test_snapshot_rejects_modified_payload(tmp_path):
    (tmp_path/"foods.json").write_text("[]")
    (tmp_path/"manifest.json").write_text(json.dumps({"sha256":"incorrect","records":[]}))
    with pytest.raises(SnapshotError):
        SnapshotProvider(tmp_path)


def test_snapshot_missing_file_is_clear(tmp_path):
    with pytest.raises(SnapshotError):
        SnapshotProvider(tmp_path)


def test_snapshot_unknown_id_is_explicit(snapshot):
    with pytest.raises(FoodNotFoundError):
        snapshot.get(999999999)


def test_missing_key_makes_no_network_request(monkeypatch):
    monkeypatch.setattr(usda_client,"urlopen",lambda *a,**k:pytest.fail("network attempted without key"))
    with pytest.raises(MissingCredentialsError):
        USDAClient(NutritionSettings()).search("banana")


def test_settings_never_serialize_api_key():
    settings=NutritionSettings(api_key="unit-test-secret")
    assert "unit-test-secret" not in repr(settings)
    assert "unit-test-secret" not in settings.model_dump_json()


@pytest.mark.parametrize(("failure","expected"),[
    (HTTPError("url",401,"sensitive",{},None),USDAAuthenticationError),
    (HTTPError("url",403,"sensitive",{},None),USDAAuthenticationError),
    (HTTPError("url",404,"sensitive",{},None),FoodNotFoundError),
    (HTTPError("url",429,"sensitive",{},None),USDARateLimitError),
    (HTTPError("url",500,"sensitive",{},None),USDAResponseError),
    (HTTPError("url",400,"sensitive",{},None),USDAResponseError),
    (TimeoutError(),USDATimeoutError), (URLError(TimeoutError()),USDATimeoutError),
    (URLError(ConnectionRefusedError()),USDAConnectionError), (OSError(),USDAConnectionError),
])
def test_network_and_http_failures_are_safe(monkeypatch,client,failure,expected):
    def fail(*args,**kwargs): raise failure
    monkeypatch.setattr(usda_client,"urlopen",fail)
    with pytest.raises(expected) as captured:
        client.search("banana")
    assert "sensitive" not in str(captured.value)
    assert "unit-test-secret" not in str(captured.value)
    assert captured.value.__suppress_context__


def test_rate_limit_retry_honors_short_retry_after(monkeypatch):
    actions=iter([HTTPError("url",429,"rate",{"Retry-After":"0"},None),b'{"foods":[],"totalHits":0}'])
    sleeps=[]
    def open_request(*args,**kwargs):
        action=next(actions)
        if isinstance(action,Exception): raise action
        return io.BytesIO(action)
    monkeypatch.setattr(usda_client,"urlopen",open_request)
    client=USDAClient(NutritionSettings(api_key="test",retries=1),sleeper=sleeps.append)
    assert client.search("banana")["foods"]==[]
    assert sleeps==[0]


def test_long_retry_after_does_not_block_or_retry_early(monkeypatch):
    calls=[]
    def fail(*args,**kwargs):
        calls.append(1)
        raise HTTPError("url",429,"rate",{"Retry-After":"60"},None)
    monkeypatch.setattr(usda_client,"urlopen",fail)
    client=USDAClient(NutritionSettings(api_key="test",retries=2),sleeper=lambda _:pytest.fail("unexpected sleep"))
    with pytest.raises(USDARateLimitError): client.search("banana")
    assert len(calls)==1


def test_server_retries_are_bounded(monkeypatch):
    calls=[]
    def fail(*a,**k):
        calls.append(1)
        raise HTTPError("url",503,"offline",{},None)
    monkeypatch.setattr(usda_client,"urlopen",fail)
    client=USDAClient(NutritionSettings(api_key="test",retries=1),sleeper=lambda _:None)
    with pytest.raises(USDAResponseError): client.search("banana")
    assert len(calls)==2


@pytest.mark.parametrize("payload",[b"not json",b"\xff",b'{"value":NaN}'])
def test_unreadable_responses_are_rejected(monkeypatch,client,payload):
    reply(monkeypatch,payload)
    with pytest.raises(USDAResponseError): client.search("banana")


def test_response_size_is_bounded(monkeypatch,client):
    reply(monkeypatch,b"x"*(usda_client.MAX_BYTES+1))
    with pytest.raises(USDAResponseError,match="oversized"): client.search("banana")


def test_search_payload_uses_documented_datatype_array_and_is_cached(monkeypatch,client):
    calls=[]
    def open_request(request,timeout):
        calls.append(json.loads(request.data))
        return io.BytesIO(b'{"foods":[],"totalHits":0}')
    monkeypatch.setattr(usda_client,"urlopen",open_request)
    client.search("boiled egg")
    client.search("boiled egg")
    assert len(calls)==1
    assert calls[0]["dataType"]==["Foundation","SR Legacy","Survey (FNDDS)"]


def test_food_details_are_cached_with_retrieval_time(monkeypatch,client):
    calls=[]
    def open_request(*a,**k):
        calls.append(1)
        return io.BytesIO(b'{"fdcId":168878}')
    monkeypatch.setattr(usda_client,"urlopen",open_request)
    assert client.food(168878)==client.food(168878)
    assert len(calls)==1


@pytest.mark.parametrize("bad",[True,0,-1,"168878",168878.0])
def test_food_ids_must_be_positive_integers(client,bad):
    with pytest.raises(FoodNotFoundError): client.food(bad)


@pytest.mark.parametrize("payload",[{},[],{"foods":[],"totalHits":-1},{"foods":[],"totalHits":True},{"foods":"rice","totalHits":1},{"foods":[{}],"totalHits":1}])
def test_search_response_contract_is_validated(payload):
    class Fake:
        def search(self,query): return payload
    with pytest.raises(USDAResponseError): LiveUSDAProvider(Fake()).search("rice")


def test_live_provider_keeps_truncation_and_normalizes_details(raw_usda):
    class Fake:
        def search(self,q): return {"totalHits":99,"foods":[{"fdcId":168878,"description":"Rice, white, long-grain, regular, enriched, cooked","dataType":"SR Legacy"}]}
        def food(self,i): return raw_usda(i),"2026-10-31T00:00:00Z"
    provider=LiveUSDAProvider(Fake())
    assert not provider.search("rice").exhaustive
    record=provider.get(168878)
    assert record.provenance.provider=="usda_live" and record.basis_grams==100
