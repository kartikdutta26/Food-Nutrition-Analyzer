from decimal import Decimal
import pytest
from agentic_ai.orchestration_demo import raw_food
from agentic_ai.recommendation_errors import RecommendationError
from agentic_ai.agents.recommendation_agent import NutritionRecommendationAgent


def test_completed_session_preserves_identity_and_revision(agent,session_factory):
    service,state=session_factory()
    before=state.model_dump_json()
    output=agent.recommend_session(state,expected_revision=state.revision)
    assert output.status=="ready"
    assert output.input_ref.session_id==state.session_id
    assert output.input_ref.revision==state.revision
    assert output.input_ref.session_status=="completed"
    assert state.model_dump_json()==before
    assert service.get(state.session_id,owner="owner").model_dump_json()==before

@pytest.mark.parametrize("revision",[0,2,True,"1",-1])
def test_stale_or_invalid_expected_revision(agent,session_factory,revision):
    _,state=session_factory()
    with pytest.raises(RecommendationError) as error:
        agent.recommend_session(state,expected_revision=revision)
    assert error.value.code in {"stale_revision","invalid_input"}


def test_current_clarification_ids_and_allowed_actions_preserved(agent,session_factory):
    _,state=session_factory([raw_food("banana","banana")])
    output=agent.recommend_session(state)
    assert output.status=="unavailable"
    steps=[m for m in output.next_steps if m.code=="clarify"]
    assert len(steps)==len(state.questions)==1
    assert steps[0].question_id==state.questions[0].question_id
    assert steps[0].item_id==state.questions[0].item_id
    assert steps[0].allowed_actions==tuple(state.questions[0].allowed_actions)


def test_exact_decimal_quantity_clarification(agent,session_factory,reply):
    service,state=session_factory([raw_food("banana","banana")])
    state=reply(service,state,0,{"kind":"quantity","quantity":"0.123456789123","unit":"g"})
    output=agent.recommend_session(state,expected_revision=state.revision)
    assert output.status=="ready"
    assert output.session_evidence==tuple(state.evidence)
    assert output.citations[0].portion.requested_grams==Decimal("0.123456789123")
    assert output.input_ref.revision==2
    assert not output.next_steps


def test_measured_mass_is_user_attribution_not_usda_measurement(agent,session_factory,reply):
    service,state=session_factory([raw_food("banana","banana")])
    state=reply(service,state,0,{"kind":"measured_grams","grams":"80.123456789"})
    output=agent.recommend_session(state)
    assert output.citations[0].portion.method=="user_measured"
    assert any(m.code=="declared_measurement" for m in output.limitations)
    assert output.session_evidence[0].request_id==state.evidence[0].request_id
    raw=state.model_dump(mode="json");raw["evidence"]=[]
    with pytest.raises(RecommendationError):agent.recommend_session(raw)


def test_completed_partial_keeps_original_extraction_and_unknowns(agent,session_factory,reply):
    service,state=session_factory([raw_food("banana","100 g banana","100","g"),raw_food("paneer curry","one bowl paneer curry","one","bowl")])
    state=reply(service,state,1,{"kind":"leave_unresolved"})
    before=state.model_dump_json()
    output=agent.recommend_session(state)
    assert output.status=="limited"
    assert output.complete_totals.calories is None
    assert output.known_subtotals.calories==89
    assert output.session_evidence==tuple(state.evidence)
    assert not any(m.code=="clarify" for m in output.next_steps)
    assert state.model_dump_json()==before


def test_expired_session_retains_evidence_without_current_guidance(session_factory):
    _,state=session_factory()
    output=NutritionRecommendationAgent(clock=lambda:state.expires_at).recommend_session(state)
    assert output.status=="unavailable" and output.input_ref.expired
    assert output.complete_totals==state.nutrition.complete_totals
    assert output.citations
    assert not output.observations and not output.suggestions
    assert any(m.code=="expired" for m in output.next_steps)

@pytest.mark.parametrize("status",["failed","limit_reached","waiting_for_retry"])
def test_failure_and_retry_states_are_not_ready(agent,session_factory,status):
    _,state=session_factory()
    raw=state.model_dump(mode="json");raw["status"]=status
    output=agent.recommend_session(raw)
    assert output.status=="limited"
    assert any(m.code==("retry" if status=="waiting_for_retry" else "terminal") for m in output.next_steps)


def test_extraction_failure_is_unavailable(agent,session_factory):
    from agentic_ai.errors import OllamaConnectionError
    _,state=session_factory(failure=OllamaConnectionError("cannot reach local model"))
    output=agent.recommend_session(state)
    assert output.status=="unavailable" and not output.facts and not output.citations

@pytest.mark.parametrize("mutation",["bad_index","duplicate_question","unknown_action","bad_revision","bad_expiry","duplicate_request"])
def test_session_evidence_inconsistency_rejected(agent,session_factory,reply,mutation):
    service,state=session_factory([raw_food("banana","banana"),raw_food("banana","banana")])
    state=reply(service,state,0,{"kind":"measured_grams","grams":"80"})
    raw=state.model_dump(mode="json")
    if mutation=="bad_index":raw["questions"][0]["item_index"]=99
    elif mutation=="duplicate_question":raw["questions"]*=2
    elif mutation=="unknown_action":raw["questions"][0]["allowed_actions"]=["prescribe"]
    elif mutation=="bad_revision":raw["evidence"][0]["revision"]=state.revision+1
    elif mutation=="bad_expiry":raw["expires_at"]=raw["created_at"]
    else:raw["evidence"]*=2
    with pytest.raises(RecommendationError):agent.recommend_session(raw)
