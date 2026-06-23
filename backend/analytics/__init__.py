"""Advanced analytics dashboard domain (Phase 7).

Institutional-style market analytics: live market overview, sector strength,
gainers/losers, heatmaps, a technical-indicator engine (RSI/MACD/SMA/EMA/
Bollinger), and a rule-based AI insights layer that turns the numbers into
plain-language interpretations.

The number-crunching (``indicators``, ``aggregator``, ``ai_insights``) is pure
and I/O-free so it is fully unit-testable and reusable by both the async API
path and the synchronous Celery precompute path.
"""
