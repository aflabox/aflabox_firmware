import asyncio
import websockets
import json
from typing import Optional, Dict, Any,Callable
from utils.logger import get_logger

logger = get_logger(__name__)

class WebSocketService:
    def __init__(self, uri: str, device_id: str):
        self.uri = uri
        self.device_id = device_id
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self.message_handlers: Dict[str, Callable] = {}

    async def connect(self) -> None:
        while True:
            try:
                url = f"{self.uri}/{self.device_id}"
                self.websocket = await websockets.connect(url)
                self.connected = True
                logger.info(f"Connected to WebSocket server: {url}")
                await self._handle_messages()
            except Exception as e:
                logger.error(f"WebSocket connection error: {e}")
                self.connected = False
                await asyncio.sleep(5)

    async def _handle_messages(self) -> None:
        while True:
            try:
                message = await self.websocket.recv()
                data = json.loads(message)
                message_type = data.get('type')
                
                if message_type in self.message_handlers:
                    await self.message_handlers[message_type](data)
                else:
                    logger.warning(f"Unhandled message type: {message_type}")
            except websockets.ConnectionClosed:
                logger.warning("WebSocket connection closed")
                break
            except Exception as e:
                logger.error(f"Error handling message: {e}")
                await asyncio.sleep(1)

    async def send_message(self, message: Dict[str, Any]) -> None:
        if not self.connected:
            logger.warning("Cannot send message: WebSocket not connected")
            return
        
        try:
            await self.websocket.send(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.connected = False

    def register_handler(self, message_type: str, handler: Callable) -> None:
        self.message_handlers[message_type] = handler