"""WebSocket connection pool + channel-based subscription engine.

Responsibilities (spec "WebSocket Event Engine"):
    connect / disconnect      — manage the connection pool
    subscribe / unsubscribe   — per-stock channel subscriptions
    subscribe_ticker          — firehose of every price update (ticker bar)
    route_*                   — fan a batched update out to the right clients

Design for scale
----------------
* A reverse index ``symbol -> {client_id}`` gives O(subscribers) fan-out per
  symbol instead of scanning every connection.
* Ticker (firehose) clients receive ONE shared serialized payload — it is
  JSON-encoded once per batch, not once per client.
* Per-symbol subscribers receive only the slice of the batch they asked for.
* Each socket has its own send lock so concurrent batches never interleave
  frames on the same connection.

This keeps the hot path proportional to *interested* clients, which is what
lets the engine approach the 10k-connection / sub-500ms target horizontally
(every API replica runs its own manager + Redis subscriber).
"""
import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import WebSocket

from monitoring.metrics import metrics

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL = 20  # seconds between server-initiated heartbeats


class ClientConnection:
    __slots__ = ("id", "ws", "symbols", "ticker", "lock", "alive")

    def __init__(self, client_id: str, ws: WebSocket) -> None:
        self.id = client_id
        self.ws = ws
        self.symbols: set[str] = set()
        self.ticker = False
        self.lock = asyncio.Lock()
        self.alive = True


class ConnectionManager:
    def __init__(self) -> None:
        self._clients: dict[str, ClientConnection] = {}
        self._symbol_index: dict[str, set[str]] = defaultdict(set)
        self._ticker_clients: set[str] = set()
        self._lock = asyncio.Lock()
        self._heartbeat_task: asyncio.Task | None = None

    # ---- connection lifecycle -------------------------------------------- #
    async def connect(self, ws: WebSocket) -> str:
        await ws.accept()
        client_id = uuid4().hex
        conn = ClientConnection(client_id, ws)
        async with self._lock:
            self._clients[client_id] = conn
        metrics.ws_connections_total += 1
        logger.info("WS connect %s (%d active)", client_id, len(self._clients))
        return client_id

    async def disconnect(self, client_id: str) -> None:
        async with self._lock:
            conn = self._clients.pop(client_id, None)
            if not conn:
                return
            for symbol in conn.symbols:
                self._symbol_index[symbol].discard(client_id)
                if not self._symbol_index[symbol]:
                    self._symbol_index.pop(symbol, None)
            self._ticker_clients.discard(client_id)
        logger.info("WS disconnect %s (%d active)", client_id, len(self._clients))

    # ---- subscriptions --------------------------------------------------- #
    async def subscribe(self, client_id: str, symbols: list[str]) -> None:
        async with self._lock:
            conn = self._clients.get(client_id)
            if not conn:
                return
            for raw in symbols:
                symbol = raw.strip().upper()
                if not symbol:
                    continue
                conn.symbols.add(symbol)
                self._symbol_index[symbol].add(client_id)

    async def unsubscribe(self, client_id: str, symbols: list[str]) -> None:
        async with self._lock:
            conn = self._clients.get(client_id)
            if not conn:
                return
            for raw in symbols:
                symbol = raw.strip().upper()
                conn.symbols.discard(symbol)
                self._symbol_index[symbol].discard(client_id)
                if not self._symbol_index[symbol]:
                    self._symbol_index.pop(symbol, None)

    async def subscribe_ticker(self, client_id: str) -> None:
        async with self._lock:
            conn = self._clients.get(client_id)
            if conn:
                conn.ticker = True
                self._ticker_clients.add(client_id)

    async def unsubscribe_ticker(self, client_id: str) -> None:
        async with self._lock:
            conn = self._clients.get(client_id)
            if conn:
                conn.ticker = False
            self._ticker_clients.discard(client_id)

    # ---- low-level send -------------------------------------------------- #
    async def _send(self, conn: ClientConnection, payload: str) -> bool:
        try:
            async with conn.lock:
                await conn.ws.send_text(payload)
            metrics.ws_messages_sent += 1
            return True
        except Exception:
            conn.alive = False
            return False

    async def _snapshot(self) -> dict[str, ClientConnection]:
        async with self._lock:
            return dict(self._clients)

    # ---- routing (called by the broadcaster) ----------------------------- #
    async def route_prices(self, seq: int, updates: list[dict]) -> None:
        """Fan a price batch to ticker clients (full) + per-symbol subscribers."""
        if not updates:
            return
        clients = await self._snapshot()
        update_map = {u["symbol"]: u for u in updates}
        sends: list[asyncio.Future] = []

        # Ticker firehose: encode once, reuse for all ticker clients.
        if self._ticker_clients:
            full = json.dumps({"type": "prices", "seq": seq, "data": updates})
            for cid in list(self._ticker_clients):
                conn = clients.get(cid)
                if conn:
                    sends.append(asyncio.ensure_future(self._send(conn, full)))

        # Per-symbol subscribers (skip ticker clients — already covered).
        for cid, conn in clients.items():
            if conn.ticker or not conn.symbols:
                continue
            subset = [update_map[s] for s in conn.symbols if s in update_map]
            if subset:
                msg = json.dumps({"type": "prices", "seq": seq, "data": subset})
                sends.append(asyncio.ensure_future(self._send(conn, msg)))

        await self._flush(sends)

    async def route_ohlc(self, seq: int, updates: list[dict]) -> None:
        """Send candle updates only to clients subscribed to that symbol."""
        await self._route_per_symbol("ohlc", seq, updates)

    async def route_volume(self, seq: int, updates: list[dict]) -> None:
        await self._route_per_symbol("volume", seq, updates)

    async def _route_per_symbol(
        self, kind: str, seq: int, updates: list[dict]
    ) -> None:
        if not updates:
            return
        clients = await self._snapshot()
        sends: list[asyncio.Future] = []
        for cid, conn in clients.items():
            wanted = conn.symbols
            if not wanted and not conn.ticker:
                continue
            subset = [
                u for u in updates if conn.ticker or u["symbol"] in wanted
            ]
            if subset:
                msg = json.dumps({"type": kind, "seq": seq, "data": subset})
                sends.append(asyncio.ensure_future(self._send(conn, msg)))
        await self._flush(sends)

    async def _flush(self, sends: list[asyncio.Future]) -> None:
        if not sends:
            return
        await asyncio.gather(*sends, return_exceptions=True)
        await self._reap_dead()

    async def _reap_dead(self) -> None:
        dead = [cid for cid, c in (await self._snapshot()).items() if not c.alive]
        for cid in dead:
            await self.disconnect(cid)
        if dead:
            metrics.ws_dead_reaped += len(dead)

    # ---- heartbeat ------------------------------------------------------- #
    async def _heartbeat_loop(self) -> None:
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            payload = json.dumps(
                {"type": "heartbeat", "ts": datetime.now(timezone.utc).isoformat()}
            )
            for conn in (await self._snapshot()).values():
                await self._send(conn, payload)
            await self._reap_dead()

    async def start_heartbeat(self) -> None:
        if self._heartbeat_task is None:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def stop_heartbeat(self) -> None:
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None

    @property
    def connection_count(self) -> int:
        return len(self._clients)


manager = ConnectionManager()
