"""Fixed workflow errors; existing agent/contract errors retain their safe codes."""

_MESSAGES = {
    "invalid_configuration": "Image workflow configuration is invalid.",
    "invalid_owner": "A trusted non-empty owner context is required.",
    "workflow_not_found": "The image workflow is unavailable for this owner.",
    "workflow_limit": "The image workflow capacity limit has been reached.",
    "metadata_limit": "Image workflow metadata exceeds the configured limit.",
    "output_limit": "The full workflow response exceeds the configured limit.",
    "confirmation_required": "Explicit image-food confirmation is required before M3.",
    "confirmation_consumed": "This workflow has already attempted its confirmed M3 start.",
    "stale_revision": "The requested session revision is no longer current.",
    "invalid_revision": "A non-negative integer session revision is required.",
    "dependency_mutation": "A dependency altered the supplied session snapshot.",
    "operation_failed": "The image workflow operation could not be completed safely.",
}


class ImageWorkflowError(Exception):
    def __init__(self, code):
        self.code = code if isinstance(code, str) and code in _MESSAGES else "operation_failed"
        super().__init__(_MESSAGES[self.code])
