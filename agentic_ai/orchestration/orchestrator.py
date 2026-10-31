"""Explicit staged execution; no LLM-generated quantities or nutrition values."""
import json
import secrets
import time
from pydantic import BaseModel, ValidationError
from agentic_ai.agents.food_agent import FoodUnderstandingAgent
from agentic_ai.agents.nutrition_agent import NutritionAnalysisAgent
from agentic_ai.clients.ollama_client import OllamaClient
from agentic_ai.clients.usda_client import USDAClient
from agentic_ai.config import Settings
from agentic_ai.errors import FoodUnderstandingError
from agentic_ai.nutrition_errors import NutritionError, USDAResponseError
from agentic_ai.providers.usda import LiveUSDAProvider, SnapshotProvider
from agentic_ai.schemas.food import FoodUnderstandingResult
from agentic_ai.schemas.nutrition import NutritionIssue, NutritionItemResult, NutritionRecord, SearchResults
from agentic_ai.schemas.orchestration import (ClarificationEvidence, ReplyRequest, RetryRequest,
                                             SessionResponse, StartRequest)
from agentic_ai.orchestration.budget import Budget
from agentic_ai.orchestration.clarifications import apply_action, make_question, validate_action
from agentic_ai.orchestration.state import ItemCheckpoint, SessionState
from agentic_ai.orchestration.store import InMemorySessionStore
from agentic_ai.orchestration.tracing import emit, safe_code, safe_error
from agentic_ai.orchestration_config import OrchestrationSettings
from agentic_ai.orchestration_errors import BudgetExceeded, OrchestrationError
from agentic_ai.tools.nutrition_calculator import summarize


def unpredictable_id():
    return secrets.token_urlsafe(32)


class CheckpointProvider:
    """Cache only normalized, bounded data; never store USDA HTTP bodies or credentials."""
    def __init__(self, provider, item, budget):
        self.provider, self.item, self.budget = provider, item, budget

    def search(self, query):
        if self.item.search is None:
            self.budget.consume("tool_calls")
            result = self.provider().search(query)
            if not isinstance(result, SearchResults) or len(result.candidates) > 50:
                raise USDAResponseError("Invalid or excessive normalized search results.")
            self.item.search = result.model_copy(deep=True)
        return self.item.search.model_copy(deep=True)

    def get(self, fdc_id):
        if fdc_id not in self.item.records:
            self.budget.consume("tool_calls")
            record = self.provider().get(fdc_id)
            if (not isinstance(record, NutritionRecord) or record.provenance.fdc_id != fdc_id
                    or len(record.model_dump_json().encode()) > 131072
                    or len(record.portions) > 200):
                raise USDAResponseError("Invalid or excessive normalized food record.")
            if self.item.search is not None:
                offered = next((c for c in self.item.search.candidates if c.fdc_id == fdc_id), None)
                if offered is not None and (offered.description != record.provenance.description
                                             or offered.data_type != record.provenance.data_type):
                    raise USDAResponseError("USDA details conflict with the offered candidate.")
            # Retain only the current record; old candidate choices need no data cache.
            self.item.records = {fdc_id: record.model_copy(deep=True)}
        return self.item.records[fdc_id].model_copy(deep=True)


class AgentOrchestrator:
    """Use owner=authenticated_subject on every call. IDs alone confer no access.

    Optional factories are trusted dependency-injection seams for deterministic tests.
    Each factory receives an attempt observer and must install it in custom transports
    if it performs HTTP calls. Built-in factories always account for every attempt.
    """
    def __init__(self, settings=None, *, store=None, food_factory=None,
                 provider_factory=None, clock=time.time, id_factory=unpredictable_id):
        self.settings = settings or (store.settings if store else OrchestrationSettings.from_environment())
        if store is not None and store.settings != self.settings:
            raise OrchestrationError("inconsistent_store_configuration")
        self.store = store or InMemorySessionStore(self.settings, clock=clock)
        self.clock = self.store.clock
        self.new_id = id_factory
        self.food_factory = food_factory or self._food_factory
        self.provider_factory = provider_factory or self._provider_factory

    @staticmethod
    def _food_factory(observer):
        settings = Settings.from_environment()
        return FoodUnderstandingAgent(settings, OllamaClient(settings, attempt_observer=observer))

    @staticmethod
    def _provider_factory(mode, observer):
        return SnapshotProvider() if mode == "snapshot" else LiveUSDAProvider(
            USDAClient(attempt_observer=observer, cache=False))

    def _request(self, value, model, limit):
        try:
            raw = value.model_dump_json() if isinstance(value, BaseModel) else json.dumps(value, allow_nan=False)
            if len(raw.encode("utf-8")) > limit:
                raise OrchestrationError("request_size_limit")
            return model.model_validate_json(raw)
        except (ValueError, TypeError, OverflowError, RecursionError):
            raise OrchestrationError("invalid_request") from None

    @staticmethod
    def _owner(owner):
        if not isinstance(owner, str) or not owner or len(owner.encode("utf-8")) > 256:
            raise OrchestrationError("invalid_owner_context")

    def start(self, request, *, owner):
        self._owner(owner)
        request = self._request(request, StartRequest, self.settings.max_request_bytes)
        now = self.clock()
        response = SessionResponse(session_id=self.new_id(), revision=0, status="waiting_for_retry",
                                   created_at=now, expires_at=now + self.settings.ttl_seconds)
        state = SessionState(owner=owner, original_text=request.text, provider=request.provider,
                             response=response)
        self.store.create(state)  # Capacity is reserved before performing tools.
        try:
            with self.store.transaction(response.session_id, owner) as state:
                state.response.revision += 1
                self._execute(state, extract=True)
                result = state.response.model_copy(deep=True)
        except OrchestrationError as error:
            if error.code not in {"session_memory_limit", "store_memory_limit"}:
                raise
            return self.store.get(response.session_id, owner)
        return result

    def get(self, session_id, *, owner):
        self._owner(owner)
        return self.store.get(session_id, owner)

    def close(self, session_id, *, owner):
        self._owner(owner)
        self.store.close(session_id, owner)

    def _check_revision(self, state, request):
        if request.request_id in state.request_ids:
            raise OrchestrationError("duplicate_request")
        if request.expected_revision != state.response.revision:
            raise OrchestrationError("stale_revision")
        if state.response.status in {"completed", "failed", "limit_reached"}:
            raise OrchestrationError("session_not_actionable")

    def respond(self, session_id, reply, *, owner):
        self._owner(owner)
        reply = self._request(reply, ReplyRequest, self.settings.max_reply_bytes)
        with self.store.transaction(session_id, owner) as state:
            self._check_revision(state, reply)
            question = next((q for q in state.response.questions if q.question_id == reply.question_id), None)
            if question is None:
                raise OrchestrationError("stale_question")
            if question.item_id != reply.item_id:
                raise OrchestrationError("cross_item_response")
            item = next(i for i in state.items if i.item_id == reply.item_id)
            validate_action(item, question, reply.action)
            budget = Budget(state, self.settings, clock=self.clock)
            # Invalid requests above leave state, revision, budgets and tools untouched.
            try:
                budget.consume("turns")
                state.response.revision += 1
                state.request_ids.append(reply.request_id)
                if reply.action.kind == "refine_food":
                    try:
                        refined = self._extract(state, reply.action.description, budget)
                        if len(refined.foods) != 1:
                            raise OrchestrationError("refinement_requires_one_food")
                    except BudgetExceeded:
                        raise
                    except Exception as error:
                        # Model calls have happened: retain their budget cost but leave
                        # the old item, extraction and nutrients unchanged.
                        state.response.error = safe_error(getattr(error, "code", "unexpected_tool_error"))
                        emit(state, self.settings, "clarification", "error", item_id=item.item_id,
                             reason_code=state.response.error.code)
                        self._finish(state, preserve_status=True)
                        return state.response.model_copy(deep=True)
                    item.effective_food = refined.foods[0]
                    item.selection, item.search, item.records, item.quantity = None, None, {}, None
                else:
                    apply_action(item, reply.action)
                state.response.evidence.append(ClarificationEvidence(
                    item_id=item.item_id, revision=state.response.revision,
                    request_id=reply.request_id, action=reply.action))
                emit(state, self.settings, "clarification", "applied", item_id=item.item_id)
                self._execute(state, indices=[item.index])
            except BudgetExceeded as error:
                self._stop(state, error)
                self._finish(state, preserve_status=True)
            # Other exceptions roll back the detached draft atomically. In particular
            # a failed refinement never replaces the previous valid item checkpoint.
            result = state.response.model_copy(deep=True)
        return result

    def retry(self, session_id, request, *, owner):
        self._owner(owner)
        request = self._request(request, RetryRequest, self.settings.max_reply_bytes)
        with self.store.transaction(session_id, owner) as state:
            self._check_revision(state, request)
            if state.response.status != "waiting_for_retry":
                raise OrchestrationError("nothing_to_retry")
            failed = [i.index for i in state.items if i.result and i.result.status == "error"]
            if request.item_id is not None:
                matched = [i.index for i in state.items if i.item_id == request.item_id and i.index in failed]
                if not matched:
                    raise OrchestrationError("invalid_retry_item")
                failed = matched
            try:
                Budget(state, self.settings, clock=self.clock).consume("turns")
                state.response.revision += 1
                state.request_ids.append(request.request_id)
                self._execute(state, extract=state.response.extraction is None, indices=failed)
            except BudgetExceeded as error:
                self._stop(state, error)
                self._finish(state, preserve_status=True)
            result = state.response.model_copy(deep=True)
        return result

    def _extract(self, state, text, budget):
        budget.consume("steps")
        budget.consume("tool_calls")
        emit(state, self.settings, "extraction", "started")
        result = self.food_factory(budget.http_attempt).analyze(text)
        if not isinstance(result, FoodUnderstandingResult):
            raise OrchestrationError("invalid_model_response")
        # Revalidate a copy: trusted custom agents cannot return model_construct data.
        result = FoodUnderstandingResult.model_validate_json(result.model_dump_json())
        emit(state, self.settings, "extraction", "completed")
        return result

    def _execute(self, state, *, extract=False, indices=None):
        budget = Budget(state, self.settings, clock=self.clock)
        state.response.error = None
        try:
            if extract:
                state.response.extraction = self._extract(state, state.original_text, budget)
                state.items = [ItemCheckpoint(item_id=self.new_id(), index=index, effective_food=food,
                    result=NutritionItemResult(item_index=index, food=food, status="needs_clarification"))
                    for index, food in enumerate(state.response.extraction.foods)]
                indices = list(range(len(state.items)))
            indices = set(indices or [])
            provider = None
            def get_provider():
                nonlocal provider
                if provider is None:
                    provider = self.provider_factory(state.provider, budget.http_attempt)
                return provider
            for item in state.items:
                if item.index not in indices or item.left_unresolved:
                    emit(state, self.settings, "nutrition", "reused", item_id=item.item_id)
                    continue
                budget.consume("steps")
                emit(state, self.settings, "nutrition", "started", item_id=item.item_id)
                try:
                    agent = NutritionAnalysisAgent(CheckpointProvider(get_provider, item, budget))
                    item.result = agent.analyze_item(item.index, item.effective_food, item.selection,
                                                    exact_quantity=item.quantity)
                    # Never copy arbitrary dependency error text into public session output.
                    for issue in item.result.issues:
                        if item.result.status == "error":
                            issue.code = safe_code(issue.code)
                            issue.message = safe_error(issue.code).message
                except BudgetExceeded:
                    raise
                except Exception as error:
                    code = safe_code(getattr(error, "code", "unexpected_tool_error"))
                    item.result = NutritionItemResult(item_index=item.index, food=item.effective_food,
                        status="error", issues=[NutritionIssue(code=code, message=safe_error(code).message)])
                outcome = "error" if item.result.status == "error" else "needs_clarification" if item.result.status == "needs_clarification" else "completed"
                metadata = {"item_id": item.item_id}
                if item.result.issues:
                    metadata["reason_code"] = safe_code(item.result.issues[0].code)
                if item.result.record:
                    metadata.update(fdc_id=item.result.record.provenance.fdc_id,
                                    basis_grams=item.result.record.basis_grams,
                                    scale_factor=item.result.scale_factor)
                if item.result.portion:
                    metadata["requested_grams"] = item.result.portion.requested_grams
                emit(state, self.settings, "nutrition", outcome, **metadata)
        except BudgetExceeded as error:
            self._stop(state, error)
            self._finish(state, preserve_status=True)
            return
        except Exception as error:
            code = safe_code(getattr(error, "code", "unexpected_tool_error"))
            state.response.error = safe_error(code)
            state.response.status = "failed" if code == "invalid_input" else "waiting_for_retry"
            try:
                emit(state, self.settings, "extraction", "error", reason_code=code)
            except BudgetExceeded as limit:
                self._stop(state, limit)
            self._finish(state, preserve_status=True)
            return
        self._finish(state)

    def _stop(self, state, error):
        state.response.status = "limit_reached"
        state.response.error = safe_error(error.code)
        emit(state, self.settings, "session", "limit_reached", reason_code=safe_code(error.code))

    def _finish(self, state, *, preserve_status=False):
        state.response.nutrition = summarize([i.result for i in state.items]) if state.response.extraction else None
        state.response.questions = [make_question(i, self.new_id) for i in state.items
                                    if not i.left_unresolved and i.result.status == "needs_clarification"]
        if not preserve_status:
            if any(i.result.status == "error" and not i.left_unresolved for i in state.items):
                state.response.status = "waiting_for_retry"
            elif state.response.questions:
                state.response.status = "awaiting_clarification"
            else:
                state.response.status = "completed"
