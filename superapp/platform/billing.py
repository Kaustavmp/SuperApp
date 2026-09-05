"""Billing stub for usage accounting and future Stripe integration."""

from __future__ import annotations


class BillingTracker:
    def __init__(self):
        self.usage = {"documents_processed": 0, "tokens_consumed": 0}

    def add_usage(self, *, documents_processed: int = 0, tokens_consumed: int = 0):
        self.usage["documents_processed"] += documents_processed
        self.usage["tokens_consumed"] += tokens_consumed

    def snapshot(self):
        return dict(self.usage)
