from typing import Dict, Optional
import configparser
from constants.PinConfig import PinConfig
from exceptions import ConfigurationError

try:
   from RPi import GPIO
except Exception:
   from hardware.simulation import MockRPiGPIO as GPIO

class PinManager:
    """Manages GPIO pin configurations and validation."""
    
    def __init__(self, config: configparser.ConfigParser):
        self.config = config
        self.pin_mapping: Dict[str, int] = {}
        self._load_pin_config()

    def _load_pin_config(self) -> None:
        """Load and validate pin configurations from config file."""
        if 'PINS' not in self.config.sections():
            raise ConfigurationError("PINS section missing in config")

        for pin_name in PinConfig.DEFAULT_PINS:
            try:
                pin_value = self.config.getint('PINS', pin_name)
                if not PinConfig.validate_pin(pin_value):
                    raise ConfigurationError(
                        f"Invalid pin number for {pin_name}: {pin_value}"
                    )
                self.pin_mapping[pin_name] = pin_value
            except configparser.NoOptionError:
                # Use default value if not in config
                self.pin_mapping[pin_name] = PinConfig.get_default_pin(pin_name)
            except ValueError as e:
                raise ConfigurationError(
                    f"Invalid pin configuration for {pin_name}: {str(e)}"
                )

    def get_pin(self, pin_name: str) -> int:
        """
        Get the configured pin number for a given pin name.
        
        Args:
            pin_name: Name of the pin (use PinConfig constants)
            
        Returns:
            int: Configured pin number
            
        Raises:
            ConfigurationError: If pin name is invalid
        """
        if pin_name not in self.pin_mapping:
            raise ConfigurationError(f"Unknown pin name: {pin_name}")
        return self.pin_mapping[pin_name]

    def get_all_pins(self) -> Dict[str, int]:
        """Get all configured pin mappings."""
        return self.pin_mapping.copy()
