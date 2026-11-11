"""Stable M5.1 errors: never include images, model text, paths or credentials."""
MESSAGES = {
    "invalid_recognition": "Recognition metadata does not match the image-food contract.",
    "invalid_confirmation": "Explicit confirmation does not match the handoff contract.",
    "invalid_handoff": "The confirmed image-food handoff is invalid.",
    "stale_result": "Confirmation refers to a different recognition result or revision.",
    "confirmation_mismatch": "Confirmation decisions or text references disagree with the recognition result.",
    "input_limit": "Image-food metadata exceeds the configured input bounds.",
    "output_limit": "The complete image-food handoff exceeds the configured output bounds.",
    "handoff_failed": "The image-food handoff could not be prepared safely.",
}


class VisionContractError(Exception):
    def __init__(self, code):
        self.code = code if code in MESSAGES else "handoff_failed"
        super().__init__(MESSAGES[self.code])
