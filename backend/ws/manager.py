"""WebSocket Connection Manager for real-time broadcasting."""

import json
import asyncio
from typing import Any
from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections and broadcasts events to all clients."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def broadcast(self, payload: dict[str, Any]):
        """Send a JSON payload to every connected client."""
        message = json.dumps(payload)
        async with self._lock:
            stale: list[WebSocket] = []
            for ws in self.active_connections:
                try:
                    await ws.send_text(message)
                except Exception:
                    stale.append(ws)
            for ws in stale:
                self.active_connections.remove(ws)

    async def send_personal(self, websocket: WebSocket, payload: dict[str, Any]):
        """Send a JSON payload to a single client."""
        await websocket.send_text(json.dumps(payload))


# Singleton used across the application
manager = ConnectionManager()
