import asyncio
import asyncpg
from aiogram import Bot

class DBListener:
    def __init__(self, db_url: str, channels: list[str], callback):
        self.db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
        self.channels = channels
        self.callback = callback
        self.conn = None

    async def start(self):
        try:
            self.conn = await asyncpg.connect(self.db_url)
            for channel in self.channels:
                await self.conn.add_listener(channel, self._handle_notification)
            
            print(f"Listening on channels: {self.channels}")
            while True:
                await asyncio.sleep(1) # Keep alive
        except Exception as e:
            print(f"Listener error: {e}")
            await asyncio.sleep(5)
            await self.start() # Reconnect

    def _handle_notification(self, connection, pid, channel, payload):
        # Fire and forget callback
        asyncio.create_task(self.callback(channel, payload))
