"""Validate a complete reply before updating its private item checkpoint."""
from agentic_ai.orchestration_errors import OrchestrationError
from agentic_ai.schemas.nutrition import ItemSelection
from agentic_ai.schemas.orchestration import Question
from agentic_ai.tools.portion_calculator import resolve_portion


def make_question(item, new_id):
    result = item.result
    reason = result.issues[0].code if result.issues else "food_not_found"
    allowed = ["leave_unresolved", "refine_food"]
    portions = []
    if result.record:
        allowed += ["quantity", "measured_grams"]
        for portion in result.record.portions:
            selection = ItemSelection(item_index=item.index, fdc_id=result.record.provenance.fdc_id,
                                      portion_id=portion.portion_id)
            _, _, issue = resolve_portion(item.effective_food, result.record, selection,
                                          exact_quantity=item.quantity)
            if issue is None:
                portions.append(portion)
        if portions:
            allowed.append("select_portion")
    else:
        allowed.append("preparation")
        if result.candidates:
            allowed.append("select_food")
    return Question(question_id=new_id(), item_id=item.item_id, item_index=item.index,
                    reason=reason, allowed_actions=allowed, candidates=result.candidates,
                    portions=portions)


def validate_action(item, question, action):
    if action.kind not in question.allowed_actions:
        raise OrchestrationError("action_not_allowed")
    if action.kind == "select_food" and action.fdc_id not in {c.fdc_id for c in question.candidates}:
        raise OrchestrationError("invalid_food_selection")
    if action.kind == "select_portion" and action.portion_id not in {p.portion_id for p in question.portions}:
        raise OrchestrationError("invalid_portion_selection")
    if action.kind == "preparation" and not action.preparation.strip():
        raise OrchestrationError("invalid_preparation")


def apply_action(item, action):
    """Runs only on the transaction's detached draft, after all validation."""
    if action.kind == "leave_unresolved":
        item.left_unresolved = True
        return
    if action.kind == "select_food":
        item.selection = ItemSelection(item_index=item.index, fdc_id=action.fdc_id)
    elif action.kind == "select_portion":
        item.selection = ItemSelection(item_index=item.index, fdc_id=item.result.record.provenance.fdc_id,
                                       portion_id=action.portion_id)
    elif action.kind == "measured_grams":
        item.selection = ItemSelection(item_index=item.index,
                                       fdc_id=item.result.record.provenance.fdc_id,
                                       measured_grams=action.grams)
    elif action.kind == "quantity":
        food = item.effective_food.model_dump()
        food.update(quantity=float(action.quantity), quantity_text=str(action.quantity), unit=action.unit,
                    issues=[])
        item.effective_food = type(item.effective_food).model_validate(food)
        item.quantity = str(action.quantity)
        # A new unit must not inherit a previously chosen portion or measured mass.
        item.selection = ItemSelection(item_index=item.index, fdc_id=item.result.record.provenance.fdc_id)
    elif action.kind == "preparation":
        food = item.effective_food.model_dump()
        food["preparation"] = action.preparation.strip()
        item.effective_food = type(item.effective_food).model_validate(food)
        item.selection, item.search, item.records = None, None, {}
