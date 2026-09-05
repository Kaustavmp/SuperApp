import pytest

from superapp.config import settings
from superapp.platform.billing import BillingTracker, BudgetExceeded


def test_model_resolution_uses_stage_cascade():
    original_provider = settings.llm_provider
    original_tier = settings.cascade_claim_extraction
    try:
        settings.llm_provider = "openai"
        settings.cascade_claim_extraction = "fast"
        assert settings.get_model_for_stage("claim_extraction") == settings.openai_fast_model
    finally:
        settings.llm_provider = original_provider
        settings.cascade_claim_extraction = original_tier


def test_billing_tracks_usage_and_enforces_limits():
    tracker = BillingTracker(max_tokens=10, max_cost_usd=1.0)
    tracker.add_usage(prompt_tokens=4, completion_tokens=5, cost_usd=0.25)
    assert tracker.snapshot()["total_tokens"] == 9
    assert tracker.snapshot()["estimated_cost_usd"] == 0.25
    with pytest.raises(BudgetExceeded):
        tracker.add_usage(completion_tokens=2)
