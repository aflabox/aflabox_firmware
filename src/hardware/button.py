import asyncio
from typing import Callable, Optional

import time
from utils.gpio_helper import GPIOManager,GPIO
# try:
#    from RPi import GPIO
# except Exception:
#    from .simulation import MockRPiGPIO as GPIO
class Button:
    def __init__(self, pin: int, debounce_time: float = 0.08,
                 click_threshold: float = 0.25, long_press_threshold: float = 1.2,gpio:GPIOManager=None):
        self.pin = pin
        self.debounce_time = debounce_time
        self.click_threshold = click_threshold
        self.long_press_threshold = long_press_threshold
        self.last_event_time = 0
        self.click_count = 0
        self.button_pressed = False
        self.ignore_until = time.monotonic() + 0.5  # Ignore first 500ms
        self.gpio = gpio if gpio else GPIOManager()
        self._setup_gpio()
        
       


    def _setup_gpio(self) -> None:
        # GPIO.setmode(GPIO.BCM)
        self.gpio.setup_pin_sync(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        # GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    async def watch(self, single_click_callback: Optional[Callable] = None,
                   double_click_callback: Optional[Callable] = None,
                   long_press_callback: Optional[Callable] = None) -> None:
        state = GPIO.input(self.pin)
        
        while True:
            await asyncio.sleep(0.005)
            # if time.monotonic() < self.ignore_until:
            #     return False  # Ignore startup noise
        
            new_state = GPIO.input(self.pin)
            current_time = time.time()

            if new_state != state:
                if new_state == GPIO.LOW:
                    self.button_pressed = True
                    press_time = current_time
                elif new_state == GPIO.HIGH and self.button_pressed:
                    self.button_pressed = False
                    press_duration = current_time - press_time
                    
                    if press_duration >= self.long_press_threshold:
                        if long_press_callback:
                            await long_press_callback(press_duration)
                    else:
                        self.click_count += 1
                        asyncio.create_task(
                            self._handle_clicks(press_time, single_click_callback, double_click_callback)
                        )
                state = new_state

    async def _handle_clicks(self, press_time: float,
                           single_click_callback: Optional[Callable],
                           double_click_callback: Optional[Callable]) -> None:
        await asyncio.sleep(self.debounce_time)
        _time_taken=time.time() - press_time
        if _time_taken >= self.click_threshold:
            if self.click_count == 1 and single_click_callback:
                await single_click_callback(_time_taken)
            elif self.click_count > 1 and double_click_callback:
                await double_click_callback(_time_taken)
            self.click_count = 0