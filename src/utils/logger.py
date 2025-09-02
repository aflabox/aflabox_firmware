
import os
import sys
import json
import logging
import logging.config
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union
from functools import wraps
import traceback
import yaml
from contextlib import contextmanager

# Configure custom log formatter for better readability
class CustomFormatter(logging.Formatter):
    """Custom formatter with colors and better task information display"""
    
    # Color codes for different log levels
    COLORS = {
        'DEBUG': '\033[94m',  # Blue
        'INFO': '\033[92m',   # Green
        'WARNING': '\033[93m', # Yellow
        'ERROR': '\033[91m',  # Red
        'CRITICAL': '\033[1;91m',  # Bold Red
        'RESET': '\033[0m'    # Reset
    }
    
    def __init__(self, use_colors=True):
        super().__init__(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        self.use_colors = use_colors
    
    def format(self, record):
        # Save original formatting
        original = self._style._fmt
        
        # Format task execution logs specially
        if "Task '" in record.getMessage() and ("completed" in record.getMessage() or 
                                               "cancelled" in record.getMessage() or
                                               "failed" in record.getMessage()):
            self._style._fmt = "%(asctime)s [%(levelname)s] %(message)s"
        # Clean up task execution logs for better readability
        if "Executing <Task" in record.getMessage():
            # Extract just the essential information
            msg = record.getMessage()
            try:
                # Extract task name
                name_start = msg.find("name='") + 6
                name_end = msg.find("'", name_start)
                task_name = msg[name_start:name_end]
                
                # Extract coroutine name
                coro_start = msg.find("coro=<") + 6
                coro_end = msg.find(" ", coro_start)
                if "running at" in msg:
                    coro_end = msg.find(" running at", coro_start)
                elif "done," in msg:
                    coro_end = msg.find(" done,", coro_start)
                coro_name = msg[coro_start:coro_end]
                
                # Extract execution time
                time_start = msg.rfind("took ") + 5
                time_end = msg.rfind(" seconds")
                exec_time = msg[time_start:time_end]
                
                # Create a clean message
                record.msg = f"Task '{task_name}' ({coro_name}) executed in {exec_time} seconds"
                self._style._fmt = "%(asctime)s [%(levelname)s] %(message)s"
            except Exception:
                # If parsing fails, just use original message
                pass
        
        # Apply colors if enabled
        if self.use_colors:
            levelname = record.levelname
            if levelname in self.COLORS:
                record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        
        result = super().format(record)
        # Restore original format
        self._style._fmt = original
        return result
class DeviceLogger:
    """
    Custom logger implementation for device management with context tracking
    and structured logging capabilities.
    """
    def __init__(self, 
                 name: str,
                 log_dir: str = "/var/log/device",
                 config_path: Optional[str] = None,
                 default_level: str = "INFO",
                 capture_extra: bool = True):
        self.name = name
        self.log_dir = Path(log_dir)
        self.capture_extra = capture_extra
        
        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize logger
        self.logger = logging.getLogger(name)
        
        
        if config_path and os.path.exists(config_path):
            self._setup_from_config(config_path)
        else:
            self._setup_default_logging(default_level)
        
        # Context tracking
        self.context: Dict[str, Any] = {}

    def _setup_from_config(self, config_path: str) -> None:
        """Setup logging configuration from file."""
        with open(config_path, 'r') as f:
            if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                config = yaml.safe_load(f)
            else:
                config = json.load(f)
        
        logging.config.dictConfig(config)

    def _setup_default_logging(self, default_level: str) -> None:
        """Setup default logging configuration."""
        # Create formatters
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s'
        )
        
        json_formatter = JsonFormatter()

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        
        # File handler
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / f"{self.name}.log",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=5
        )
        file_handler.setFormatter(file_formatter)
        
        # JSON handler for structured logging
        json_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / f"{self.name}_structured.json",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=5
        )
        json_handler.setFormatter(json_formatter)

        # Set log level
        level = getattr(logging, default_level.upper(), logging.INFO)
        self.logger.setLevel(level)

        # Add handlers
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(json_handler)
        console_handler.setFormatter(CustomFormatter(use_colors=True))

    def set_context(self, **kwargs) -> None:
        """Set context values for logging."""
        self.context.update(kwargs)

    def clear_context(self) -> None:
        """Clear all context values."""
        self.context.clear()

    def _format_message(self, message: str, extra: Optional[Dict[str, Any]] = None) -> str:
        """Format message with context if available."""
        if not self.capture_extra:
            return message

        log_data = {
            'message': message,
            'context': self.context.copy()
        }
        
        if extra:
            log_data['extra'] = extra

        return json.dumps(log_data)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self.logger.debug(self._format_message(message, kwargs))

    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self.logger.info(self._format_message(message, kwargs))

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self.logger.warning(self._format_message(message, kwargs))

    def error(self, message: str, exc_info: bool = False, **kwargs) -> None:
        """Log error message."""
        self.logger.error(
            self._format_message(message, kwargs),
            exc_info=exc_info
        )

    def critical(self, message: str, exc_info: bool = True, **kwargs) -> None:
        """Log critical message."""
        self.logger.critical(
            self._format_message(message, kwargs),
            exc_info=exc_info
        )

    @contextmanager
    def context_bind(self, **kwargs):
        """Temporarily bind context values."""
        previous = self.context.copy()
        self.set_context(**kwargs)
        try:
            yield
        finally:
            self.context = previous

    def function_logger(self, func):
        """Decorator to log function entry and exit."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            self.debug(f"Entering function: {func_name}")
            try:
                result = func(*args, **kwargs)
                self.debug(f"Exiting function: {func_name}")
                return result
            except Exception as e:
                self.error(
                    f"Error in function {func_name}: {str(e)}",
                    exc_info=True
                )
                raise
        return wrapper

class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.utcfromtimestamp(record.created).isoformat(),
            'name': record.name,
            'level': record.levelname,
            'message': record.getMessage(),
            'path': record.pathname,
            'line': record.lineno,
            'function': record.funcName
        }

        if record.exc_info:
            exc_type, exc_value, exc_traceback = record.exc_info
            if exc_type: 
                log_data['exception'] = {
                    'type': exc_type.__name__,
                    'message': str(exc_value),
                    'traceback': traceback.format_exception(exc_type, exc_value, exc_traceback)
                }


        return json.dumps(log_data)

# Global logger instance
_logger_instance: Optional[DeviceLogger] = None

def setup_logger(name: str = "device",
                log_dir: str = "/var/log/device",
                config_path: Optional[str] = None,
                default_level: str = "INFO") -> DeviceLogger:
    """Setup and return global logger instance."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = DeviceLogger(
            name=name,
            log_dir=log_dir,
            config_path=config_path,
            default_level=default_level
        )
    return _logger_instance

def get_logger(name=__name__) -> DeviceLogger:
    """Get global logger instance."""
    if _logger_instance is None:
        return setup_logger(name=name)
    return _logger_instance

# Example usage:
# if __name__ == "__main__":
#     # Setup logger
#     logger = setup_logger(
#         name="device_test",
#         log_dir="logs",
#         default_level="DEBUG"
#     )

#     # Basic logging
#     logger.info("System starting up")
#     logger.debug("Initializing components")

#     # Logging with context
#     logger.set_context(device_id="DEV001", location="main_hall")
#     logger.info("Device initialized")

#     # Logging with temporary context
#     with logger.context_bind(operation="maintenance"):
#         logger.info("Performing maintenance")

#     # Function logging decorator
#     @logger.function_logger
#     def example_function():
#         logger.info("Doing something")
#         raise ValueError("Example error")

#     try:
#         example_function()
#     except ValueError:
#         pass  # Error already logged

#     # Structured logging with extra data
#     logger.info(
#         "Processing complete",
#         duration_ms=150,
#         status="success"
#     )