"""Stable error codes for the CLI and future backend integration."""


class FoodUnderstandingError(Exception):
    code = "food_understanding_error"


class InvalidInputError(FoodUnderstandingError):
    code = "invalid_input"


class ConfigurationError(FoodUnderstandingError):
    code = "configuration_error"


class OllamaConnectionError(FoodUnderstandingError):
    code = "ollama_unavailable"


class OllamaTimeoutError(FoodUnderstandingError):
    code = "ollama_timeout"


class OllamaModelNotFoundError(FoodUnderstandingError):
    code = "model_not_found"


class OllamaResponseError(FoodUnderstandingError):
    code = "invalid_model_response"


class OllamaServiceError(FoodUnderstandingError):
    code = "ollama_service_error"
