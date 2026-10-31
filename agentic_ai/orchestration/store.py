"""Bounded serialized storage with atomic copy-on-write transactions.

The global RLock serializes operations, including tools. This intentionally simple
single-process implementation favors correctness; a production adapter should use
per-session transactions, authenticated ownership and shared durable storage.
"""
from contextlib import contextmanager
import hmac
import threading
import time
from typing import ContextManager, Protocol
from agentic_ai.orchestration.state import SessionState
from agentic_ai.orchestration_config import OrchestrationSettings
from agentic_ai.orchestration_errors import OrchestrationError
from agentic_ai.orchestration.tracing import emit, safe_error


class SessionStore(Protocol):
    """Durable adapters must enforce ownership, TTL, quotas and atomic revision checks."""
    settings: OrchestrationSettings
    clock: object

    def create(self, state: SessionState) -> None: ...
    def transaction(self, sid: str, owner: str) -> ContextManager[SessionState]: ...
    def get(self, sid: str, owner: str): ...
    def close(self, sid: str, owner: str) -> None: ...


class InMemorySessionStore:
    def __init__(self, settings=None, *, clock=time.time):
        self.settings = settings or OrchestrationSettings.from_environment()
        self.clock = clock
        self._entries = {}
        self._lock = threading.RLock()

    def _purge(self):
        now = self.clock()
        for key in list(self._entries):
            if self._entries[key][0] <= now:
                del self._entries[key]

    def _encode(self, state):
        raw = state.model_dump_json().encode("utf-8")
        # Reserve room for a terminal error, one request ID and final usage.
        reserve = 0 if state.response.status in {"completed", "failed", "limit_reached"} else 1024
        if len(raw) + reserve > self.settings.max_session_bytes:
            raise OrchestrationError("session_memory_limit")
        return raw, len(raw) + reserve

    def _put(self, state, *, create=False):
        raw, charge = self._encode(state)
        sid = state.response.session_id
        if create and sid in self._entries:
            raise OrchestrationError("session_id_collision")
        old_size = self._entries[sid][2] if sid in self._entries else 0
        if sum(value[2] for value in self._entries.values()) - old_size + charge > self.settings.max_store_bytes:
            raise OrchestrationError("store_memory_limit")
        self._entries[sid] = (state.response.expires_at, raw, charge)

    def _load(self, sid, owner):
        self._purge()
        if not isinstance(sid, str) or len(sid) > 100:
            raise OrchestrationError("session_not_found")
        entry = self._entries.get(sid)
        if not entry:
            raise OrchestrationError("session_not_found")
        state = SessionState.model_validate_json(entry[1])
        if not isinstance(owner, str) or not hmac.compare_digest(state.owner.encode(), owner.encode()):
            raise OrchestrationError("session_not_found")
        return state

    def create(self, state):
        with self._lock:
            self._purge()
            if len(self._entries) >= self.settings.max_sessions:
                raise OrchestrationError("active_session_limit")
            self._put(state, create=True)

    @contextmanager
    def transaction(self, sid, owner):
        with self._lock:
            state = self._load(sid, owner)
            original = state.model_copy(deep=True)
            yield state
            # TTL is fixed; a slow tool cannot resurrect an expired session.
            if self.clock() >= state.response.expires_at:
                self._entries.pop(sid, None)
                raise OrchestrationError("session_not_found")
            try:
                self._put(state)
            except OrchestrationError as error:
                if error.code not in {"session_memory_limit", "store_memory_limit"}:
                    raise
                # Tool calls may already have occurred. Preserve old nutrition while
                # retaining spent budgets and making the session terminal, so repeated
                # oversized replies cannot obtain unbounded retries.
                original.response.usage = state.response.usage
                original.response.revision = state.response.revision
                original.request_ids = state.request_ids
                original.response.status = "limit_reached"
                original.response.error = safe_error(error.code)
                for item in original.items:
                    item.records, item.search = {}, None
                original.response.trace = original.response.trace[:self.settings.max_trace_events - 1]
                emit(original, self.settings, "session", "limit_reached", reason_code=error.code)
                try:
                    self._put(original)
                except OrchestrationError:
                    # If metadata itself cannot fit, free old trace data before
                    # discarding any nutrition checkpoints. Error remains explicit.
                    original.response.trace = []
                    emit(original, self.settings, "session", "limit_reached", reason_code=error.code)
                    self._put(original)
                raise OrchestrationError(error.code) from None

    def get(self, sid, owner):
        with self._lock:
            return self._load(sid, owner).response

    def close(self, sid, owner):
        with self._lock:
            self._load(sid, owner)
            del self._entries[sid]
