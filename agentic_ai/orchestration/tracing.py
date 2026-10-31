"""Allowlisted metadata only: never exception strings, prompts or model reasoning."""
from agentic_ai.schemas.orchestration import SafeError, TraceEvent
from agentic_ai.orchestration_errors import BudgetExceeded

# Only locally defined codes are allowed; dependency messages are never copied.
SAFE_CODES = frozenset({
    "invalid_input", "configuration_error", "ollama_unavailable", "ollama_timeout",
    "model_not_found", "invalid_model_response", "ollama_service_error",
    "invalid_nutrition_input", "usda_credentials_missing", "usda_authentication_failed",
    "usda_rate_limited", "usda_timeout", "usda_unavailable", "invalid_usda_response",
    "food_not_found", "invalid_snapshot", "ambiguous_food", "search_incomplete",
    "preparation_required", "inconsistent_source_record", "incompatible_food_selection",
    "missing_quantity", "missing_unit", "invalid_quantity", "unsupported_portion",
    "ambiguous_portion", "incompatible_portion_selection", "missing_nutrients",
    "source_data_notes", "unexpected_tool_error", "steps_limit", "turns_limit",
    "tool_calls_limit", "http_attempts_limit", "trace_limit", "refinement_requires_one_food",
    "session_memory_limit", "store_memory_limit", "session_ttl_limit",
})


def safe_code(code):
    return code if code in SAFE_CODES else "unexpected_tool_error"


def safe_error(code):
    code = safe_code(code)
    return SafeError(code=code, message=code.replace("_", " ").capitalize() + ". Review configuration or retry the failed stage.")


def emit(state, settings, stage, event, **metadata):
    trace = state.response.trace
    # Reserve the final slot for the explicit stop event.
    if len(trace) >= settings.max_trace_events - 1 and event != "limit_reached":
        raise BudgetExceeded("trace_limit")
    if len(trace) >= settings.max_trace_events:
        return
    trace.append(TraceEvent(sequence=len(trace) + 1, revision=state.response.revision,
                            stage=stage, event=event, **metadata))
