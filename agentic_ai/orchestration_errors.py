"""Stable transport-independent orchestration failures. Messages contain no tool data."""

class OrchestrationError(Exception):
    def __init__(self, code, message=None):
        self.code = code
        super().__init__(message or code.replace("_", " ").capitalize() + ".")


class BudgetExceeded(OrchestrationError):
    pass
