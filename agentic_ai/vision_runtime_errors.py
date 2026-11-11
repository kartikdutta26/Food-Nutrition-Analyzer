"""Fixed public M5.3 failures; never expose model text, images or paths."""

_MESSAGES = {
    "invalid_configuration": "The local vision configuration is invalid.",
    "service_unavailable": "The local Ollama service is unavailable.",
    "timeout": "The local vision operation exceeded its time limit.",
    "response_limit": "The local vision response exceeded its size limits.",
    "invalid_response": "Ollama returned an invalid vision response.",
    "model_missing": "Install the approved local vision model before recognition.",
    "unsupported_runtime": "This local Ollama version is not supported for vision.",
    "vision_unavailable": "The installed model does not declare vision capability.",
    "unsafe_model": "The selected model is not an approved local vision model.",
    "model_changed": "The installed vision model changed during the operation.",
    "invalid_model_output": "The model output failed the food-identity safety contract.",
    "invalid_image": "Only intact, preprocessed image input is accepted.",
    "insufficient_memory": "Available RAM is below the conservative local demo threshold.",
    "memory_unavailable": "Available RAM could not be checked safely.",
    "inference_failed": "Local food recognition could not be completed safely.",
}


class VisionRuntimeError(Exception):
    def __init__(self, code):
        self.code = code if isinstance(code, str) and code in _MESSAGES else "inference_failed"
        super().__init__(_MESSAGES[self.code])
