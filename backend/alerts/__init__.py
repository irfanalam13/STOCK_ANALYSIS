"""Alerts & notifications domain (Phase 6).

Real-time, event-driven alert engine: users register conditions against live
market data; a Celery evaluation task fires matching alerts each tick and hands
them to the multi-channel notification layer.
"""
