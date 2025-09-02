from smbus2 import SMBus
shown=False
class VirtualSMBus:
    
    class SMBus:
        def __init__(self, bus):
            self.registers = {}  # Simulated I2C registers

        def read_byte_data(self, i2c_addr, register):
            return self.registers.get((i2c_addr, register), 0xFF)  # Default value 0xFF

        def write_byte_data(self, i2c_addr, register, value):
            self.registers[(i2c_addr, register)] = value

class MockRPiGPIO:
    BCM = "BCM"
    BOARD = "BOARD"
    IN = "IN"
    OUT = "OUT"
    PUD_OFF = "PULL_OFF"
    PUD_UP = "PULL_UP"
    PUD_DOWN = "PULL_DOWN"
    HIGH = 1
    LOW = 0

    _mode = None  # Store mode globally
    _pins = {}  # Store pin configurations globally
    _warnings = True  # Warning state
    _pwm_instances = {}  # Store active PWM instances

    @staticmethod
    def setmode(mode):
        if mode not in [MockRPiGPIO.BCM, MockRPiGPIO.BOARD]:
            raise ValueError("Invalid mode. Use GPIO.BCM or GPIO.BOARD")
        MockRPiGPIO._mode = mode
        print(f"Mock GPIO: Mode set to {mode}")

    @staticmethod
    def setup(channel, direction, pull_up_down=PUD_OFF, initial=None):
        if not isinstance(channel, (int, str)):
            raise ValueError("Pin identifier must be an integer or string")

        if direction not in [MockRPiGPIO.IN, MockRPiGPIO.OUT]:
            raise ValueError("Invalid direction. Use GPIO.IN or GPIO.OUT")

        MockRPiGPIO._pins[channel] = {"direction": direction, "pull_up_down": pull_up_down}

        if direction == MockRPiGPIO.OUT and initial is not None:
            MockRPiGPIO._pins[channel]["state"] = initial
            print(f"Mock GPIO: Set pin {channel} to {initial}")

        print(f"Mock GPIO: Setup pin {channel} as {direction} with {pull_up_down}")

    @staticmethod
    def output(channel, state):
        if channel not in MockRPiGPIO._pins or MockRPiGPIO._pins[channel]["direction"] != MockRPiGPIO.OUT:
            raise ValueError(f"Pin {channel} not set as OUTPUT")
        MockRPiGPIO._pins[channel]["state"] = state
        # print(f"Mock GPIO: Set pin {channel} to {'HIGH' if state else 'LOW'}")

    @staticmethod
    def input(channel):
        if channel not in MockRPiGPIO._pins or MockRPiGPIO._pins[channel]["direction"] != MockRPiGPIO.IN:
            raise ValueError(f"Pin {channel} not set as INPUT")
        return MockRPiGPIO._pins[channel].get("state", MockRPiGPIO.LOW)  # Default LOW

    @staticmethod
    def cleanup():
        MockRPiGPIO._pins.clear()
        print("Mock GPIO: Cleanup called")
    @staticmethod
    def setwarnings(flag):
        """Enable or disable warnings"""
        MockRPiGPIO._warnings = flag
        print(f"Mock GPIO: Warnings {'enabled' if flag else 'disabled'}")
    def cleanup(channel: int | list[int] | tuple[int, ...] = -666):
        print(f"Mock GPIO: cleanup")
    class PWM:
        """Mock class for PWM (Pulse Width Modulation)"""
        def __init__(self, channel, frequency):
            if channel not in MockRPiGPIO._pins or MockRPiGPIO._pins[channel]["direction"] != MockRPiGPIO.OUT:
                raise ValueError(f"Pin {channel} must be set as OUTPUT before using PWM")
            self.channel = channel
            self.frequency = frequency
            self.duty_cycle = 0
            self.running = False
            MockRPiGPIO._pwm_instances[channel] = self
            print(f"Mock GPIO: PWM initialized on pin {channel} with frequency {frequency}Hz")

        def start(self, duty_cycle):
            """Start PWM with a given duty cycle (0-100%)"""
            self.duty_cycle = duty_cycle
            self.running = True
            print(f"Mock GPIO: PWM started on pin {self.channel} with {duty_cycle}% duty cycle")
        def ChangeDutyCycle(self,duty):
            pass
        def ChangeFrequency(self, frequency):
            self.frequency = frequency
            print(f"Mock GPIO: PWM frequency changed to {frequency}Hz on pin {self.channel}")
        def change_frequency(self, frequency):
            """Change the PWM frequency"""
            self.frequency = frequency
            print(f"Mock GPIO: PWM frequency changed to {frequency}Hz on pin {self.channel}")

        def change_duty_cycle(self, duty_cycle):
            """Change the PWM duty cycle"""
            self.duty_cycle = duty_cycle
            print(f"Mock GPIO: PWM duty cycle changed to {duty_cycle}% on pin {self.channel}")

        def stop(self):
            """Stop PWM on the pin"""
            self.running = False
            print(f"Mock GPIO: PWM stopped on pin {self.channel}")


class MockSpiDev:
    class SpiDev:
        def __init__(self,mode=0,speed=500000):
            self.mode = 0
            self.max_speed_hz = 500000
            self.bits_per_word = 8
            self.opened = False
            self.showned=False

        def open(self, bus, device):
            self.opened = True
            print(f"Mock SPI: Opened bus {bus}, device {device}")

        def close(self):
            self.opened = False
            print("Mock SPI: Closed")

        def xfer(self, data):
            print(f"Mock SPI: Transferring {len(data)}")
            return [0xFF] * len(data)  # Return dummy data

        def xfer2(self, data):
            print(f"Mock SPI: Transferring (xfer2) {len(data)}")
            return [0xFF] * len(data)

        def writebytes(self, data):
            global shown
            # if shown:
            pass
           
            # print(f"Mock SPI: Writing {len(data)}")
            # shown=True

