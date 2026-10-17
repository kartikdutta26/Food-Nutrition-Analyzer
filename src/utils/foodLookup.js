export function formatFoodLookupError(error, foodName) {
  if (error?.status === 404) {
    if (error.message && !error.message.startsWith('No USDA FoodData Central match')) {
      return error.message;
    }
    return `No USDA FoodData Central match was found for “${foodName}”. Try a more specific food name.`;
  }
  if (error?.status === 422) {
    return `The backend rejected this food lookup: ${error.message}`;
  }
  if ([502, 503, 504].includes(error?.status)) {
    return error.message || 'USDA FoodData Central could not complete the lookup. Try again later.';
  }
  return error instanceof Error ? error.message : 'Could not look up nutrition for this food.';
}

export function buildFoodLookupRequest(foodName) {
  const normalizedName = typeof foodName === 'string' ? foodName.trim() : '';
  return normalizedName ? { food_name: normalizedName } : null;
}

export function submitFoodNameLookup(foodName, onAnalyzeFood, options) {
  const lookup = buildFoodLookupRequest(foodName);
  return lookup ? onAnalyzeFood(lookup, options) : Promise.resolve(null);
}

export function getFoodMatchChoices(result) {
  const matches = Array.isArray(result?.matches)
    ? result.matches.filter((match) => (
      match
      && Number.isInteger(Number(match.fdc_id))
      && Number(match.fdc_id) > 0
      && typeof match.name === 'string'
      && match.name.trim()
    ))
    : [];
  return matches.length > 1 ? matches : [];
}

export function buildFoodMealRequest(meal, mealSlot, nutrition, portionMultiplier = 1) {
  if (meal?.data_source === 'sample_preset' && meal.preset_id) {
    return { preset_id: meal.preset_id, meal_slot: mealSlot };
  }

  if (
    meal?.data_source !== 'usda_food_data_central'
    || !Number.isInteger(Number(meal.fdc_id))
    || Number(meal.fdc_id) <= 0
    || !meal.serving?.description
    || !Number.isFinite(Number(meal.serving.gram_weight))
    || Number(meal.serving.gram_weight) <= 0
  ) {
    return null;
  }

  const multiplier = Number(portionMultiplier);
  if (!Number.isFinite(multiplier) || multiplier <= 0) return null;

  const serving = meal.serving;
  return {
    name: meal.name,
    meal_slot: mealSlot,
    nutrition,
    data_source: 'usda_food_data_central',
    fdc_id: Number(meal.fdc_id),
    serving: {
      description: multiplier === 1
        ? serving.description
        : `${multiplier}× ${serving.description}`,
      gram_weight: Number((Number(serving.gram_weight) * multiplier).toFixed(2)),
    },
  };
}
