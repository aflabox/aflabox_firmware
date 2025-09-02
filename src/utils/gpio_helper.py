#!/usr/bin/env python3
"""
Enhanced GPIO Manager with comprehensive conflict resolution
for pin setup and output operations.

This module provides a centralized way to manage GPIO pins,
prevent conflicts between different parts of an application,
and work with multiple GPIO libraries including gpiozero.
"""
import asyncio
import logging
import time
import sys

from .logger import get_logger
from threading import Lock, RLock
from datetime import datetime
from typing import Dict, Set, List, Callable, Any, Optional, Union, Tuple

logger=get_logger()

# Flag to track GPIO initialization state
_gpio_initialized = False

try:
    from gpiozero.pins.native import NativeFactory
    from gpiozero.pins.rpigpio import RPiGPIOFactory
    from gpiozero import Device
    from gpiozero.pins.local import  LocalPiPin
except ImportError:
    pass
# Try importing GPIO with proper error handling
try:
    from RPi import GPIO
    IS_RPI = True
except ImportError:
    try:
        # Try lgpio as alternative
        import lgpio
        IS_RPI = True
        # Create a compatibility layer
        class GPIOCompat:
            OUT = 1
            IN = 0
            BCM = 0
            BOARD = 1
            PUD_UP = 1
            PUD_DOWN = 0
            LOW = 0
            HIGH = 1
            
            @staticmethod
            def setmode(mode):
                # lgpio doesn't need setmode
                pass
                
            @staticmethod
            def setup(pin, mode, pull_up_down=None, initial=None):
                try:
                    handle = lgpio.gpiochip_open(0)
                    if mode == GPIOCompat.OUT:
                        lgpio.gpio_claim_output(handle, pin)
                        if initial is not None:
                            lgpio.gpio_write(handle, pin, initial)
                    else:
                        lgpio.gpio_claim_input(handle, pin)
                    return handle
                except Exception as e:
                    logger.error(f"lgpio setup error on pin {pin}: {e}")
                    raise
            
            @staticmethod
            def cleanup(pin=None):
                try:
                    # lgpio needs to close handles
                    pass  # Simplified for example
                except:
                    pass
                    
        GPIO = GPIOCompat
    except ImportError:
        from hardware.simulation import MockRPiGPIO as GPIO
        IS_RPI = False
        logger.warning("Using mock GPIO - hardware control disabled")

def init_gpio():
    """Initialize GPIO once to avoid conflicts"""
    global _gpio_initialized
    if not _gpio_initialized:
        try:
            # Ensure GPIO is properly cleaned up before initializing
            try:
                GPIO.cleanup()
            except:
                pass
                
            # Set mode only once per application lifecycle
            if hasattr(GPIO, 'setmode'):
                GPIO.setmode(GPIO.BCM)
            _gpio_initialized = True
            logger.info("GPIO initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing GPIO: {e}")
            return False
    return True

# Pin event types for notifications
class PinEventType:
    SETUP = 'setup'
    VALUE_CHANGE = 'value_change'
    RELEASE = 'release'
    CONFLICT = 'conflict'

class GPIOManager:
    """
    Comprehensive GPIO manager with conflict resolution
    
    Features:
    - Pin setup and mode tracking
    - Conflict detection and resolution
    - Pin value monitoring
    - Event notification system
    - Support for different GPIO libraries
    - Support for gpiozero integration
    - Comprehensive logging
    - Thread-safe operations
    
    This manager can be used with both synchronous and asynchronous code,
    and supports integration with gpiozero and other GPIO libraries.
    """
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super(GPIOManager, cls).__new__(cls)
            cls._instance._setup()
        return cls._instance
    
    def _setup(self):
        """Set up the manager's internal state"""
        if not self._initialized:
            # Main tracking collections
            self._pins_in_use: Set[int] = set()
            self._pin_objects: Dict[int, Any] = {}
            self._pin_modes: Dict[int, int] = {}
            self._pin_values: Dict[int, int] = {}
            self._pin_owners: Dict[int, str] = {}
            self._pin_priorities: Dict[int, int] = {}
            self._pin_listeners: Dict[int, List[Callable]] = {}
            self._pin_setups: List[Dict[str, Any]] = []
            self._pin_handles: Dict[int, Any] = {}
            
            # Lock for thread safety
            self._lock = RLock()
            
            # Async lock if asyncio is available
            if 'asyncio' in sys.modules:
                self._async_lock = asyncio.Lock()
            else:
                self._async_lock = None
                
            # Logging setup
            self.logger = logger
            
            # Initialize GPIO
            init_gpio()
            
            # Mark as initialized
            self._initialized = True
    
    # ===== PIN SETUP METHODS =====
    
    def setup_pin_sync(self, pin: int, mode: int, pull_up_down: Optional[int] = None, 
                       initial: Optional[int] = None, owner: Optional[str] = None, 
                       priority: int = 0, force: bool = False) -> bool:
        """
        Setup a pin with comprehensive conflict handling
        
        Args:
            pin: GPIO pin number (BCM numbering)
            mode: GPIO.OUT or GPIO.IN
            pull_up_down: For input pins, pull-up/down resistor mode
            initial: For output pins, initial value
            owner: Optional owner identifier for conflict resolution
            priority: Priority level (higher wins conflicts)
            force: Force reconfiguration even if conflicts
            
        Returns:
            bool: Success or failure
        """
        with self._lock:
            # Record this setup request for tracking
            setup_info = {
                'pin': pin,
                'mode': mode,
                'pull_up_down': pull_up_down,
                'initial': initial,
                'owner': owner,
                'priority': priority,
                'timestamp': time.time()
            }
            self._pin_setups.append(setup_info)
            
            # Check if pin is already in use
            if pin in self._pins_in_use:
                current_mode = self._pin_modes.get(pin)
                current_owner = self._pin_owners.get(pin)
                current_priority = self._pin_priorities.get(pin, 0)
                
                # Case 1: Same mode, no conflict
                if current_mode == mode:
                    # Update owner if higher priority
                    if owner and (force or priority >= current_priority):
                        self._pin_owners[pin] = owner
                        self._pin_priorities[pin] = priority
                    
                    # For output pins, update value if specified
                    if mode == GPIO.OUT and initial is not None:
                        try:
                            GPIO.output(pin, initial)
                            self._pin_values[pin] = initial
                            
                            # Notify listeners about value change
                            self._notify_pin_event(pin, PinEventType.VALUE_CHANGE, {
                                'value': initial,
                                'owner': owner,
                                'priority': priority
                            })
                        except Exception as e:
                            self.logger.error(f"Error setting initial value on pin {pin}: {e}")
                            
                    # Notify listeners about setup update
                    self._notify_pin_event(pin, PinEventType.SETUP, setup_info)
                    return True
                
                # Case 2: Different mode, potential conflict
                elif not force and owner != current_owner and priority <= current_priority:
                    # Conflict that we can't resolve
                    self.logger.warning(
                        f"PIN CONFLICT: Pin {pin} mode conflict. "
                        f"Already configured as {current_mode} by {current_owner} "
                        f"with priority {current_priority}. "
                        f"Requested {mode} by {owner} with priority {priority}."
                    )
                    
                    # Notify listeners about conflict
                    self._notify_pin_event(pin, PinEventType.CONFLICT, {
                        'pin': pin,
                        'current_mode': current_mode,
                        'current_owner': current_owner,
                        'current_priority': current_priority,
                        'requested_mode': mode,
                        'requested_owner': owner,
                        'requested_priority': priority
                    })
                    return False
                else:
                    # We're forcing or have higher priority - release and reconfigure
                    self.logger.info(
                        f"Pin {pin} mode change: {current_mode} -> {mode} "
                        f"(Owner: {current_owner} -> {owner}, "
                        f"Priority: {current_priority} -> {priority})"
                    )
                    self.release_pin_sync(pin)
            
            # Initialize GPIO if needed
            init_gpio()
            
            # Setup pin with error handling
            try:
                handle = None
                
                # For output pins
                if mode == GPIO.OUT:
                    if initial is not None:
                        handle = GPIO.setup(pin, mode, initial=initial)
                        self._pin_values[pin] = initial
                    else:
                        handle = GPIO.setup(pin, mode)
                        # Default initial value is LOW
                        self._pin_values[pin] = GPIO.LOW
                # For input pins
                elif mode == GPIO.IN:
                    if pull_up_down is not None:
                        handle = GPIO.setup(pin, mode, pull_up_down=pull_up_down)
                    else:
                        handle = GPIO.setup(pin, mode)
                else:
                    handle = GPIO.setup(pin, mode)
                    
                # Track pin usage
                self._pins_in_use.add(pin)
                self._pin_modes[pin] = mode
                
                if owner:
                    self._pin_owners[pin] = owner
                    self._pin_priorities[pin] = priority
                
                # If we got a handle back (e.g., from lgpio), store it
                if handle is not None:
                    self._pin_handles[pin] = handle
                
                # Notify listeners about setup
                self._notify_pin_event(pin, PinEventType.SETUP, setup_info)
                
                self.logger.debug(
                    f"Pin {pin} set up as {'OUTPUT' if mode == GPIO.OUT else 'INPUT'} "
                    f"by {owner if owner else 'unknown'}"
                )
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to setup pin {pin}: {e}")
                return False
    
    async def setup_pin(self, pin: int, mode: int, pull_up_down: Optional[int] = None, 
                        initial: Optional[int] = None, owner: Optional[str] = None, 
                        priority: int = 0, force: bool = False) -> bool:
        """
        Async version of setup_pin_sync
        """
        if self._async_lock:
            async with self._async_lock:
                return self.setup_pin_sync(pin, mode, pull_up_down, initial, owner, priority, force)
        else:
            return self.setup_pin_sync(pin, mode, pull_up_down, initial, owner, priority, force)
    
    # ===== PIN VALUE METHODS =====
    
    def set_pin_value_sync(self, pin: int, value: int, owner: Optional[str] = None, 
                           priority: int = 0) -> bool:
        """
        Set a pin value with conflict handling
        
        Args:
            pin: GPIO pin number
            value: GPIO.HIGH or GPIO.LOW
            owner: Optional owner identifier for conflict resolution
            priority: Priority level (higher wins conflicts)
            
        Returns:
            bool: Success or failure
        """
        with self._lock:
            # Case 1: Pin not in use yet - auto setup
            if pin not in self._pins_in_use:
                self.logger.debug(f"Auto-setting up pin {pin} as output for value setting")
                success = self.setup_pin_sync(pin, GPIO.OUT, initial=value, 
                                           owner=owner, priority=priority)
                return success
            
            # Case 2: Pin is an input - can't set value
            if self._pin_modes.get(pin) == GPIO.IN:
                self.logger.warning(f"Cannot set value on pin {pin} configured as INPUT")
                return False
            
            # Case 3: Not the owner and not high enough priority
            current_owner = self._pin_owners.get(pin)
            current_priority = self._pin_priorities.get(pin, 0)
            
            if (current_owner and owner and 
                current_owner != owner and
                current_priority > priority):
                self.logger.warning(
                    f"Value set rejected: Pin {pin} owned by {current_owner} "
                    f"(priority {current_priority}) - requested by {owner} "
                    f"(priority {priority})"
                )
                return False
            
            # Case 4: We can set the value
            try:
                GPIO.output(pin, value)
                
                # Update tracking
                old_value = self._pin_values.get(pin)
                self._pin_values[pin] = value
                
                # Update owner if higher priority
                if owner and priority >= current_priority:
                    self._pin_owners[pin] = owner
                    self._pin_priorities[pin] = priority
                
                # Only notify if value actually changed
                if old_value != value:
                    self._notify_pin_event(pin, PinEventType.VALUE_CHANGE, {
                        'value': value,
                        'old_value': old_value,
                        'owner': owner,
                        'priority': priority
                    })
                
                return True
            except Exception as e:
                self.logger.error(f"Error setting value {value} on pin {pin}: {e}")
                return False
    
    async def set_pin_value(self, pin: int, value: int, owner: Optional[str] = None, 
                           priority: int = 0) -> bool:
        """
        Async version of set_pin_value_sync
        """
        if self._async_lock:
            async with self._async_lock:
                return self.set_pin_value_sync(pin, value, owner, priority)
        else:
            return self.set_pin_value_sync(pin, value, owner, priority)
    
    def get_pin_value_sync(self, pin: int) -> Optional[int]:
        """
        Get current value of a pin
        
        Args:
            pin: GPIO pin number
            
        Returns:
            int: GPIO.HIGH or GPIO.LOW, or None if error
        """
        with self._lock:
            # Check if pin is set up
            if pin not in self._pins_in_use:
                self.logger.warning(f"Attempting to read pin {pin} which is not set up")
                return None
                
            try:
                # For output pins, return tracked value
                if self._pin_modes.get(pin) == GPIO.OUT:
                    return self._pin_values.get(pin)
                
                # For input pins, read from GPIO
                value = GPIO.input(pin)
                # Update our tracking
                self._pin_values[pin] = value
                return value
            except Exception as e:
                self.logger.error(f"Error reading value from pin {pin}: {e}")
                return None
    
    async def get_pin_value(self, pin: int) -> Optional[int]:
        """
        Async version of get_pin_value_sync
        """
        if self._async_lock:
            async with self._async_lock:
                return self.get_pin_value_sync(pin)
        else:
            return self.get_pin_value_sync(pin)
    
    # ===== PIN RELEASE AND CLEANUP METHODS =====
    
    def release_pin_sync(self, pin: int, owner: Optional[str] = None, 
                       priority: int = 0) -> bool:
        """
        Release a pin with conflict handling
        
        Args:
            pin: GPIO pin number
            owner: Optional owner identifier for conflict resolution
            priority: Priority level (higher wins conflicts)
            
        Returns:
            bool: Success or failure
        """
        with self._lock:
            if pin not in self._pins_in_use:
                return True  # Already released
                
            # Check ownership
            current_owner = self._pin_owners.get(pin)
            current_priority = self._pin_priorities.get(pin, 0)
            
            if (current_owner and owner and 
                current_owner != owner and
                current_priority > priority):
                self.logger.warning(
                    f"Release rejected: Pin {pin} owned by {current_owner} "
                    f"(priority {current_priority}) - requested by {owner} "
                    f"(priority {priority})"
                )
                return False
            
            try:
                # If pin has a handle, use it for cleanup
                if pin in self._pin_handles:
                    handle = self._pin_handles.pop(pin)
                    # Handle-specific cleanup would go here
                    
                # Standard GPIO cleanup
                GPIO.cleanup(pin)
                
                # Remove from tracking
                self._pins_in_use.remove(pin)
                if pin in self._pin_modes:
                    del self._pin_modes[pin]
                if pin in self._pin_values:
                    del self._pin_values[pin]
                if pin in self._pin_owners:
                    del self._pin_owners[pin]
                if pin in self._pin_priorities:
                    del self._pin_priorities[pin]
                
                # Notify listeners
                self._notify_pin_event(pin, PinEventType.RELEASE, {
                    'owner': owner,
                    'priority': priority
                })
                
                self.logger.debug(f"Released pin {pin}")
                return True
            except Exception as e:
                self.logger.error(f"Error releasing pin {pin}: {e}")
                # Remove from tracking even if cleanup failed to avoid stale state
                if pin in self._pins_in_use:
                    self._pins_in_use.remove(pin)
                return False
    
    async def release_pin(self, pin: int, owner: Optional[str] = None, 
                        priority: int = 0) -> bool:
        """
        Async version of release_pin_sync
        """
        if self._async_lock:
            async with self._async_lock:
                return self.release_pin_sync(pin, owner, priority)
        else:
            return self.release_pin_sync(pin, owner, priority)
    
    def cleanup_all(self):
        """
        Clean up all pins managed by this instance
        """
        with self._lock:
            # Get a copy of the pins to clean up
            pins = list(self._pins_in_use)
            
            for pin in pins:
                try:
                    self.release_pin_sync(pin)
                except Exception as e:
                    self.logger.error(f"Error while cleaning up pin {pin}: {e}")
            
            # Global cleanup as a final step
            try:
                GPIO.cleanup()
            except Exception as e:
                self.logger.error(f"Error in global GPIO cleanup: {e}")
                
            # Clear all tracking
            self._pins_in_use.clear()
            self._pin_modes.clear()
            self._pin_values.clear()
            self._pin_owners.clear()
            self._pin_priorities.clear()
            self._pin_handles.clear()
            
            self.logger.info("All GPIO pins cleaned up")
    
    # ===== EVENT NOTIFICATION METHODS =====
    
    def register_pin_listener(self, pin: int, callback: Callable, 
                            event_types: Optional[List[str]] = None):
        """
        Register a callback for pin events
        
        Args:
            pin: GPIO pin number
            callback: Function to call when events occur
            event_types: List of event types to listen for (None for all)
        """
        with self._lock:
            if pin not in self._pin_listeners:
                self._pin_listeners[pin] = []
            
            # Store callback with event types
            self._pin_listeners[pin].append({
                'callback': callback,
                'event_types': event_types
            })
            
            # Call immediately with current state if pin is set up
            if pin in self._pins_in_use:
                try:
                    current_info = {
                        'value': self._pin_values.get(pin),
                        'mode': self._pin_modes.get(pin),
                        'owner': self._pin_owners.get(pin),
                        'priority': self._pin_priorities.get(pin, 0)
                    }
                    
                    if event_types is None or PinEventType.SETUP in event_types:
                        callback(pin, PinEventType.SETUP, current_info)
                except Exception as e:
                    self.logger.error(f"Error calling pin listener for pin {pin}: {e}")
    
    def unregister_pin_listener(self, pin: int, callback: Optional[Callable] = None):
        """
        Unregister a callback for pin events
        
        Args:
            pin: GPIO pin number
            callback: Function to unregister (None for all)
        """
        with self._lock:
            if pin not in self._pin_listeners:
                return
                
            if callback is None:
                # Remove all listeners for this pin
                del self._pin_listeners[pin]
            else:
                # Remove specific callback
                self._pin_listeners[pin] = [
                    listener for listener in self._pin_listeners[pin]
                    if listener['callback'] != callback
                ]
                
                # Clean up empty lists
                if not self._pin_listeners[pin]:
                    del self._pin_listeners[pin]
    
    def _notify_pin_event(self, pin: int, event_type: str, event_data: Dict[str, Any]):
        """
        Notify all listeners about a pin event
        
        Args:
            pin: GPIO pin number
            event_type: Type of event
            event_data: Event data dictionary
        """
        if pin not in self._pin_listeners:
            return
            
        for listener in self._pin_listeners[pin]:
            callback = listener['callback']
            event_types = listener['event_types']
            
            # Check if this listener cares about this event type
            if event_types is not None and event_type not in event_types:
                continue
                
            try:
                callback(pin, event_type, event_data)
            except Exception as e:
                self.logger.error(
                    f"Error in pin listener for pin {pin}, event {event_type}: {e}"
                )
    
    # ===== INFORMATION AND DIAGNOSTICS METHODS =====
    
    def get_pin_info(self, pin: int) -> Dict[str, Any]:
        """
        Get comprehensive information about a pin
        
        Args:
            pin: GPIO pin number
            
        Returns:
            dict: Pin information dictionary
        """
        with self._lock:
            return {
                'pin': pin,
                'in_use': pin in self._pins_in_use,
                'mode': self._pin_modes.get(pin),
                'value': self._pin_values.get(pin),
                'owner': self._pin_owners.get(pin),
                'priority': self._pin_priorities.get(pin, 0),
                'has_listeners': pin in self._pin_listeners,
                'listener_count': len(self._pin_listeners.get(pin, [])),
                'setup_history': [
                    setup for setup in self._pin_setups
                    if setup['pin'] == pin
                ]
            }
    
    def get_active_pins(self) -> List[int]:
        """Get a list of all active pins"""
        return list(self._pins_in_use)
    
    def is_pin_in_use(self, pin: int) -> bool:
        """Check if a pin is currently in use"""
        return pin in self._pins_in_use
    
    def get_pin_mode(self, pin: int) -> Optional[int]:
        """Get the current mode of a pin"""
        return self._pin_modes.get(pin)
    
    def get_pin_owner(self, pin: int) -> Optional[str]:
        """Get the current owner of a pin"""
        return self._pin_owners.get(pin)
    
    def get_setup_history(self, pin: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get setup history for a pin or all pins
        
        Args:
            pin: GPIO pin number or None for all pins
            
        Returns:
            list: List of setup history dictionaries
        """
        if pin is None:
            return self._pin_setups.copy()
        else:
            return [setup for setup in self._pin_setups if setup['pin'] == pin]
    
    # ===== GPIOZERO INTEGRATION METHODS =====
    
    def register_gpiozero_pin(self, pin_number: int, pin_obj: Any) -> bool:
        """
        Register a gpiozero pin object with the manager
        
        Args:
            pin_number: GPIO pin number
            pin_obj: gpiozero pin object
            
        Returns:
            bool: Success or failure
        """
        with self._lock:
            # If pin is already in use, release it first
            if pin_number in self._pins_in_use:
                self.release_pin_sync(pin_number)
                
            # Register the pin
            self._pins_in_use.add(pin_number)
            self._pin_objects[pin_number] = pin_obj
            
            # Try to determine the mode and value
            try:
                # gpiozero pins typically have a function and state method
                if hasattr(pin_obj, 'function'):
                    function = pin_obj.function()
                    if function == 'output':
                        self._pin_modes[pin_number] = GPIO.OUT
                    elif function == 'input':
                        self._pin_modes[pin_number] = GPIO.IN
                
                if hasattr(pin_obj, 'state'):
                    state = pin_obj.state()
                    self._pin_values[pin_number] = GPIO.HIGH if state else GPIO.LOW
            except:
                pass  # Ignore errors in introspection
                
            return True
    
    def release_gpiozero_pin(self, pin_number: int) -> bool:
        """
        Release a gpiozero pin
        
        Args:
            pin_number: GPIO pin number
            
        Returns:
            bool: Success or failure
        """
        with self._lock:
            if pin_number not in self._pin_objects:
                return True  # Already released
                
            pin_obj = self._pin_objects[pin_number]
            
            try:
                # Close the pin if it has a close method
                if hasattr(pin_obj, 'close'):
                    pin_obj.close()
                    
                # Remove from tracking
                if pin_number in self._pin_objects:
                    del self._pin_objects[pin_number]
                if pin_number in self._pins_in_use:
                    self._pins_in_use.remove(pin_number)
                if pin_number in self._pin_modes:
                    del self._pin_modes[pin_number]
                if pin_number in self._pin_values:
                    del self._pin_values[pin_number]
                if pin_number in self._pin_owners:
                    del self._pin_owners[pin_number]
                if pin_number in self._pin_priorities:
                    del self._pin_priorities[pin_number]
                    
                return True
                
            except Exception as e:
                self.logger.error(f"Error releasing gpiozero pin {pin_number}: {e}")
                # Remove from tracking even if cleanup failed
                if pin_number in self._pin_objects:
                    del self._pin_objects[pin_number]
                if pin_number in self._pins_in_use:
                    self._pins_in_use.remove(pin_number)
                return False

# ===== GPIOZERO FACTORY CLASSES =====

# This section will be included if gpiozero is available
try:
    from gpiozero.pins import Pin
    from gpiozero.pins.native import NativeFactory
    from gpiozero.pins.rpigpio import RPiGPIOFactory
    
    # We have gpiozero available, so we can create factory classes
    
    # ===== GPIOZERO INTEGRATION CLASSES =====

    class GPIOManagerPin(Pin):
        """Pin implementation that delegates to the GPIOManager"""
        
        def __init__(self, manager, number):
            super().__init__()
            self._manager = manager
            self._number = number
            self._function = None
            self._state = None
            self._pull = None
            self._initialized = False
            
        def close(self):
            """Close this pin and release all resources"""
            self._manager.release_pin_sync(self._number)
            self._initialized = False
            
        def output_with_state(self, state):
            """Set this pin's function to output and its state to state"""
            self._function = 'output'
            self._state = state
            self._manager.setup_pin_sync(
                self._number, GPIO.OUT, initial=GPIO.HIGH if state else GPIO.LOW
            )
            self._initialized = True
        
        def input_with_pull(self, pull):
            """Set this pin's function to input with the specified pull-up/down resistor"""
            self._function = 'input'
            self._pull = pull
            
            # Map the pull values
            pull_map = {
                'up': GPIO.PUD_UP,
                'down': GPIO.PUD_DOWN,
                None: None
            }
            
            self._manager.setup_pin_sync(
                self._number, GPIO.IN, pull_up_down=pull_map.get(pull)
            )
            self._initialized = True
        
        def function(self):
            """Return the pin's current function"""
            return self._function
        
        def state(self):
            """Return the pin's current state"""
            if self._function == 'input':
                # For input pins, read from GPIO
                value = self._manager.get_pin_value_sync(self._number)
                self._state = bool(value)
            return self._state

    class MixedPinFactory:
        """Factory that delegates to different pin factories based on pin needs"""
        
        def __init__(self, gpio_manager=None):
            self.gpio_manager = gpio_manager or GPIOManager()
            
            # Create underlying factories
            self.native_factory = NativeFactory()
            self.rpi_factory = RPiGPIOFactory()
            
            # Track which factory handles which pin
            self.pin_assignments = {}
            self.pins = {}
            self.pin_reservations = {}
        
        def pin(self, spec):
            """Get a pin implementation for the specified pin"""
            if spec in self.pins:
                return self.pins[spec]
                
            # Get the pin number
            pin_number = self._get_pin_number(spec)
                
            # Determine which factory should handle this pin
            factory_type = self.pin_assignments.get(spec, self.pin_assignments.get(pin_number, 'native'))
            
            # Create the pin using the appropriate factory or our GPIOManagerPin
            if factory_type == 'managed':
                # Use our custom pin implementation
                pin = GPIOManagerPin(self.gpio_manager, pin_number)
            elif factory_type == 'native':
                pin = self.native_factory.pin(spec)
            else:  # 'rpi'
                pin = self.rpi_factory.pin(spec)
                
            # Register this pin with the GPIO manager for tracking
            self.gpio_manager.register_gpiozero_pin(pin_number, pin)
            
            # Store for future reference
            self.pins[spec] = pin
            return pin
        
        def _get_pin_number(self, spec):
            """Convert a pin spec to a BCM pin number"""
            # Handle list of pins
            if isinstance(spec, list):
                # Return the first pin in the list
                if spec:
                    return self._get_pin_number(spec[0])
                else:
                    return 0  # Return default for empty list
                    
            # Handle other pin spec types
            if isinstance(spec, int):
                return spec
            elif str(spec).isdigit():
                return int(spec)
            elif str(spec).startswith('GPIO'):
                return int(str(spec)[4:])
            elif str(spec).startswith('BOARD'):
                # Simplified board to BCM mapping
                board_to_bcm = {
                    '3': 2, '5': 3, '7': 4, '8': 14, '10': 15,
                    '11': 17, '12': 18, '13': 27, '15': 22,
                    '16': 23, '18': 24, '19': 10, '21': 9,
                    '22': 25, '23': 11, '24': 8, '26': 7,
                    '29': 5, '31': 6, '32': 12, '33': 13,
                    '35': 19, '36': 16, '37': 26, '38': 20,
                    '40': 21
                }
                return board_to_bcm.get(str(spec)[5:], 0)
            return 0  # Default fallback
        
        def use_native_for(self, pin_spec):
            """Specify that a pin should use the NativeFactory"""
        
            if isinstance(pin_spec, list):
                for spec in pin_spec:
                    self.pin_assignments[spec] = 'native'
            else:
                
                self.pin_assignments[pin_spec] = 'native'
            
        def use_rpi_for(self, pin_spec):
            """Specify that a pin should use the RPiGPIOFactory"""
            if isinstance(pin_spec, list):
                for spec in pin_spec:
                    self.pin_assignments[spec] = 'rpi'
            else:
                
                self.pin_assignments[pin_spec] = 'rpi'
            
        def use_managed_for(self, pin_spec):
            """Specify that a pin should use our GPIOManagerPin"""
            self.pin_assignments[pin_spec] = 'managed'
        
        def close(self):
            """Close all pins and clean up"""
            # Copy the list of pins since we'll be modifying it
            for spec in list(self.pins.keys()):
                try:
                    pin = self.pins[spec]
                    pin.close()
                except Exception as e:
                    logger.error(f"Error closing pin {spec}: {e}")
            
            self.pins.clear()
            
            # Close the underlying factories
            try:
                self.native_factory.close()
            except Exception as e:
                logger.error(f"Error closing native factory: {e}")
                
            try:
                self.rpi_factory.close()
            except Exception as e:
                logger.error(f"Error closing RPi factory: {e}")
            
            # Clean up GPIO manager
            self.gpio_manager.cleanup_all()
        
        def reserve_pins(self, requester, pins):
            """
            Reserve pins for exclusive use by a requester
            
            Args:
                requester: The device reserving the pins
                pins: A single pin or a sequence of pins to reserve
            """
            # Handle single pin or sequence of pins
            if not isinstance(pins, (list, tuple)):
                pins = [pins]
            
            # Reserve each pin
            for pin in pins:
                # Store reservation
                if requester not in self.pin_reservations:
                    self.pin_reservations[requester] = set()
                self.pin_reservations[requester].add(pin)
                
                # Ensure the pin is created
                if pin not in self.pins:
                    self.pin(pin)
        
        def release_pins(self, requester, pins=None):
            """
            Release pins previously reserved by a requester
            
            Args:
                requester: The device releasing the pins
                pins: A single pin, a sequence of pins, or None for all pins
            """
            # If no pins specified, release all pins reserved by this requester
            if pins is None:
                if requester in self.pin_reservations:
                    pins = list(self.pin_reservations[requester])
                else:
                    return
            
            # Handle single pin
            if not isinstance(pins, (list, tuple)):
                pins = [pins]
            
            # Release each pin
            for pin in pins:
                try:
                    # Remove from reservations
                    if requester in self.pin_reservations:
                        self.pin_reservations[requester].discard(pin)
                    
                    # Close the pin if no other reservations
                    if self._count_reservations(pin) == 0 and pin in self.pins:
                        self.pins[pin].close()
                        del self.pins[pin]
                except Exception as e:
                    logger.error(f"Error releasing pin {pin}: {e}")
            
            # Clean up empty reservations
            if requester in self.pin_reservations and not self.pin_reservations[requester]:
                del self.pin_reservations[requester]
        
        def _count_reservations(self, pin):
            """Count how many reservations exist for a pin"""
            count = 0
            for requester, pins in self.pin_reservations.items():
                if pin in pins:
                    count += 1
            return count
        
        def all_pins(self):
            """Return a set containing all pin objects created by this factory"""
            return set(self.pins.values())

except ImportError:
        logger.error("Using mock GPIOManagerPin - hardware control disabled",exc_info=True)
        from unittest.mock import MagicMock
        # gpiozero is not available, so we'll just define stub classes
        class GPIOManagerPin(MagicMock):
            def __init__(self, gpio_manager=None, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.gpio_manager = gpio_manager or MagicMock()
            """Stub class when gpiozero is not available"""
            pass
        
        class MixedPinFactory(MagicMock):
            """Stub class when gpiozero is not available"""
            def __init__(self, gpio_manager=None, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.gpio_manager = gpio_manager or MagicMock()
            
            def close(self):
                self.gpio_manager.cleanup_all()
        class RPiGPIOFactory(MagicMock):
             def __init__(self, gpio_manager=None, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.gpio_manager = gpio_manager or MagicMock()
            
             def close(self):
                self.gpio_manager.cleanup_all()