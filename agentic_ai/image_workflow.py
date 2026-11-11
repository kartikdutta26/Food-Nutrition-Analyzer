"""Process-local image -> explicit confirmation -> existing M3 -> existing M4.

No caption-to-M1 path exists. No image bytes, paths or recommendation cache are
stored. Dependency injection is trusted Python code, not an authentication API.
"""
from dataclasses import dataclass, field
from functools import wraps
import hashlib
import hmac
import secrets
import threading

from agentic_ai.adapters.vision_handoff import prepare_confirmation, to_m3_start_request, validate_recognition_result
from agentic_ai.agents.recommendation_agent import NutritionRecommendationAgent
from agentic_ai.image_workflow_config import ImageWorkflowSettings
from agentic_ai.image_workflow_errors import ImageWorkflowError
from agentic_ai.orchestration_errors import OrchestrationError
from agentic_ai.orchestration.tracing import SAFE_CODES
from agentic_ai.recommendation_errors import RecommendationError
from agentic_ai.schemas.image_workflow import ImageWorkflowSnapshot
from agentic_ai.schemas.orchestration import SessionResponse
from agentic_ai.schemas.recommendation import RecommendationResult
from agentic_ai.schemas.vision import ConfirmedImageMeal, ImageFoodRecognitionResult
from agentic_ai.tools.image_input import ImageInputError
from agentic_ai.vision_errors import VisionContractError
from agentic_ai.vision_runtime_errors import VisionRuntimeError


_SESSION_CODES = SAFE_CODES | {
    "session_not_found", "invalid_owner_context", "invalid_request", "request_size_limit",
    "active_session_limit", "session_id_collision", "duplicate_request", "stale_revision",
    "session_not_actionable", "stale_question", "cross_item_response", "action_not_allowed",
    "invalid_food_selection", "invalid_portion_selection", "invalid_preparation",
    "nothing_to_retry", "invalid_retry_item",
}


def _boundary(operation):
    @wraps(operation)
    def wrapped(*args, **kwargs):
        try:
            return operation(*args, **kwargs)
        except ImageWorkflowError:
            raise
        except (VisionContractError, VisionRuntimeError, ImageInputError, RecommendationError) as error:
            raise type(error)(error.code) from None
        except OrchestrationError as error:
            if isinstance(error.code, str) and error.code in _SESSION_CODES:
                raise OrchestrationError(error.code) from None
            raise ImageWorkflowError("operation_failed") from None
        except Exception:
            raise ImageWorkflowError("operation_failed") from None
    return wrapped


@dataclass
class _Entry:
    workflow_id: str
    owner_digest: str = field(repr=False)
    expires_at: float
    recognition: bytes = field(repr=False)
    handoff: bytes | None = field(default=None, repr=False)
    session_id: str | None = None
    phase: str = "awaiting_confirmation"

    @property
    def charge(self):
        return len(self.recognition) + len(self.handoff or b"")


class ImageNutritionWorkflow:
    """Use a trusted owner on EVERY operation; local owner strings are not login.

    One RLock serializes operations (including dependencies), like the existing
    standalone M3 store. Production multi-process storage is outside this module.
    Orchestrator and vision agent are explicit to avoid silently enabling models.
    """
    def __init__(self, *, vision_agent, orchestrator, recommendation_agent=None, settings=None):
        try:
            self.settings = ImageWorkflowSettings.model_validate(settings if settings is not None else ImageWorkflowSettings())
            self.vision_agent = vision_agent
            self.orchestrator = orchestrator
            self.clock = orchestrator.clock
            self.recommendation_agent = (recommendation_agent if recommendation_agent is not None
                                         else NutritionRecommendationAgent(clock=self.clock))
            self._entries = {}
            self._lock = threading.RLock()
        except Exception:
            raise ImageWorkflowError("invalid_configuration") from None

    @staticmethod
    def _owner(owner):
        try:
            if not isinstance(owner, str) or not 0 < len(owner.encode("utf-8")) <= 256:
                raise ValueError()
            return hashlib.sha256(owner.encode("utf-8")).hexdigest()
        except (ValueError, UnicodeError):
            raise ImageWorkflowError("invalid_owner") from None

    def _purge(self):
        for key in list(self._entries):
            if self.clock() >= self._entries[key].expires_at:
                del self._entries[key]

    def _entry(self, workflow_id, owner):
        digest = self._owner(owner)
        self._purge()
        entry = self._entries.get(workflow_id) if isinstance(workflow_id, str) and len(workflow_id) <= 100 else None
        if entry is None or not hmac.compare_digest(digest, entry.owner_digest):
            raise ImageWorkflowError("workflow_not_found")
        return entry

    def _capacity(self, entry, *, replacing=False):
        old = self._entries[entry.workflow_id].charge if replacing else 0
        if entry.charge > self.settings.max_metadata_bytes:
            raise ImageWorkflowError("metadata_limit")
        if sum(value.charge for value in self._entries.values()) - old + entry.charge > self.settings.max_store_bytes:
            raise ImageWorkflowError("metadata_limit")

    def _session(self, entry, owner):
        if entry.phase != "session_started" or entry.session_id is None:
            raise ImageWorkflowError("confirmation_required")
        result = self.orchestrator.get(entry.session_id, owner=owner)
        if not isinstance(result, SessionResponse) or result.session_id != entry.session_id:
            raise ImageWorkflowError("operation_failed")
        return SessionResponse.model_validate_json(result.model_dump_json())

    def _view(self, entry, owner, *, session=None, recommendations=None):
        if entry.phase == "session_started" and session is None:
            session = self._session(entry, owner)
        result = ImageWorkflowSnapshot(workflow_id=entry.workflow_id, phase=entry.phase, expires_at=entry.expires_at,
                    recognition=ImageFoodRecognitionResult.model_validate_json(entry.recognition),
                    handoff=ConfirmedImageMeal.model_validate_json(entry.handoff) if entry.handoff else None,
                    session=session, recommendations=recommendations)
        raw = result.model_dump_json()
        if len(raw.encode("utf-8")) > self.settings.max_output_bytes:
            raise ImageWorkflowError("output_limit")
        if self.clock() >= entry.expires_at:
            self._entries.pop(entry.workflow_id, None)
            raise ImageWorkflowError("workflow_not_found")
        # Nested M3 objects are mutable; return independent copies, never store them.
        return ImageWorkflowSnapshot.model_validate_json(raw)

    @_boundary
    def begin(self, path, *, owner):
        digest = self._owner(owner)
        with self._lock:
            self._purge()
            if len(self._entries) >= self.settings.max_workflows:
                raise ImageWorkflowError("workflow_limit")
            recognition = validate_recognition_result(self.vision_agent.analyze(path))
            workflow_id = secrets.token_urlsafe(32)
            if workflow_id in self._entries:
                raise ImageWorkflowError("workflow_limit")
            entry = _Entry(workflow_id, digest, self.clock()+self.settings.ttl_seconds,
                           recognition.model_dump_json().encode("utf-8"))
            self._capacity(entry)
            result = self._view(entry, owner)
            self._entries[workflow_id] = entry
            return result

    @_boundary
    def get(self, workflow_id, *, owner):
        with self._lock:
            return self._view(self._entry(workflow_id, owner), owner)

    @_boundary
    def confirm(self, workflow_id, confirmation, *, owner):
        with self._lock:
            entry = self._entry(workflow_id, owner)
            if entry.phase != "awaiting_confirmation":
                raise ImageWorkflowError("confirmation_consumed")
            recognition = ImageFoodRecognitionResult.model_validate_json(entry.recognition)
            handoff = prepare_confirmation(recognition, confirmation)
            request = to_m3_start_request(handoff, provider="snapshot")
            raw = handoff.model_dump_json().encode("utf-8")
            draft = _Entry(entry.workflow_id, entry.owner_digest, entry.expires_at, entry.recognition, raw)
            self._capacity(draft, replacing=True)
            # Consume BEFORE tools: even an ambiguous downstream failure must not
            # create a second M3 session by replaying this confirmation.
            entry.handoff, entry.phase = raw, "start_failed"
            result = self.orchestrator.start(request, owner=owner)
            if not isinstance(result, SessionResponse):
                raise ImageWorkflowError("operation_failed")
            entry.session_id, entry.phase = result.session_id, "session_started"
            entry.expires_at = min(entry.expires_at, result.expires_at)
            self._entry(workflow_id, owner)  # Slow tools cannot resurrect expiry.
            return self._view(entry, owner)

    @_boundary
    def respond(self, workflow_id, reply, *, owner):
        with self._lock:
            entry = self._entry(workflow_id, owner)
            self._session(entry, owner)
            self.orchestrator.respond(entry.session_id, reply, owner=owner)
            self._entry(workflow_id, owner)
            return self._view(entry, owner)

    @_boundary
    def retry(self, workflow_id, request, *, owner):
        with self._lock:
            entry = self._entry(workflow_id, owner)
            self._session(entry, owner)
            self.orchestrator.retry(entry.session_id, request, owner=owner)
            self._entry(workflow_id, owner)
            return self._view(entry, owner)

    @_boundary
    def recommend(self, workflow_id, *, expected_revision, owner, context=None):
        with self._lock:
            entry = self._entry(workflow_id, owner)
            session = self._session(entry, owner)
            if type(expected_revision) is not int or expected_revision < 0:
                raise ImageWorkflowError("invalid_revision")
            if expected_revision != session.revision:
                raise ImageWorkflowError("stale_revision")
            before = session.model_dump_json()
            recommendation = self.recommendation_agent.recommend_session(session, context=context,
                                                                         expected_revision=expected_revision)
            if session.model_dump_json() != before:
                raise ImageWorkflowError("dependency_mutation")
            self._entry(workflow_id, owner)
            current = self._session(entry, owner)
            if current.model_dump_json() != before:
                raise ImageWorkflowError("stale_revision")
            recommendation = RecommendationResult.model_validate_json(recommendation.model_dump_json())
            if (recommendation.input_ref.session_id != current.session_id
                    or recommendation.input_ref.revision != current.revision):
                raise ImageWorkflowError("stale_revision")
            return self._view(entry, owner, session=current, recommendations=recommendation)

    @_boundary
    def close(self, workflow_id, *, owner):
        with self._lock:
            entry = self._entry(workflow_id, owner)
            if entry.session_id is not None:
                self.orchestrator.close(entry.session_id, owner=owner)
            del self._entries[workflow_id]
