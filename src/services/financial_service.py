import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import aiohttp
from ..exceptions import DeviceError
from ..utils.logger import get_logger
from ..utils.cache import AsyncTTLCache

logger = get_logger(__name__)

class FinancialService:
    """
    Handles all financial operations including balance checking,
    transaction processing, and wallet management.
    """
    def __init__(self, base_url: str, device_id: str, 
                 cache_ttl: int = 300,  # 5 minutes cache
                 max_retries: int = 3,
                 retry_delay: int = 1):
        self.base_url = base_url
        self.device_id = device_id
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Initialize cache for balance
        self.balance_cache = AsyncTTLCache(ttl=cache_ttl)
        
        # Initialize state tracking
        self._last_update: Optional[datetime] = None
        self._balance_update_lock = asyncio.Lock()

    async def start(self) -> None:
        """Initialize the financial service."""
        self.session = aiohttp.ClientSession()
        # Initial balance fetch
        await self.get_balance(force_refresh=True)

    async def stop(self) -> None:
        """Cleanup resources."""
        if self.session:
            await self.session.close()

    async def get_balance(self, force_refresh: bool = False) -> float:
        """
        Get current balance with caching and retry mechanism.
        
        Args:
            force_refresh (bool): Force a fresh balance check ignoring cache
            
        Returns:
            float: Current balance
            
        Raises:
            DeviceError: If balance cannot be retrieved after retries
        """
        cache_key = f"balance_{self.device_id}"
        
        # Return cached balance if available and not forced refresh
        if not force_refresh:
            cached_balance = await self.balance_cache.get(cache_key)
            if cached_balance is not None:
                return cached_balance

        async with self._balance_update_lock:
            # Double check cache in case another task updated while waiting
            if not force_refresh:
                cached_balance = await self.balance_cache.get(cache_key)
                if cached_balance is not None:
                    return cached_balance

            for attempt in range(self.max_retries):
                try:
                    balance = await self._fetch_balance()
                    await self.balance_cache.set(cache_key, balance)
                    self._last_update = datetime.now()
                    return balance
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        raise DeviceError(f"Failed to get balance after {self.max_retries} attempts: {e}")
                    await asyncio.sleep(self.retry_delay * (attempt + 1))

            raise DeviceError("Failed to get balance: Unknown error")

    async def _fetch_balance(self) -> float:
        """
        Internal method to fetch balance from the server.
        """
        if not self.session:
            raise DeviceError("Session not initialized")

        try:
            url = f"{self.base_url}/finance/devices/{self.device_id}/wallet"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return float(data.get('balance', 0.0))
                else:
                    text = await response.text()
                    raise DeviceError(f"Failed to fetch balance: {text}")
        except aiohttp.ClientError as e:
            raise DeviceError(f"Network error while fetching balance: {e}")

    async def process_transaction(self, 
                                amount: float, 
                                transaction_type: str,
                                metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a financial transaction.
        
        Args:
            amount (float): Transaction amount
            transaction_type (str): Type of transaction (e.g., 'test', 'maintenance')
            metadata (dict, optional): Additional transaction metadata
            
        Returns:
            dict: Transaction result including new balance and transaction ID
            
        Raises:
            DeviceError: If transaction processing fails
        """
        if not self.session:
            raise DeviceError("Session not initialized")

        transaction_data = {
            "device_id": self.device_id,
            "amount": amount,
            "type": transaction_type,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }

        try:
            url = f"{self.base_url}/finance/transactions"
            async with self.session.post(
                url,
                json=transaction_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    # Invalidate balance cache
                    await self.balance_cache.delete(f"balance_{self.device_id}")
                    return result
                else:
                    text = await response.text()
                    raise DeviceError(f"Transaction failed: {text}")
        except aiohttp.ClientError as e:
            raise DeviceError(f"Network error during transaction: {e}")

    async def get_transaction_history(self, 
                                    start_date: Optional[datetime] = None,
                                    end_date: Optional[datetime] = None,
                                    limit: int = 10) -> list:
        """
        Get transaction history for the device.
        
        Args:
            start_date (datetime, optional): Start date for history
            end_date (datetime, optional): End date for history
            limit (int): Maximum number of transactions to return
            
        Returns:
            list: List of transactions
        """
        if not self.session:
            raise DeviceError("Session not initialized")

        params = {
            "device_id": self.device_id,
            "limit": limit
        }

        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()

        try:
            url = f"{self.base_url}/finance/transactions/history"
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    text = await response.text()
                    raise DeviceError(f"Failed to fetch transaction history: {text}")
        except aiohttp.ClientError as e:
            raise DeviceError(f"Network error while fetching history: {e}")
