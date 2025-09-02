from hardware.power import Powerpi
# import RPi.GPIO as GPIO 
import logging
import sys
from time import sleep
from unittest.mock import MagicMock
from utils.gpio_helper import GPIOManager,GPIO,MixedPinFactory

try:
    import pigpio
except ModuleNotFoundError:
    pigpio = MagicMock()
    sys.modules["pigpio"] = pigpio
    
if "linux" not in sys.platform:
    from unittest.mock import MagicMock
    LED = MagicMock()
else:
    from gpiozero import LED
import asyncio

class BatteryService:
    def __init__(self, dashboard,gpio:GPIOManager=None):
        """
        Initialize the BatteryServices class with a UPS monitoring instance and a dashboard.
        """
        self.ups = Powerpi()
        self.dashboard = dashboard
        pin_factory=MixedPinFactory(gpio)
        pin_factory.use_native_for(pin_spec=[13,17])
        
        self.led_task = None  # Track the blinking LED task
        self.has_refreshed_once=False
        self.logger=logging
        # Define LED pins
        self.button_led = LED(13,pin_factory=pin_factory)  # LED for button indicator
        self.charge_led = LED(17,pin_factory=pin_factory)  # LED for charging status
        dashboard.setBatteryUps(self.ups)
    def setLogger(self,logger):
        self.logger=logger
    def addLoop(self,loop):
        self.loop=loop   
    async def power_monitor(self,loop,queue):
        """
        Continuously waits for UPS updates and refreshes the dashboard every 30 seconds.
        """
        self.ups.start_monitoring(loop,queue)
        while True:
            
            new_data = await self.ups.wait_for_update()
          
            if new_data and self.dashboard.isHomeScreen(): #only redraw if in homescreen avoid redirection to home
                self.dashboard.show_homescreen()
                self.has_refreshed_once= True
            await asyncio.sleep(30 if self.has_refreshed_once else 10)
    def stop_monitoring(self):
         self.ups.stop_monitoring()
    def get_latest_status(self):
        return self.ups.get_latest_status()
    async def blink_led(self, led):
        """
        Blinks the LED rapidly to indicate charging status.
        """
        try:
            while True:
                led.on()
                await asyncio.sleep(0.1)  # Short delay for blinking effect
                led.off()
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            led.off()  # Ensure LED turns off when task is cancelled

    async def power_led(self):
        """
        Monitors UPS status and blinks LED when charging.
        """
        self.button_led.on()  # Keep button LED always on
        self.charge_led.on()  # Initial state of charging LED

        while True:
            data = self.ups.get_latest_status()

            if data and data.get("PowerInputStatus") == "Connected":
                if self.led_task is None or (self.led_task and self.led_task.done()):
                    print("Charging started - Blinking LED")
                    self.led_task = asyncio.create_task(self.blink_led(self.charge_led))  # Start blinking
            else:
                if self.led_task and not self.led_task.done():
                    print("Charging stopped - Turning off LED")
                    self.led_task.cancel()  # Stop blinking
                    try:
                        await self.led_task  # Wait for cancellation
                    except asyncio.CancelledError:
                        pass
                    self.charge_led.off()  # Ensure LED is off
                    self.led_task = None  # Reset task
            
            await asyncio.sleep(1)  # Poll UPS status every second

    async def run_services(self):
        """
        Starts all battery-related monitoring tasks.
        """
        await asyncio.gather(
            self.power_monitor(),
            self.power_led()
        )
    async def observe(self):
        
        try:
            #"LISTEN TO BAT INTERRUPTION"
            # GPIO.setmode(GPIO.BCM)
            # GPIO.setup(4, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            # GPIO.add_event_detect(4, GPIO.FALLING, callback=self.interrupt_handler, bouncetime=200)
            pi = pigpio.pi()
            PIN = 4
            pi.set_mode(PIN, pigpio.INPUT)
            pi.set_pull_up_down(PIN, pigpio.PUD_UP)
            pi.callback(PIN, pigpio.FALLING_EDGE, self.interrupt_handler)
            
        except Exception as ex:
            self.logger.error("Error attaching interrupt to GPIO4, UPS will work without interrupt.")
        
        
        while (True):
            self.read_status()
            sleep(2)
