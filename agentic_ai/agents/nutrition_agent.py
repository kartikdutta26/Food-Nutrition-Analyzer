"""Coordinate verified lookup and calculation tools; no LLM nutrition generation."""

from pydantic import ValidationError

from agentic_ai.nutrition_errors import NutritionError, NutritionInputError
from agentic_ai.providers.usda import SnapshotProvider
from agentic_ai.schemas.nutrition import FoodCandidate, NUTRIENTS, NutritionIssue, NutritionItemResult, NutritionRequest
from agentic_ai.tools.food_matching import compatible, preparation_needed, search_query
from agentic_ai.tools.nutrition_calculator import calculate, summarize
from agentic_ai.tools.portion_calculator import resolve_portion


class NutritionAnalysisAgent:
    def __init__(self, provider=None):
        self.provider = provider if provider is not None else SnapshotProvider()

    def analyze(self, extraction, selections=()):
        try:
            request = NutritionRequest(extraction=extraction, selections=list(selections))
        except (ValidationError, TypeError):
            raise NutritionInputError("Invalid extraction or item selections for nutrition analysis.") from None
        selections_by_index = {selection.item_index: selection for selection in request.selections}
        return summarize([self.analyze_item(index, food, selections_by_index.get(index))
                          for index, food in enumerate(request.extraction.foods)])

    def analyze_item(self, index, food, selection=None, *, exact_quantity=None):
        """Analyze one item, retaining unrounded values for orchestration checkpoints.

        The existing analyze() interface still validates requests and returns the
        same rounded public result. Callers of this additive method supply validated
        FoodItem and ItemSelection objects.
        """
        item = NutritionItemResult(item_index=index, food=food, status="needs_clarification")
        try:
            if selection and selection.fdc_id:
                record = self.provider.get(selection.fdc_id)
                candidate = FoodCandidate(fdc_id=record.provenance.fdc_id, description=record.provenance.description, data_type=record.provenance.data_type)
                item.candidates = [candidate]
                item.search_scope = "Explicit user-selected food ID; compatibility checked"
                if not compatible(food, candidate):
                    self._clarify(item, "incompatible_food_selection", "Selected USDA record conflicts with the food description or preparation.")
                    return item
            else:
                search = self.provider.search(search_query(food))
                item.search_scope = search.scope
                item.candidates = [candidate for candidate in search.candidates if compatible(food, candidate)]
                if not search.exhaustive:
                    self._clarify(item, "search_incomplete", "USDA search results were truncated. Refine the food description or explicitly select a compatible FDC ID.")
                    return item
                if len(item.candidates) != 1:
                    code = "ambiguous_food" if item.candidates else "food_not_found"
                    self._clarify(item, code, "Choose a compatible food record by its FDC ID." if item.candidates else "No compatible food record found in this provider. Supply a more specific description or another documented source.")
                    return item
                candidate = item.candidates[0]
                if preparation_needed(food, candidate):
                    self._clarify(item, "preparation_required", "Specify the preparation method or explicitly confirm this database record.")
                    return item
                record = self.provider.get(candidate.fdc_id)
                # Details must still agree with search metadata and the request.
                detail_candidate = FoodCandidate(fdc_id=record.provenance.fdc_id, description=record.provenance.description, data_type=record.provenance.data_type)
                if detail_candidate != candidate or not compatible(food, detail_candidate):
                    self._clarify(item, "inconsistent_source_record", "USDA details differ from the selected search result; repeat the lookup.")
                    return item
            item.record = record
            resolution, _, issue = resolve_portion(food, record, selection, exact_quantity=exact_quantity)
            if issue:
                self._clarify(item, issue, "Supply total edible grams or choose a compatible database portion, including size/form where required.")
            else:
                item.portion = resolution
                item.nutrition, item.scale_factor = calculate(record, resolution.requested_grams)
                missing = [name for name in NUTRIENTS if getattr(item.nutrition, name) is None]
                item.status = "incomplete_nutrients" if missing else "complete"
                if missing:
                    item.issues.append(NutritionIssue(code="missing_nutrients", message="Unknown nutrients: " + ", ".join(missing)))
                if record.issues:
                    item.issues.append(NutritionIssue(code="source_data_notes", message="; ".join(record.issues)))
        except NutritionError as error:
            item.status = "error"
            item.issues.append(NutritionIssue(code=error.code, message=str(error)))
        return item

    @staticmethod
    def _clarify(item, code, message):
        item.issues.append(NutritionIssue(code=code, message=message))
        item.questions.append(f"Item {item.item_index} ({item.food.source_text}): {message}")
