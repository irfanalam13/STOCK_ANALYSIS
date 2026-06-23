"""WebSocket endpoint ``/ws/market`` — the per-session real-time channel.

Client authenticates with a JWT access token as the ``token`` query parameter
(browsers can't set Authorization headers on the WS handshake).

Client -> server protocol (JSON text frames):
    {"action": "subscribe",   "symbols": ["NABIL", "NICA"]}
    {"action": "subscribe",   "channel": "ticker"}   # firehose for the ticker bar
    {"action": "unsubscribe", "symbols": ["NABIL"]}
    {"action": "ping"}                                # -> {"type": "pong"}

Server -> client frames:
    {"type": "prices",    "seq": N, "data": [PriceUpdate, ...]}
    {"type": "ohlc",      "seq": N, "data": [OHLCUpdate, ...]}
    {"type": "volume",    "seq": N, "data": [...]}
    {"type": "subscribed","symbols": [...]} | {"type": "pong"} | {"type": "heartbeat"}
"""
import asyncio
import json
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from jose import JWTError

from core.config import settings
from core.redis_client import (
    KEY_MARKET_SNAPSHOT,
    KEY_REPLAY,
    KEY_SEQ,
    get_redis,
)
from core.security import TOKEN_TYPE_ACCESS, decode_token
from security.ws_guard import MessageRateLimiter
from websocket.manager import manager

logger = logging.getLogger(__name__)
router = APIRouter()


async def _send_snapshot(ws: WebSocket, symbols: list[str], ticker: bool) -> None:
    """Push the current market snapshot immediately on subscribe.

    New clients see live state at once instead of waiting for the next tick.
    """
    redis = get_redis()
    raw = await redis.get(KEY_MARKET_SNAPSHOT)
    if not raw:
        return
    quotes = json.loads(raw)
    if not ticker:
        wanted = {s.strip().upper() for s in symbols}
        quotes = [q for q in quotes if q["symbol"] in wanted]
    if not quotes:
        return
    seq = int(await redis.get(KEY_SEQ) or 0)
    await ws.send_text(
        json.dumps({"type": "prices", "seq": seq, "data": quotes, "snapshot": True})
    )


async def _send_replay(ws: WebSocket, from_seq: int) -> None:
    """Replay buffered price envelopes with seq > from_seq, oldest first."""
    redis = get_redis()
    raw_items = await redis.lrange(KEY_REPLAY, 0, -1)  # newest-first
    envelopes = []
    for raw in raw_items:
        try:
            env = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if int(env.get("seq", 0)) > from_seq:
            envelopes.append(env)
    for env in sorted(envelopes, key=lambda e: e["seq"]):
        await ws.send_text(
            json.dumps({"type": "prices", "seq": env["seq"], "data": env["updates"], "replay": True})
        )


async def _handle_action(client_id: str, ws: WebSocket, msg: dict) -> None:
    action = msg.get("action")
    if action == "subscribe":
        ticker = msg.get("channel") == "ticker"
        symbols = msg.get("symbols") or []
        if ticker:
            await manager.subscribe_ticker(client_id)
        if symbols:
            await manager.subscribe(client_id, symbols)
        await ws.send_text(
            json.dumps({"type": "subscribed", "symbols": symbols, "ticker": ticker})
        )
        await _send_snapshot(ws, symbols, ticker)
    elif action == "unsubscribe":
        if msg.get("channel") == "ticker":
            await manager.unsubscribe_ticker(client_id)
        symbols = msg.get("symbols") or []
        if symbols:
            await manager.unsubscribe(client_id, symbols)
    elif action == "replay":
        await _send_replay(ws, int(msg.get("from_seq", 0)))
    elif action == "ping":
        await ws.send_text(json.dumps({"type": "pong"}))


@router.websocket("/ws/market")
async def market_ws(websocket: WebSocket, token: str = Query(...)) -> None:
    # 1) Authenticate the handshake with a valid JWT access token before accept.
    try:
        decode_token(token, expected_type=TOKEN_TYPE_ACCESS)
    except JWTError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    client_id = await manager.connect(websocket)
    # 2) Per-socket flood protection + 3) idle auto-disconnect.
    limiter = MessageRateLimiter(settings.WS_MSG_RATE_LIMIT, settings.WS_MSG_WINDOW)
    try:
        await websocket.send_text(json.dumps({"type": "connected", "client_id": client_id}))
        while True:
            try:
                raw = await asyncio.wait_for(
                    websocket.receive_text(), timeout=settings.WS_IDLE_TIMEOUT
                )
            except asyncio.TimeoutError:
                await websocket.close(code=status.WS_1001_GOING_AWAY)
                break
            if not limiter.allow():
                # Abusive frame rate — reject the connection.
                await websocket.send_text(
                    json.dumps({"type": "error", "error": "rate_limited"})
                )
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                break
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            await _handle_action(client_id, websocket, msg)
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001 - ensure cleanup on any failure
        logger.exception("WebSocket error for %s", client_id)
    finally:
        await manager.disconnect(client_id)
