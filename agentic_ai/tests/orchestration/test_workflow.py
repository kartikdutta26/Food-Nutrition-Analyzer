from decimal import Decimal, localcontext
import pytest
from agentic_ai.agents.nutrition_agent import NutritionAnalysisAgent
from agentic_ai.orchestration_errors import OrchestrationError
from agentic_ai.schemas.orchestration import SessionResponse
from agentic_ai.tools.nutrition_calculator import calculate, summarize


def test_indian_multi_turn_reuses_unrelated_items(make_service, raw, send, monkeypatch):
    service, state, provider, calls = make_service([
        raw("roti", "2 rotis", "2", "piece"),
        raw("white rice", "cooked white rice", preparation="cooked"),
        raw("egg", "100 g boiled eggs", "100", "g", "boiled")])
    assert state.status == "awaiting_clarification"
    original = state.extraction.model_dump_json()
    egg_before = state.nutrition.items[2].model_dump_json()
    processed = []
    analyze_item = NutritionAnalysisAgent.analyze_item
    def track(self, index, *args, **kwargs):
        processed.append(index)
        return analyze_item(self, index, *args, **kwargs)
    monkeypatch.setattr(NutritionAnalysisAgent, "analyze_item", track)
    state = send(service, state, 1, {"kind": "quantity", "quantity": "0.5", "unit": "cup"})
    assert processed == [1]
    assert state.nutrition.items[1].portion.requested_grams == Decimal("79")
    state = send(service, state, 0, {"kind": "select_portion", "portion_id": "299422"})
    assert processed == [1, 0]
    assert state.nutrition.items[0].portion.requested_grams == Decimal("54")
    assert state.nutrition.items[2].model_dump_json() == egg_before
    assert state.extraction.model_dump_json() == original
    assert len(calls) == 1
    assert provider.gets == [2707713, 168878, 173424]
    assert len(provider.searches) == 3
    assert state.status == "completed" and state.nutrition.status == "complete"
    assert state.nutrition.coverage["calories"].complete
    assert {e.event for e in state.trace} >= {"reused", "applied", "completed"}
    assert len(state.evidence) == 2


def test_ambiguous_apple_then_missing_banana_size(make_service, raw, send):
    service, state, provider, _ = make_service([
        raw("apple", "100 g apples", "100", "g"), raw("banana", "1 banana", "1", "piece")])
    assert {c.fdc_id for c in state.questions[0].candidates} == {171688, 171689}
    state = send(service, state, 0, {"kind": "select_food", "fdc_id": 171688})
    state = send(service, state, 1, {"kind": "select_portion", "portion_id": "93515"})
    assert state.status == "completed"
    assert state.nutrition.items[1].portion.requested_grams == Decimal("118")
    assert provider.gets == [173944, 171688]


def test_measured_grams_do_not_invent_density(make_service, raw, send):
    service, state, _, _ = make_service([raw("whole milk", "250 ml whole milk", "250", "ml")])
    state = send(service, state, 0, {"kind": "select_food", "fdc_id": 171265})
    assert state.nutrition.items[0].portion is None
    assert state.questions[0].reason in {"ambiguous_portion", "unsupported_portion"}
    state = send(service, state, 0, {"kind": "measured_grams", "grams": "257.25"})
    assert state.status == "completed"
    assert state.nutrition.items[0].portion.method == "user_measured"
    assert state.nutrition.items[0].portion.requested_grams == Decimal("257.25")
    assert "User-supplied" in state.nutrition.items[0].portion.evidence


def test_leave_unknown_keeps_coverage_and_partial_totals(make_service, raw, send):
    service, state, _, _ = make_service([
        raw("banana", "100 g banana", "100", "g"), raw("paneer curry", "one bowl paneer curry", "one", "bowl")])
    assert not state.questions[0].candidates
    state = send(service, state, 1, {"kind": "leave_unresolved"})
    assert state.status == "completed" and state.nutrition.status == "partial"
    assert state.nutrition.total_items == 2
    assert state.nutrition.complete_totals.calories is None
    assert state.nutrition.known_subtotals.calories == Decimal("89")
    assert state.nutrition.coverage["calories"].known_items == 1
    assert state.nutrition.coverage["calories"].total_items == 2
    assert not state.questions
    assert state.nutrition.items[1].record is None


def test_missing_nutrient_remains_unknown_not_zero(make_service, raw):
    from conftest import RecordingProvider
    provider = RecordingProvider()
    provider.records[173944].nutrients.fiber = None  # Synthetic fault case, never saved to snapshot.
    _, state, _, _ = make_service([raw("banana", "100 g banana", "100", "g")], provider=provider)
    assert state.status == "completed"
    assert state.nutrition.status == "partial"
    assert state.nutrition.complete_totals.fiber is None
    assert state.nutrition.known_subtotals.fiber is None
    assert state.nutrition.coverage["fiber"].known_items == 0


def test_repeated_foods_have_distinct_item_identity(make_service, raw, send):
    service, state, _, _ = make_service([raw("banana", "banana"), raw("banana", "banana")])
    assert state.questions[0].item_id != state.questions[1].item_id
    state = send(service, state, 0, {"kind": "measured_grams", "grams": "80"})
    assert state.nutrition.items[0].portion.requested_grams == Decimal("80")
    assert state.nutrition.items[1].portion is None


def test_preparation_is_explicit_user_evidence(make_service, raw, send):
    service, state, _, calls = make_service([raw("egg", "100 g eggs", "100", "g")])
    assert {c.fdc_id for c in state.questions[0].candidates} == {173424, 173423}
    state = send(service, state, 0, {"kind": "preparation", "preparation": "boiled"})
    assert state.status == "completed"
    assert state.extraction.foods[0].preparation is None
    assert state.extraction.foods[0].source_text == "100 g eggs"
    assert state.nutrition.items[0].food.preparation == "boiled"
    assert state.evidence[0].action.preparation == "boiled"
    assert len(calls) == 1


def test_refine_one_item_uses_model_only_for_reply(make_service, raw, send):
    from agentic_ai.orchestration_demo import ScriptedChat
    from agentic_ai.agents.food_agent import FoodUnderstandingAgent
    from agentic_ai.config import Settings
    service, state, provider, calls = make_service([
        raw("paneer curry", "paneer curry"), raw("banana", "100 g banana", "100", "g")])
    refined_calls = []
    class Refiner:
        def analyze(self, text):
            refined_calls.append(text)
            return FoodUnderstandingAgent(Settings(), ScriptedChat([
                raw("egg", "100 g boiled egg", "100", "g", "boiled")])).analyze(text)
    service.food_factory = lambda observer: Refiner()
    banana = state.nutrition.items[1].model_dump_json()
    state = send(service, state, 0, {"kind": "refine_food", "description": "100 g boiled egg"})
    assert state.status == "completed"
    assert refined_calls == ["100 g boiled egg"]
    assert len(calls) == 1
    assert state.nutrition.items[1].model_dump_json() == banana
    assert state.extraction.foods[0].name == "paneer curry"
    assert state.nutrition.items[0].food.name == "egg"


def test_unrounded_checkpoints_survive_unrelated_clarifications(make_service, raw, send):
    service, state, _, _ = make_service([
        raw("banana", "0.123456789 g banana", "0.123456789", "g"),
        raw("roti", "2 rotis", "2", "piece"), raw("egg", "boiled egg", preparation="boiled")])
    with service.store.transaction(state.session_id, "alice") as checkpoint:
        exact = checkpoint.items[0].result.nutrition.calories
    assert exact == Decimal("0.10987654221")
    state = send(service, state, 1, {"kind": "select_portion", "portion_id": "299422"})
    state = send(service, state, 2, {"kind": "measured_grams", "grams": "50.123456789"})
    with service.store.transaction(state.session_id, "alice") as checkpoint:
        assert checkpoint.items[0].result.nutrition.calories == exact
        before = checkpoint.items[0].result.model_dump_json()
        a = summarize([i.result for i in checkpoint.items])
        b = summarize([i.result for i in checkpoint.items])
        assert a == b
        assert checkpoint.items[0].result.model_dump_json() == before
        with localcontext() as ctx:
            ctx.prec = 40
            expected = sum((i.result.nutrition.calories for i in checkpoint.items), Decimal(0)).quantize(Decimal("0.0001"))
        assert state.nutrition.complete_totals.calories == expected


def test_reply_decimal_does_not_round_through_float(make_service, raw, send):
    service, state, _, _ = make_service([raw("banana", "banana")])
    quantity = "0.123456789123"
    state = send(service, state, 0, {"kind": "quantity", "quantity": quantity, "unit": "g"})
    with service.store.transaction(state.session_id, "alice") as checkpoint:
        assert checkpoint.items[0].result.portion.requested_grams == Decimal(quantity)
        assert checkpoint.items[0].result.nutrition.calories == Decimal(quantity) * Decimal("0.89")


def test_roundtrip_and_returned_snapshots_are_detached(make_service, raw):
    service, state, _, _ = make_service([raw("banana", "banana")])
    assert SessionResponse.model_validate_json(state.model_dump_json()) == state
    state.questions.clear()
    state.trace.clear()
    assert service.get(state.session_id, owner="alice").questions
    assert service.get(state.session_id, owner="alice").trace


def test_no_food_workflow_completes_without_provider(make_service):
    _, state, provider, _ = make_service([])
    assert state.status == "completed"
    assert state.nutrition.status == "no_food"
    assert state.nutrition.complete_totals.calories is None
    assert provider.gets == [] and provider.searches == []


def test_snapshot_source_and_calculation_attribution(make_service, raw):
    _, state, _, _ = make_service([raw("white rice", "150 g cooked white rice", "150", "g", "cooked")])
    item = state.nutrition.items[0]
    assert item.record.provenance.fdc_id == 168878
    assert item.record.provenance.provider == "usda_snapshot"
    assert item.record.provenance.snapshot_sha256 == "c3fde77650f6b10f4fa2f568a800464b34808cacb7bef239e40ea38a7c768937"
    assert str(item.record.provenance.fdc_id) in item.record.provenance.source_url
    assert item.record.basis_grams == Decimal("100")
    assert item.scale_factor == Decimal("1.5")
    assert item.nutrition.calories == Decimal("195")
    event = state.trace[-1]
    assert event.fdc_id == 168878 and event.scale_factor == Decimal("1.5")
    assert event.basis_grams == Decimal("100") and event.requested_grams == Decimal("150")
