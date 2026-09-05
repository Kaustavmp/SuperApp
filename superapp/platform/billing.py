"""Per-analysis token and cost accounting."""

from __future__ import annotations

from dataclasses import dataclass

from superapp.config import settings


class BudgetExceeded(RuntimeError):
    """Raised when an analysis exceeds its configured budget."""


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def as_dict(self) -> dict:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
        }


class BillingTracker:
    def __init__(self, *, max_tokens: int | None = None, max_cost_usd: float | None = None):
        self.usage = Usage()
        self.documents_processed = 0
        self.max_tokens = settings.max_tokens_per_job if max_tokens is None else max_tokens
        self.max_cost_usd = settings.max_cost_per_job_usd if max_cost_usd is None else max_cost_usd

    def add_usage(
        self,
        *,
        documents_processed: int = 0,
        tokens_consumed: int = 0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost_usd: float = 0.0,
    ) -> None:
        if tokens_consumed and not (prompt_tokens or completion_tokens):
            completion_tokens = tokens_consumed
        self.documents_processed += documents_processed
        self.usage.prompt_tokens += prompt_tokens
        self.usage.completion_tokens += completion_tokens
        self.usage.estimated_cost_usd += cost_usd
        self.check_budget()

    def record_response(self, response: dict) -> None:
        """Record provider usage metadata when a provider returns it."""
        usage = response.get("usage", {}) if isinstance(response, dict) else {}
        prompt = int(usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0)
        completion = int(usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0)
        cost = float(usage.get("estimated_cost_usd", 0.0) or 0.0)
        if not cost:
            cost = (
                prompt * settings.input_cost_per_million_tokens
                + completion * settings.output_cost_per_million_tokens
            ) / 1_000_000
        self.add_usage(prompt_tokens=prompt, completion_tokens=completion, cost_usd=cost)

    def check_budget(self) -> None:
        if self.max_tokens and self.usage.total_tokens > self.max_tokens:
            raise BudgetExceeded(f"Token budget exceeded: {self.usage.total_tokens} > {self.max_tokens}")
        if self.max_cost_usd and self.usage.estimated_cost_usd > self.max_cost_usd:
            raise BudgetExceeded(
                f"Cost budget exceeded: ${self.usage.estimated_cost_usd:.4f} > ${self.max_cost_usd:.4f}"
            )

    def snapshot(self) -> dict:
        return {"documents_processed": self.documents_processed, **self.usage.as_dict()}
