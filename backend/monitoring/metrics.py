"""In-process metrics for the real-time layer.

A single mutable counter object updated on the hot paths (WebSocket sends,
broadcaster consumption) and read by the ``/metrics`` endpoints. Deliberately
dependency-free: no Prometheus client, but a Prometheus text exposition is
rendered on demand so an external scraper can still consume it.

Tracked signals (per the monitoring requirement):
* WebSocket messages/sec  — derived from ``ws_messages_sent`` between scrapes
* Redis lag               — consume time minus the tick timestamp (ms)
* Dropped frames          — ``broadcaster_seq_gaps`` (missing sequence numbers)
"""
import time
from dataclasses import dataclass, field


@dataclass
class Metrics:
    ws_connections_total: int = 0
    ws_messages_sent: int = 0
    ws_dead_reaped: int = 0

    broadcaster_envelopes: int = 0
    broadcaster_reconnects: int = 0
    broadcaster_seq_gaps: int = 0
    last_seq: int = 0
    last_lag_ms: float = 0.0

    _started: float = field(default_factory=time.monotonic)
    _last_scrape_t: float = field(default_factory=time.monotonic)
    _last_scrape_sent: int = 0

    def snapshot(self, active: int) -> dict:
        """Return current metrics, computing the messages/sec since last scrape."""
        now = time.monotonic()
        dt = now - self._last_scrape_t
        rate = (self.ws_messages_sent - self._last_scrape_sent) / dt if dt > 0 else 0.0
        self._last_scrape_t = now
        self._last_scrape_sent = self.ws_messages_sent
        return {
            "uptime_seconds": round(now - self._started, 1),
            "ws_active_connections": active,
            "ws_connections_total": self.ws_connections_total,
            "ws_messages_sent": self.ws_messages_sent,
            "ws_messages_per_sec": round(rate, 2),
            "ws_dead_reaped": self.ws_dead_reaped,
            "broadcaster_envelopes": self.broadcaster_envelopes,
            "broadcaster_reconnects": self.broadcaster_reconnects,
            "broadcaster_seq_gaps": self.broadcaster_seq_gaps,
            "last_seq": self.last_seq,
            "redis_lag_ms": round(self.last_lag_ms, 1),
        }


metrics = Metrics()
