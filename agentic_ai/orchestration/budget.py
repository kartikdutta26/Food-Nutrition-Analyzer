"""Budgets are consumed before operations, including each HTTP retry attempt."""
from agentic_ai.orchestration_errors import BudgetExceeded


class Budget:
    def __init__(self, state, settings, *, clock):
        self.state, self.settings, self.clock = state, settings, clock

    def consume(self, name):
        if self.clock() >= self.state.response.expires_at:
            raise BudgetExceeded("session_ttl_limit")
        usage = self.state.response.usage
        if getattr(usage, name) >= getattr(self.settings, "max_" + name):
            raise BudgetExceeded(name + "_limit")
        setattr(usage, name, getattr(usage, name) + 1)

    def http_attempt(self):
        self.consume("http_attempts")
