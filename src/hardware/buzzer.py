
from time import sleep
from utils.gpio_helper import GPIOManager,GPIO
# try:
#    from RPi import GPIO
# except Exception:
#    from .simulation import MockRPiGPIO as GPIO

class BuzzerController:
    def __init__(self, pin, frequency=1000, silent=False,gpio:GPIOManager=None):
        self.pin = pin
        self.frequency = frequency
        self.silent = silent
        self.gpio = gpio if gpio else GPIOManager()
        # GPIO.setwarnings(False)
        # GPIO.setmode(GPIO.BCM)
        # GPIO.setup(self.pin, GPIO.OUT)
        self.gpio.setup_pin_sync(self.pin, GPIO.OUT)
        self.pwm = GPIO.PWM(self.pin, self.frequency)
        self.pwm.start(0)  # Start PWM with 0% duty cycle (off)

    def beep(self, duration, frequency=None):
        if not self.silent:
            if frequency:
                self.pwm.ChangeFrequency(frequency)
            self.pwm.ChangeDutyCycle(50)
            sleep(duration)
            self.pwm.ChangeDutyCycle(0)
        sleep(duration)

    def booting(self):
        if not self.silent:
            print("Booting...")
            self.beep(1, 1000)

    def photo_taken(self):
        if not self.silent:
            print("Photo taken...")
            self.beep(0.2, 1500)
            sleep(0.1)
            self.beep(0.2, 1500)

    def error_network(self):
        if not self.silent:
            print("Network error...")
            for _ in range(3):
                self.beep(0.1, 2000)
                sleep(0.1)

    def error_script(self):
        if not self.silent:
            print("Script error...")
            self.beep(0.5, 500)

    def error_upload(self):
        if not self.silent:
            print("Upload error...")
            for _ in range(2):
                self.beep(0.3, 1000)
                sleep(0.2)

    def error_power(self):
        if not self.silent:
            print("Power error...")
            self.beep(0.2, 1000)
            sleep(0.2)
            self.beep(0.2, 1000)
            sleep(0.2)
            self.beep(0.2, 1000)

    def error_overheat(self):
        if not self.silent:
            print("Overheat error...")
            for _ in range(5):
                self.beep(0.1, 2500)
                sleep(0.1)

    def error_sd_card(self):
        if not self.silent:
            print("SD card error...")
            self.beep(1, 300)

    def double_click(self):
        if not self.silent:
            print("Double buzzer detected...")
            self.beep(0.1, 1500)
            sleep(0.1)
            self.beep(0.1, 1500)

    def single_click(self):
        if not self.silent:
            print("Single buzzer detected...")
            self.beep(0.1, 1500)

    def memory_error(self):
        if not self.silent:
            print("Memory error...")
            for _ in range(3):
                self.beep(0.3, 400)
                sleep(0.1)

    def disk_full(self):
        if not self.silent:
            print("Disk full...")
            self.beep(0.5, 800)
            sleep(0.5)
            self.beep(0.5, 800)

    def permission_issue(self):
        if not self.silent:
            print("Permission issue...")
            self.beep(0.2, 1000)
            sleep(0.1)
            self.beep(0.2, 1000)
            sleep(0.1)
            self.beep(0.2, 1000)

    def cleanup(self):
        self.pwm.stop()

    def toggle_silence(self):
        """Toggle the silent mode on or off."""
        self.silent = not self.silent
        if self.silent:
            print("Buzzer silenced.")
        else:
            print("Buzzer active.")