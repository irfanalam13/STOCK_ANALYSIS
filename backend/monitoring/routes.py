"""Monitoring endpoints exposing real-time metrics (JSON + Prometheus text)."""
from fastapi import APIRouter, Response

from monitoring.metrics import metrics
from websocket.manager import manager

router = APIRouter(tags=["monitoring"])


@router.get("/metrics")
async def metrics_json() -> dict:
    return metrics.snapshot(active=manager.connection_count)


@router.get("/metrics/prometheus")
async def metrics_prometheus() -> Response:
    data = metrics.snapshot(active=manager.connection_count)
    lines: list[str] = []
    for key, value in data.items():
        lines.append(f"# TYPE nepse_{key} gauge")
        lines.append(f"nepse_{key} {value}")
    return Response("\n".join(lines) + "\n", media_type="text/plain")
