import uuid
import socket
import platform
import asyncio
import aiohttp
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pydantic import BaseModel
from typing import Dict, Any, Optional

from ..utils.logger import get_logger
from ..exceptions import DeviceError

logging = get_logger(__name__)





class DeviceService:
    def __init__(self, base_url: str, device_code: str):
        self.base_url = base_url
        self.device_code = device_code
        self.account_balance = "N/A"
        self.headers = {
            "Content-Type": "application/json"
        }
        
    @retry(
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        reraise=True
    )
    async def _make_request(self, method: str, endpoint: str, data: Any = None) -> Dict[str, Any]:
        """Make HTTP request with retries using tenacity"""
        async with aiohttp.ClientSession() as session:
            request_method = getattr(session, method.lower())
            async with request_method(
                f"{self.base_url}/{endpoint}", 
                data=data.json() if data else None,
                headers=self.headers
            ) as response:
                if response.status == 200:
                    if method.lower() == "get":
                        return await response.json()
                    return {"status": "success"}
                else:
                    error_text = await response.text()
                    logging.error(f"Request failed with status {response.status}: {error_text}")
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=f"Request failed: {error_text}",
                        headers=response.headers
                    )
    
    async def register_device(self) -> None:
        """Register device with server with retry capability"""
        try:
            # Get device MAC address
            mac = uuid.UUID(int=uuid.getnode()).hex[-12:]
            mac = ':'.join(mac[i:i+2] for i in range(0, 12, 2))
            
            # Get hostname and IP
            host = socket.gethostname()
            ip = None
            try:
                ip = socket.gethostbyname(host)
            except Exception:
                logging.warning("Could not resolve IP address")
                
            # Prepare device data
            data = {
                "serial_number": self.device_code,
                "mac_address": mac,
                "system": platform.system(),
                "node_name": platform.node(),
                "host_name": host,
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "ip_address": ip,
                'timezone': datetime.now().astimezone().strftime('%Z:%z')
            }
            
            # Create log object
            log = DeviceLog(
                device_id=uuid.uuid4(),
                log_type="device_data", 
                log_data=data
            )
            
            # Send data with retry capability
            await self._make_request("post", "device/device-logs", data=log)
            logging.info("Device registered successfully")
            
        except Exception as e:
            logging.error(f"Failed to register device: {str(e)}")
    
    async def get_balance(self) -> Optional[str]:
        """Get device wallet balance with retry capability"""
        try:
            wallet_endpoint = f"finance/devices/{self.device_code}/wallet"
            logging.info(f"Fetching balance from: {self.base_url}/{wallet_endpoint}")
            
            wallet = await self._make_request("get", wallet_endpoint)
            self.account_balance = wallet.get('balance')
            return self.account_balance
            
        except Exception as e:
            logging.error(f"Failed to get balance after retries: {str(e)}")
            self.account_balance = "N/A"
            return None
    
    async def get_test_logs(self) -> None:
        """Get test logs from the device"""
        # Empty implementation as requested
        pass
    
    async def get_device_settings(self) -> None:
        """Get device settings"""
        # Empty implementation as requested
        pass
    
    async def is_device_up_to_date(self) -> None:
        """Check if device firmware is up to date"""
        # Empty implementation as requested
        pass
    
    async def update_firmware(self) -> None:
        """Update device firmware"""
        # Empty implementation as requested
        pass


# Example usage
async def main():
    service = DeviceService()
    await service.register_device()
    balance = await service.get_balance()
    print(f"Current balance: {balance}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
    
    