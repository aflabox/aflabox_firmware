class DeviceError(Exception):
    """Base exception for device-related errors"""
    pass

class ConfigurationError(DeviceError):
    """Raised when there's an error in configuration"""
    pass

class HardwareError(DeviceError):
    """Raised when there's an error with hardware components"""
    pass
