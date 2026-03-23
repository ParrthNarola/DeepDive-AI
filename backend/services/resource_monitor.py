"""Resource monitoring — polls CPU & RAM and broadcasts via WebSocket."""

import asyncio
import psutil
from ws.manager import manager


async def poll_resources():
    """Background loop: broadcasts system stats every second."""
    while True:
        payload = {
            "type": "resource_stats",
            "cpu": psutil.cpu_percent(interval=None),
            "ram": psutil.virtual_memory().percent,
        }
        await manager.broadcast(payload)
        await asyncio.sleep(1)
