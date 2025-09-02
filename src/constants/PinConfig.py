class PinConfig:
    """Pin configuration constants and validation."""
    
    # ✅ Class variables (Static Constants)
    MAIN_BUTTON = "ButtonPin"
    WHITE_LIGHT = "WhitePin"
    UV_LIGHT = "UVLightPin"
    BUZZER = "BuzzerPin"
    RED = "RedPin"
    BLUE = "BluePin"
    GREEN = "GreenPin"

    # ✅ Default pin numbers (Static Class Variable)
    DEFAULT_PINS = {
        MAIN_BUTTON: 12,
        WHITE_LIGHT: 18,
        UV_LIGHT: 27,
        BUZZER: 16,
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
        return cls.DEFAULT_PINS.get(pin_name, -1)  # Return -1 if pin not found
