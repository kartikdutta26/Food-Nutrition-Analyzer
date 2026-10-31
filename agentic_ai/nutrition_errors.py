"""Nutrition-specific errors; Milestone 1's exception contracts stay unchanged."""


class NutritionError(Exception):
    code = "nutrition_error"


class NutritionInputError(NutritionError):
    code = "invalid_nutrition_input"


class MissingCredentialsError(NutritionError):
    code = "usda_credentials_missing"


class USDAAuthenticationError(NutritionError):
    code = "usda_authentication_failed"


class USDARateLimitError(NutritionError):
    code = "usda_rate_limited"


class USDATimeoutError(NutritionError):
    code = "usda_timeout"


class USDAConnectionError(NutritionError):
    code = "usda_unavailable"


class USDAResponseError(NutritionError):
    code = "invalid_usda_response"


class FoodNotFoundError(NutritionError):
    code = "food_not_found"


class SnapshotError(NutritionError):
    code = "invalid_snapshot"
