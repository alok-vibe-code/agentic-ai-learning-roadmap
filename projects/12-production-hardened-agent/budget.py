"""Request-level resource budgets."""

from __future__ import annotations

from dataclasses import dataclass

from config import BudgetConfig
from errors import BudgetExceeded
from models import ProviderResponse


@dataclass
class BudgetUsage:
    attempts: int = 0
    estimated_tokens: int = 0
    simulated_cost_usd: float = 0.0


class RequestBudget:
    def __init__(self, config: BudgetConfig) -> None:
        self.config = config
        self.usage = BudgetUsage()

    def reserve_attempt(self) -> None:
        if self.usage.attempts + 1 > self.config.max_provider_attempts:
            raise BudgetExceeded("Provider-attempt budget exceeded.")
        self.usage.attempts += 1

    def consume_response(self, response: ProviderResponse) -> None:
        new_tokens = self.usage.estimated_tokens + response.estimated_tokens
        new_cost = self.usage.simulated_cost_usd + response.simulated_cost_usd

        if new_tokens > self.config.max_estimated_tokens:
            raise BudgetExceeded("Estimated-token budget exceeded.")
        if new_cost > self.config.max_simulated_cost_usd + 1e-12:
            raise BudgetExceeded("Simulated-cost budget exceeded.")

        self.usage.estimated_tokens = new_tokens
        self.usage.simulated_cost_usd = new_cost

    def snapshot(self) -> dict:
        return {
            "attempts": self.usage.attempts,
            "estimated_tokens": self.usage.estimated_tokens,
            "simulated_cost_usd": round(self.usage.simulated_cost_usd, 8),
        }
