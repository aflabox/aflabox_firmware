from enum import Enum
from enum import Enum
from typing import Dict, Any
from dataclasses import dataclass

class LightType(Enum):
    WHITE = "white"
    UV_365 = "uv_365"

@dataclass
class PinConfig:
    """Pin configuration constants and validation."""
    # Pin names as constants
    MAIN_BUTTON: str = 'ButtonPin'
    WHITE_LIGHT: str = 'WhitePin'
    UV_LIGHT: str = 'UVLightPin'
    BUZZER: str = 'BuzzerPin'
    RED: str = 'RedPin'
    BLUE: str = 'BluePin'
    GREEN: str = 'GreenPin'

    # Default pin numbers (can be overridden by config.ini)
    DEFAULT_PINS: Dict[str, int] = {
        BUTTON: 17,
        WHITE_LIGHT: 18,
        UV_LIGHT: 27,
        BUZZER: 22,
        RED: 23,
        BLUE: 24,
        GREEN: 25
    }

    @staticmethod
    def validate_pin(pin: int) -> bool:
        """Validate if a pin number is within acceptable range."""
        return 0 <= pin <= 27  # Raspberry Pi GPIO pins range

    @classmethod
    def get_default_pin(cls, pin_name: str) -> int:
        """Get default pin number for a given pin name."""
        return cls.DEFAULT_PINS.get(pin_name, -1)