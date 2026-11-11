"""Milestone 4: deterministic, evidence-linked nutrition interpretation only."""
import time
from decimal import DecimalException
from pydantic import BaseModel, ValidationError

from agentic_ai.nutrition_errors import NutritionError
from agentic_ai.recommendation.evidence import extract_evidence
from agentic_ai.recommendation.rendering import message, RULE_IDS
from agentic_ai.recommendation.rules import apply_rules
from agentic_ai.recommendation.validation import parse_request, validate_nutrition
from agentic_ai.recommendation_config import RecommendationSettings
from agentic_ai.recommendation_errors import RecommendationError
from agentic_ai.schemas.recommendation import InputReference, RecommendationResult


def _raw(value):
    return value.model_dump(mode="python") if isinstance(value, BaseModel) else value


class NutritionRecommendationAgent:
    def __init__(self, settings=None, *, clock=time.time):
        self.settings = settings if settings is not None else RecommendationSettings()
        self.clock = clock

    def recommend(self, nutrition_result, *, context=None):
        return self.recommend_request({"source":{"kind":"nutrition","result":_raw(nutrition_result)},
            "context":{} if context is None else _raw(context)})

    def recommend_session(self, session_response, *, context=None, expected_revision=None):
        return self.recommend_request({"source":{"kind":"session","result":_raw(session_response)},
            "context":{} if context is None else _raw(context), "expected_revision":expected_revision})

    def recommend_request(self, value):
        try:
            request, fingerprint = parse_request(value, self.settings)
            nutrition, session = validate_nutrition(request, self.settings)
            expired = bool(session and self.clock() >= session.expires_at)
            facts, citations = extract_evidence(nutrition)
            status, observations, suggestions, next_steps, limitations, comparisons = apply_rules(
                nutrition, session, request.context, facts, citations, expired=expired)
            result = RecommendationResult(
                status=status,
                input_ref=InputReference(kind=request.source.kind, sha256=fingerprint,
                    session_id=session.session_id if session else None,
                    revision=session.revision if session else None,
                    session_status=session.status if session else None,
                    expires_at=session.expires_at if session else None, expired=expired),
                context=request.context.model_copy(deep=True),
                nutrition_status=nutrition.status if nutrition else None,
                complete_totals=nutrition.complete_totals.model_copy(deep=True) if nutrition else None,
                known_subtotals=nutrition.known_subtotals.model_copy(deep=True) if nutrition else None,
                coverage={name:coverage.model_copy(deep=True) for name,coverage in nutrition.coverage.items()} if nutrition else {},
                facts=facts, observations=observations, suggestions=suggestions, next_steps=next_steps,
                limitations=limitations, citations=citations, comparisons=comparisons,
                session_evidence=tuple(e.model_copy(deep=True) for e in session.evidence) if session else ())
            self._validate_output(result, session)
            # Full output is returned or a safe limit error; warnings are never truncated.
            return RecommendationResult.model_validate_json(result.model_dump_json())
        except RecommendationError:
            raise
        except (NutritionError, DecimalException):
            raise RecommendationError("invalid_evidence") from None
        except (ValidationError, ValueError, TypeError, OverflowError, RecursionError):
            raise RecommendationError("invalid_input") from None
        except Exception:
            raise RecommendationError("recommendation_failed") from None

    def _validate_output(self, result, session):
        entries = result.observations + result.suggestions + result.next_steps + result.limitations
        if len(entries) > self.settings.max_messages or len(result.model_dump_json().encode("utf-8")) > self.settings.max_output_bytes:
            raise RecommendationError("output_limit")
        facts = {fact.id:fact for fact in result.facts}
        citations = {citation.id:citation for citation in result.citations}
        if len(facts) != len(result.facts) or len(citations) != len(result.citations):
            raise RecommendationError("invalid_evidence")
        references = set(facts) | set(citations) | {"input", "context"}
        for fact in result.facts:
            if set(fact.source_refs) - set(citations):
                raise RecommendationError("invalid_evidence")
        for entry in entries:
            if entry.code not in RULE_IDS or entry.rule_id != entry.code or set(entry.evidence_refs) - references:
                raise RecommendationError("invalid_rules")
            kwargs = {}
            if entry.code in {"complete_fact", "subtotal_fact", "unknown_fact"}:
                kwargs["fact"] = facts[entry.evidence_refs[0]]
            elif entry.code.startswith("target_"):
                comparison = next(c for c in result.comparisons if c.fact_ref == entry.evidence_refs[0])
                kwargs = {"fact":facts[comparison.fact_ref], "target":comparison.target,
                    "relation":comparison.relation if comparison.relation != "not_compared" else None}
            elif entry.code == "clarify":
                if session is None:
                    raise RecommendationError("invalid_evidence")
                kwargs["question"] = next(q for q in session.questions if q.question_id == entry.question_id)
            if message(entry.code, entry.evidence_refs, **kwargs) != entry:
                raise RecommendationError("invalid_rules")
