import os
import asyncio
from typing import List
from services.websocket_service import WebSocketService
from services.rabbitmq_service import RabbitMQService
from services.battery_service import BatteryService
from services.firmware import FirmwareUpdater
from hardware.button import Button
from hardware.display import DashboardAnimation
from utils.config_manager import ConfigManager
from utils.logger import get_logger
from utils.menu_handler import MenuHandler
from utils.pin_manager import PinManager
from constants.PinConfig import PinConfig
from hardware.button import Button
from services.camera_scanner_service import CameraScannerService
from hardware.buzzer import BuzzerController
import asyncio
from typing import List
import numpy as np
import importlib
from utils.click_tracker import ClickTracker
from services.test_retries import TestRetryWorker
try:
   from RPi import GPIO
except Exception:
   from hardware.simulation import MockRPiGPIO as GPIO





# Run script
dashboard = DashboardAnimation()

led_task = None
thresholds = {
    "click":[],
    "double_click":[],
    "long_press":[],
}
config_path=os.path.abspath("../config/config.ini")
config = ConfigManager(config_path)

logger=get_logger()
dashboard.addConfig(config.config)
# Initialize hardware components
pin_manager = PinManager(config.config)

buzzer = BuzzerController(pin_manager.get_pin(PinConfig.BUZZER))

click_tracker = ClickTracker(device_id=config.config.get('DEVICE_SETTINGS', 'device_id'))   
button = Button(pin_manager.get_pin(PinConfig.MAIN_BUTTON),debounce_time= 0.08,click_threshold = 0.25, long_press_threshold= 1.2)

 # Initialize services
websocket_service = WebSocketService(
    config.config.get('WEBSOCKET', 'remote_uri'),
    config.config.get('DEVICE_SETTINGS', 'device_id')
)

test_reuploader=TestRetryWorker(
    config=config.config,
)
rabbitmq_service = RabbitMQService(
    config.config.get('RABBITMQ_QUEUE', 'amq_url'),
    config.config.get('DEVICE_SETTINGS', 'device_id'),
    buzzer=buzzer
)


firmwareUpdater = FirmwareUpdater(config_path=config_path)

battery_service = BatteryService(
    dashboard=dashboard
)
battery_service.setLogger(logger)

camera_scanner = CameraScannerService(
                   device_id=config.config.get('DEVICE_SETTINGS', 'device_id'),
                   config=config.config,
                   dashboard=dashboard
                )
# camera_scanner.switch_led_off()

rabbitmq_service.register_handler("TEST_RESULTS",camera_scanner.show_test_results)

menu_handler = MenuHandler(click_tracker, dashboard)
menu_handler.addScanner(camera_scanner)
menu_handler.addUpdater(firmwareUpdater)



dashboard.show_homescreen()

async def safe_task(name, coro):
    try:
        return await coro
    except Exception as e:
        return f"{name} failed: {e}"


def safe_cleanup():
    try:
        GPIO.cleanup()
    except RuntimeError as e:
        if "set pin numbering mode" in str(e):
            # Gracefully ignore or log a warning if desired
            print("GPIO cleanup called without setting mode — skipping cleanup.")
        else:
            raise  # Re-raise if it's an unexpected error   
async def main():
    loop = asyncio.get_running_loop()
    battery_service.addLoop(loop)
    # camera_scanner.start_file_uploads()
    loop.create_task(camera_scanner.start_file_uploads())
    loop.create_task(test_reuploader.start())
    
    
    
    tasks: List[asyncio.Task] = [
 
        asyncio.create_task(button.watch(
            single_click_callback=menu_handler.handle_short_press,
            double_click_callback=menu_handler.handle_double_press,
            long_press_callback=menu_handler.handle_long_press
        )),
        asyncio.create_task(battery_service.power_monitor(loop,asyncio.Queue)),
        asyncio.create_task(battery_service.power_led()),
        # asyncio.create_task(rabbitmq_service.start())
        
    ]
    try:
        dashboard.show_homescreen()
        loop.create_task(rabbitmq_service.start()) 
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
       print("Shutting down...")
    except Exception as e:
       logger.error(f"{e}",exc_info=True)
    finally:
        for task in tasks:
            task.cancel()
        await rabbitmq_service.stop()
        battery_service.stop_monitoring()
        camera_scanner.stop_file_uploads()
        dashboard.cleanup()
        test_reuploader.stop()
        
        # safe_cleanup()
    
 
if __name__ == "__main__":
    
    asyncio.run(main())
