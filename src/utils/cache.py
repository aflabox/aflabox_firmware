from datetime import datetime, timedelta
from typing import Optional, Any, Dict
import asyncio
from ..services.financial_service import FinancialService

class AsyncTTLCache:
    """
    Asynchronous TTL (Time To Live) cache implementation.
    """
    def __init__(self, ttl: int):
        self.ttl = ttl
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        async with self._lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if datetime.now() - timestamp < timedelta(seconds=self.ttl):
                    return value
                del self._cache[key]
            return None

    async def set(self, key: str, value: Any) -> None:
        """Set value in cache with current timestamp."""
        async with self._lock:
            self._cache[key] = (value, datetime.now())

    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        async with self._lock:
            self._cache.pop(key, None)

    async def clear(self) -> None:
        """Clear all cached values."""
        async with self._lock:
            self._cache.clear()

# Example usage in main.py
async def setup_financial_services(config_manager) -> FinancialService:
    """Initialize and configure financial services."""
    financial_service = FinancialService(
        base_url=config_manager.get_setting("DEFAULT", "BaseUrl"),
        device_id=config_manager.get_setting("settings", "device_id"),
        cache_ttl=300  # 5 minutes cache
    )
    await financial_service.start()
    return financial_service

# Example of balance display handler
async def display_balance_handler(display_service, financial_service):
    """Handle balance display requests."""
    try:
        balance = await financial_service.get_balance()
        await display_service.show_balance(balance)
    except DeviceError as e:
        logger.error(f"Failed to display balance: {e}")
        await display_service.show_error("Balance unavailable")