#!/usr/bin/env python3
import os
import asyncio
import gc
import time
import weakref
import logging
import signal
import sys
from utils.helpers import free_camera_resources,delete_all_screenshots
from typing import List, Dict, Set, Optional
from concurrent.futures import ThreadPoolExecutor
from utils.gpio_helper import GPIOManager,init_gpio
from collections import Counter

# Defer heavy imports and initialization until needed
# This significantly speeds up startup time
ENABLE_MEMORY_TRACKING = True  # Set to True only when debugging memory issues
ENABLE_BATTERY_MONITORING=False
logger = logging.getLogger()
scan_counter = Counter()

# Global flag to track shutdown state
_shutdown_requested = False
_shutdown_in_progress = False
gpio_manager = None

# Try importing GPIO with proper error handling
try:
    from RPi import GPIO
    IS_RPI = True
except ImportError:
    from hardware.simulation import MockRPiGPIO as GPIO
    IS_RPI = False


# Import essential services and components in stages
try:
    # First stage imports - essential for initialization
    from utils.config_manager import ConfigManager
    from utils.logger import get_logger
    from hardware.display import DashboardAnimation
    from utils.network_monitor import NetworkMonitor

    
    # Display splash screen as early as possible to give user feedback
    def show_splash_screen():
        splash = DashboardAnimation(gpio=gpio_manager)
        try:
            
            splash.show_splash_screen("Booting")
            
            if "linux" not in sys.platform:
                delete_all_screenshots()
            return splash
        except Exception as e:
            logger.error(f"Failed to show splash screen: {e}")
            return splash
    init_gpio()
    gpio_manager = GPIOManager()
    # Show splash immediately
    dashboard = show_splash_screen()
    
except ImportError as e:
    logger.critical(f"Failed to import essential modules: {e}")
    exit(1)


# Add this to your main function or where you set up your application
def setup_graceful_shutdown(rabbitmq_service):
    def signal_handler():
        # Cancel all running tasks properly
        for task in asyncio.all_tasks():
            task.cancel()
        
        # Close RabbitMQ connections properly
        asyncio.create_task(rabbitmq_service.close())
        
    # Register the handler for SIGINT (Ctrl+C)
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, signal_handler)
class LazyImporter:
    """Handles lazy imports to speed up startup"""
    _imports = {}
    
    @classmethod
    def get(cls, module_name):
        if module_name not in cls._imports:
            try:
                start_time = time.time()
                module = __import__(module_name, fromlist=['*'])
                load_time = time.time() - start_time
                if load_time > 0.1:  # Log slow imports
                    logger.debug(f"Imported {module_name} in {load_time:.3f}s")
                cls._imports[module_name] = module
            except ImportError as e:
                logger.error(f"Failed to import {module_name}: {e}")
                raise
        return cls._imports[module_name]

class TaskRegistry:
    """Class to keep track of all tasks to ensure proper cleanup"""
    def __init__(self):
        self.tasks: Set[asyncio.Task] = set()
        self._lock = asyncio.Lock()
        self._cleanup_done = asyncio.Event()
        self._cleanup_done.set()  # Initially set as "done"
        
    def register_task(self, task: asyncio.Task) -> asyncio.Task:
        """Register a task for later cleanup"""
        if task is None:
            return None
            
        self.tasks.add(task)
        task.add_done_callback(self._task_done_callback)
        return task
    
    def _task_done_callback(self, task):
        """Callback when a task is done to remove it from the registry"""
        self.tasks.discard(task)
        
        # Get task name for better logging
        task_name = task.get_name() if hasattr(task, 'get_name') else 'Unknown'
        
        # Check task state and log appropriately
        if task.cancelled():
            logger.debug(f"Task '{task_name}' was cancelled")
        elif task.exception():
            logger.error(f"Task '{task_name}' failed with exception: {task.exception()}")
    
    async def cancel_all(self):
        """Cancel all registered tasks with proper handling for Ctrl+C"""
        # Use lock to prevent concurrent cancellation
        async with self._lock:
            # Mark as in progress
            self._cleanup_done.clear()
            
            # Take a snapshot of current tasks
            tasks = list(self.tasks)
            if not tasks:
                self._cleanup_done.set()
                return
            
            logger.info(f"Cancelling {len(tasks)} tasks...")
            
            # Cancel all tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete with a shorter timeout
            try:
                # Use a shorter timeout to ensure shutdown proceeds
                done, pending = await asyncio.wait(tasks, timeout=5.0, return_when=asyncio.ALL_COMPLETED)
                
                if pending:
                    logger.warning(f"{len(pending)} tasks still pending after timeout")
                    
            except Exception as e:
                logger.error(f"Error waiting for tasks to cancel: {e}")
            
            # Clear task set
            self.tasks.clear()
            
            # Mark as complete
            self._cleanup_done.set()
    
    async def wait_for_cleanup(self, timeout=10.0):
        """Wait for cleanup to complete with timeout"""
        try:
            await asyncio.wait_for(self._cleanup_done.wait(), timeout)
            return True
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for task cleanup")
            return False

class ResourceManager:
    """Manages proper cleanup of system resources"""
    def __init__(self):
        self.resources = []
        self._lock = asyncio.Lock()
        self._cleanup_done = asyncio.Event()
        self._cleanup_done.set()  # Initially set as "done"
        
    def register(self, resource, cleanup_method=None):
        """Register a resource for cleanup"""
        if resource is None:
            return
        self.resources.append((resource, cleanup_method))
        
    async def cleanup_all(self):
        """Clean up all registered resources with improved Ctrl+C handling"""
        # Use lock to prevent concurrent cleanup
        async with self._lock:
            # Mark as in progress
            self._cleanup_done.clear()
            
            # Process resources in reverse order (LIFO)
            for resource, cleanup_method in reversed(self.resources):
                try:
                    if resource is None:
                        continue
                        
                    # Use a shorter timeout to prevent hanging during shutdown
                    if cleanup_method:
                        if asyncio.iscoroutinefunction(cleanup_method):
                            await asyncio.wait_for(cleanup_method(), timeout=2.0)
                        else:
                            cleanup_method()
                    elif hasattr(resource, 'close'):
                        if asyncio.iscoroutinefunction(resource.close):
                            await asyncio.wait_for(resource.close(), timeout=2.0)
                        else:
                            resource.close()
                    elif hasattr(resource, 'cleanup'):
                        if asyncio.iscoroutinefunction(resource.cleanup):
                            await asyncio.wait_for(resource.cleanup(), timeout=2.0)
                        else:
                            resource.cleanup()
                    elif hasattr(resource, 'stop'):
                        if asyncio.iscoroutinefunction(resource.stop):
                            await asyncio.wait_for(resource.stop(), timeout=2.0)
                        else:
                            resource.stop()
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout cleaning up resource: {resource.__class__.__name__}")
                except Exception as e:
                    logger.error(f"Error cleaning up resource {resource.__class__.__name__}: {e}")
            
            # Mark as complete
            self._cleanup_done.set()
    
    async def wait_for_cleanup(self, timeout=10.0):
        """Wait for cleanup to complete with timeout"""
        try:
            await asyncio.wait_for(self._cleanup_done.wait(), timeout)
            return True
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for resource cleanup")
            return False
def anyMessage(data):
    print(data)
    
class DeviceApplication:
    """Main application class with optimized startup and better Ctrl+C handling"""
    def __init__(self, config_path: str):
        self.logger = get_logger()
        self.task_registry = TaskRegistry()
        self.resource_manager = ResourceManager()
        self.config_path = config_path
        self.dashboard = dashboard  # Use the globally created dashboard
        self._shutdown_requested = False
        self._stop_event = asyncio.Event()
        
        # Start with minimal configuration
        try:
            start_time = time.time()
            self.config = ConfigManager(config_path)
            if not self.config.config:
                raise ValueError(f"Failed to load configuration from {config_path}")
            load_time = time.time() - start_time
            self.logger.debug(f"Loaded configuration in {load_time:.3f}s")
        except Exception as e:
            self.logger.critical(f"Failed to load configuration: {e}")
            raise
            
        # Initialize minimal components immediately
        self.resource_manager.register(self.dashboard)
        if self.dashboard:
            self.dashboard.addConfig(self.config.config)
            self.dashboard.update_status("Loading...")
        
        # Other components will be initialized on demand
        self.initialized = False
        self.components_initialized = asyncio.Event()
        
        # Schedule remaining initialization to run after application starts
        # This allows the UI to be responsive while slower components load
        asyncio.create_task(self._deferred_init())
        
    async def _deferred_init(self):
        """Initialize components in the background after startup"""
        try:
            # Initialize hardware components
            start_time = time.time()
            device_id = self.config.config.get('DEVICE_SETTINGS', 'device_id')
            
            # Update status
            if self.dashboard:
                self.dashboard.update_status("Wait...")
            
            # Import and initialize pin manager
            from utils.pin_manager import PinManager
            from constants.PinConfig import PinConfig
            self.pin_manager = PinManager(self.config.config)
            self.resource_manager.register(self.pin_manager)
            
            # Import and initialize buzzer
            from hardware.buzzer import BuzzerController
            buzzer_pin = self.pin_manager.get_pin(PinConfig.BUZZER)
            self.buzzer = BuzzerController(buzzer_pin,gpio=gpio_manager)
            self.resource_manager.register(self.buzzer)
            
            # Import and initialize button
            from hardware.button import Button
            from utils.click_tracker import ClickTracker
            self.click_tracker = ClickTracker(device_id=device_id)
            button_pin = self.pin_manager.get_pin(PinConfig.MAIN_BUTTON)
            self.button = Button(
                button_pin,
                debounce_time=0.08,
                click_threshold=0.25,
                long_press_threshold=1.2,
                gpio=gpio_manager
            )
            self.resource_manager.register(self.button)
            
            if self.dashboard:
                self.dashboard.update_status("Launching...")
            
            # Initialize services with proper resource management
            # Import services only when needed
            from services.websocket_service import WebSocketService
            from services.rabbitmq_service import RabbitMQService
            from services.battery_service import BatteryService
            from services.firmware import FirmwareUpdater
            from services.camera_scanner_service import CameraScannerService
            from utils.menu_handler import MenuHandler
            from services.test_retries import TestRetryWorker
            
            
            # ws_uri = self.config.config.get('WEBSOCKET', 'remote_uri')
            # self.websocket_service = WebSocketService(ws_uri, device_id)
            # self.resource_manager.register(self.websocket_service)
            self.network_monitor=NetworkMonitor()
            self.network_monitor.set_on_network_changed(dashboard.on_network_change)
            self.resource_manager.register(self.network_monitor)
            
            
            self.test_reuploader = TestRetryWorker(config=self.config.config)
            self.resource_manager.register(self.test_reuploader)
            
            self.camera_scanner = CameraScannerService(
                device_id=device_id,
                config=self.config.config,
                dashboard=weakref.proxy(self.dashboard),
                gpio=gpio_manager
            )
            self.resource_manager.register(self.camera_scanner)
            
            amq_url = self.config.config.get('RABBITMQ_QUEUE', 'amq_url')
            self.rabbitmq_service = RabbitMQService(amq_url, device_id, buzzer=self.buzzer)
             # Register event handlers
            self.rabbitmq_service.register_handler(
                "TEST_RESULTS", 
                self.camera_scanner.show_test_results
            )
            
            self.firmware_updater = FirmwareUpdater(config_path=self.config_path)
            self.resource_manager.register(self.firmware_updater)
            
            self.rabbitmq_service.add_counter(scan_counter)
            self.rabbitmq_service.register_handler("NEW_VERSION",self.config.update_version)
            self.rabbitmq_service.register_handler("DEFAULT",self.camera_scanner.show_test_results)
            self.rabbitmq_service.register_handler("SIMULATE_CAPTURE", lambda data: asyncio.create_task(self.camera_scanner.start()))
            self.rabbitmq_service.register_handler("UPDATE_FIRMWARE", lambda data: self.firmware_updater.run())
            
            self.resource_manager.register(self.rabbitmq_service)
            
            
            if ENABLE_BATTERY_MONITORING:
                self.battery_service = BatteryService(dashboard=weakref.proxy(self.dashboard),gpio=gpio_manager)
                self.battery_service.setLogger(self.logger)
                self.resource_manager.register(self.battery_service)
            
            
            
            
           
            
            
            # Initialize menu handler
            self.menu_handler = MenuHandler(self.click_tracker, weakref.proxy(self.dashboard))
            self.menu_handler.addScanner(self.camera_scanner,scan_counter)
            self.menu_handler.addUpdater(self.firmware_updater)
            
            # Initialize memory monitoring only if enabled
            if ENABLE_MEMORY_TRACKING:
                import tracemalloc
                tracemalloc.start(25)
                from utils.memory_monitor import MemoryMonitor
                self.memory_monitor = MemoryMonitor(interval=600, logger=self.logger)
            else:
                self.memory_monitor = None
                
            total_time = time.time() - start_time
            self.logger.info(f"Components initialized in {total_time:.3f}s")
            
            # Mark initialization as complete
            self.initialized = True
            self.components_initialized.set()
            
            # Show homescreen now that everything is loaded
            if self.dashboard:
                self.dashboard.show_homescreen()
            
        except Exception as e:
            self.logger.critical(f"Failed to initialize components: {e}", exc_info=True)
            if self.dashboard:
                self.dashboard.show_error("Startup failed","Status")
            # Re-raise to stop the application
            raise
    
    async def start_services(self, loop):
        """Start all services with proper error handling"""
        # Wait for initialization to complete
        if not self.initialized:
            if self.dashboard:
                self.dashboard.update_status("Starting Services...")
            await self.components_initialized.wait()
        
        try:
            # Add event loop to battery service
            if ENABLE_BATTERY_MONITORING:
                self.battery_service.addLoop(loop)
            
            # Start file uploads with proper error handling
            file_upload_task = self.task_registry.register_task(
                asyncio.create_task(self._safe_execute(
                    "camera_scanner.start_file_uploads",
                    self.camera_scanner.start_file_uploads()
                ))
            )
            if hasattr(file_upload_task, 'set_name'):
                file_upload_task.set_name("file_uploads")
            
            # Start test reuploader with proper error handling
            reupload_task = self.task_registry.register_task(
                asyncio.create_task(self._safe_execute(
                    "test_reuploader.start",
                    self.test_reuploader.start()
                ))
            )
            
            if hasattr(reupload_task, 'set_name'):
                reupload_task.set_name("test_reuploader")
            
            network_task = self.task_registry.register_task(
                asyncio.create_task(self._safe_execute(
                    "network_monitor",
                     self.network_monitor.monitor()
                ))
            )
            
            if hasattr(network_task, 'set_name'):
                network_task.set_name("network_monitor")
                
                
            # Start memory monitoring if enabled
            if self.memory_monitor:
                memory_task = await self.memory_monitor.start_monitoring()
                self.task_registry.register_task(memory_task)
                if hasattr(memory_task, 'set_name'):
                    memory_task.set_name("memory_monitor")
            
        except Exception as e:
            self.logger.error(f"Failed to start services: {e}", exc_info=True)
            raise
    
    async def _safe_execute(self, name, coro):
        """Safely execute a coroutine with error handling"""
        start_time = time.time()
        self.logger.info(f"Task '{name}' queued")
        
        try:
            result = await coro
            execution_time = time.time() - start_time
            
            # Only log longer operations
            if execution_time > 0.5:
                self.logger.debug(f"Task '{name}' completed in {execution_time:.3f}s")
                
            return result
            
        except asyncio.CancelledError:
            execution_time = time.time() - start_time
            self.logger.info(f"Task '{name}' cancelled after {execution_time:.3f}s")
            raise
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Error in '{name}' after {execution_time:.3f}s: {e}")
            return f"{name} failed: {e}"
    
    async def run(self):
        """Run the application with proper error handling and resource management"""
        loop = asyncio.get_running_loop()
        
        try:
            # Create a bounded queue with max size for battery service
            battery_queue = asyncio.Queue(maxsize=100)
            
            # Start core UI first so app appears responsive
            if self.dashboard:
                self.dashboard.update_status("Starting services...")
            
            # Run periodic garbage collection in background
            gc_task = self.task_registry.register_task(
                asyncio.create_task(self._periodic_gc(interval=600))  # Less frequent GC
            )
            if hasattr(gc_task, 'set_name'):
                gc_task.set_name("gc_task")
            
            # Start services (which waits for initialization to complete)
            await self.start_services(loop)
            
            # Register core tasks with descriptive names
            if self.dashboard:
                self.dashboard.update_status("Starting tasks...")
                
            # Wait for initialization before starting button and other tasks
            if not self.initialized:
                await self.components_initialized.wait()
                
            button_task = self.task_registry.register_task(asyncio.create_task(
                self._safe_execute("button.watch", self.button.watch(
                    single_click_callback=self.menu_handler.handle_short_press,
                    double_click_callback=self.menu_handler.handle_double_press,
                    long_press_callback=self.menu_handler.handle_long_press
                ))
            ))
            if hasattr(button_task, 'set_name'):
                button_task.set_name("button_watch")
                
            if ENABLE_BATTERY_MONITORING:
                battery_monitor_task = self.task_registry.register_task(asyncio.create_task(
                    self._safe_execute("battery_service.power_monitor", 
                                    self.battery_service.power_monitor(loop, battery_queue))
                ))
                if hasattr(battery_monitor_task, 'set_name'):
                    battery_monitor_task.set_name("battery_monitor")
                
                battery_led_task = self.task_registry.register_task(asyncio.create_task(
                    self._safe_execute("battery_service.power_led",
                                    self.battery_service.power_led())
                ))
                if hasattr(battery_led_task, 'set_name'):
                    battery_led_task.set_name("battery_led")
            
            rabbitmq_task = self.task_registry.register_task(asyncio.create_task(
                self._safe_execute("rabbitmq_service.start",
                                 self.rabbitmq_service.start())
            ))
            if hasattr(rabbitmq_task, 'set_name'):
                rabbitmq_task.set_name("rabbitmq")
            
            # Show homescreen to indicate successful startup
            if self.dashboard:
                self.dashboard.show_homescreen()
                
            # Create a shutdown monitor to watch for shutdown signals
            shutdown_task = asyncio.create_task(self._monitor_shutdown())
            
            # Wait for stop event
            await self._stop_event.wait()
            self.logger.info("Stop event received")
            
        except asyncio.CancelledError:
            self.logger.info("Application task cancelled")
            
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}", exc_info=True)
            
        finally:
            # Set shutdown flag to notify other tasks
            self._shutdown_requested = True
            
            # Cleanup phase
            await self._cleanup()
    
    async def _monitor_shutdown(self):
        """Monitor for shutdown conditions like Ctrl+C"""
        while not self._shutdown_requested and not _shutdown_requested:
            await asyncio.sleep(0.1)
        
        # If global shutdown was requested, trigger our own shutdown
        if _shutdown_requested and not self._shutdown_requested:
            self.logger.info("Global shutdown detected")
            self.request_shutdown()
            
    async def _cleanup(self):
        """Clean up all resources and tasks"""
        global _shutdown_in_progress
        _shutdown_in_progress = True
        
        try:
            self.logger.info("Shutting down services...")
            
            # Show shutdown screen
            if self.dashboard:
                self.dashboard.show_error("Shutting down...","Status")
            
            # Cancel all registered tasks
            await self.task_registry.cancel_all()
            
            # Stop memory monitor if enabled
            if hasattr(self, 'memory_monitor') and self.memory_monitor:
                self.memory_monitor.stop()
            
            # Clean up resources
            await self.resource_manager.cleanup_all()
            
            # Final GPIO cleanup
            if IS_RPI:
                try:
                    GPIO.cleanup()
                except RuntimeError as e:
                    if "set pin numbering mode" in str(e):
                        self.logger.warning("GPIO cleanup called without setting mode — skipping cleanup.")
                    else:
                        raise
            
            self.logger.info("Shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}", exc_info=True)
    
    def request_shutdown(self):
        """Signal the application to shut down"""
        if not self._shutdown_requested:
            self._shutdown_requested = True
            self._stop_event.set()
    
    async def _periodic_gc(self, interval=300):
        """Run garbage collection periodically"""
        import gc
        while not self._shutdown_requested:
            try:
                await asyncio.sleep(interval)
                start_time = time.time()
                collected = gc.collect()
                duration = time.time() - start_time
                if collected > 0:
                    self.logger.debug(f"GC collected {collected} objects in {duration:.3f}s")
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in periodic GC: {e}")
                await asyncio.sleep(interval)

# Better signal handling for Ctrl+C
def handle_signal(sig, frame):
    """Handle signals like SIGINT (Ctrl+C) and SIGTERM"""
    global _shutdown_requested
    
    # Only handle once
    if _shutdown_requested:
        return
        
    # Set global flag
    _shutdown_requested = True
    
    if _shutdown_in_progress:
        # If already shutting down, a second signal forces exit
        logger.critical("Forced exit requested")
        sys.exit(1)
    else:
        logger.info("Shutdown signal received, stopping application gracefully")

async def main():
    """Main entry point with faster startup and better Ctrl+C handling"""
    # Use absolute path to config to avoid path-related issues
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.abspath(os.path.join(script_dir, "../config/config.ini"))
    success = free_camera_resources()
    if not success:
        print("WARNING: Failed to free camera resources. Camera may not work properly.")
    # Record startup time
    start_time = time.time()
    
    # Create a cleanup event
    cleanup_event = asyncio.Event()
    app = None
    
    try:
        logger.info("Starting application...")
        
        # Create application - this will start UI immediately
        app = DeviceApplication(config_path)
        
        # Setup signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()
        
        # Run the application
        await app.run()
        
    except asyncio.CancelledError:
        logger.info("Main task cancelled")
    except Exception as e:
        logger.critical(f"Fatal error in main: {e}", exc_info=True)
    finally:
        # Log total runtime
        total_time = time.time() - start_time
        logger.info(f"Application lifecycle completed in {total_time:.3f}s")
        
        # Force exit to ensure complete termination
        if _shutdown_requested:
            sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers early
    signal.signal(signal.SIGINT, handle_signal)   # Ctrl+C
    signal.signal(signal.SIGTERM, handle_signal)  # Termination request
    
    
    
    # Set up a custom exception hook to catch unhandled exceptions
    def custom_except_hook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Don't show traceback for Ctrl+C
            
            logger.info("Application terminated by keyboard interrupt")
            # Force exit
            sys.exit(0)
        else:
            logger.critical("Unhandled exception", 
                           exc_info=(exc_type, exc_value, exc_traceback))
        # Call the original exception hook
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    
    # Install the custom exception hook
    sys.excepthook = custom_except_hook
    
    try:
        # Run the application
        if sys.version_info >= (3, 8):
            # For Python 3.8+
            asyncio.run(main(), debug=False)  # Debug mode can slow shutdown
        else:
            # For Python 3.7
            loop = asyncio.get_event_loop()
            try:
                loop.run_until_complete(main())
            except KeyboardInterrupt:
                # Handle Ctrl+C specially for older Python
                logger.info("Application terminated by keyboard interrupt")
                sys.exit(0)
            finally:
                # Always close the loop
                loop.close()
    except KeyboardInterrupt:
        # This provides a second layer of Ctrl+C handling
        logger.info("Application terminated by keyboard interrupt")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Ensure we really exit
        if _shutdown_requested:
            sys.exit(0)