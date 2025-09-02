#!/usr/bin/env python3
import os
import asyncio
import gc
import tracemalloc
import time
import weakref
from typing import List, Dict, Set, Optional
from contextlib import asynccontextmanager
from utils.logger import get_logger
import numpy as np

# Memory monitoring setup
tracemalloc.start(25)  # Start memory monitoring with 25 frames depth


# Try importing GPIO with proper error handling
try:
    from RPi import GPIO
    IS_RPI = True
except ImportError:
    from hardware.simulation import MockRPiGPIO as GPIO
    IS_RPI = False
logging = get_logger()
# Import services and components with proper error handling
try:
    from services.websocket_service import WebSocketService
    from services.rabbitmq_service import RabbitMQService
    from services.battery_service import BatteryService
    from services.firmware import FirmwareUpdater
    from hardware.button import Button
    from hardware.display import DashboardAnimation
    from utils.config_manager import ConfigManager
    from utils.logger import get_logger
    from utils.menu_handler import MenuHandler
    from utils.pin_manager import PinManager
    from constants.PinConfig import PinConfig
    from services.camera_scanner_service import CameraScannerService
    from hardware.buzzer import BuzzerController
    from utils.click_tracker import ClickTracker
    from services.test_retries import TestRetryWorker
except ImportError as e:
    logging.critical(f"Failed to import required modules: {e}")
    exit(1)

class TaskRegistry:
    """Class to keep track of all tasks to ensure proper cleanup"""
    def __init__(self):
        self.tasks: Set[asyncio.Task] = set()
        self._cleanup_lock = asyncio.Lock()
        self._cleaned_up = False
        
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
            logging.debug(f"Task '{task_name}' was cancelled")
        elif task.exception():
            logging.error(f"Task '{task_name}' failed with exception: {task.exception()}")
        else:
            logging.debug(f"Task '{task_name}' completed successfully")
    
    async def cancel_all(self):
        """Cancel all registered tasks with proper locking to prevent concurrent cancellation"""
        async with self._cleanup_lock:
            # Check if already cleaned up
            if self._cleaned_up:
                logging.info("Tasks already cancelled, skipping")
                return
                
            # Mark as cleaned up
            self._cleaned_up = True
            
            # Get a snapshot of current tasks
            tasks = list(self.tasks)
            if not tasks:
                logging.info("No tasks to cancel")
                return
                
            # Log task cancellation in a cleaner format
            task_names = [task.get_name() if hasattr(task, 'get_name') else 'unnamed' for task in tasks]
            logging.info(f"Cancelling {len(tasks)} tasks: {', '.join(task_names)}")
            
            # Track task execution times for performance monitoring
            start_times = {task: time.time() for task in tasks}
            
            # First pass: request cancellation for all tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
            
            # Second pass: wait for tasks to complete with a timeout
            try:
                # Wait for tasks to respond to cancellation with a timeout
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=10.0  # Allow 10 seconds for tasks to cancel
                )
            except asyncio.TimeoutError:
                # Log but continue if some tasks don't respond to cancellation
                remaining_tasks = [t for t in tasks if not t.done()]
                remaining_names = [t.get_name() if hasattr(t, 'get_name') else 'unnamed' for t in remaining_tasks]
                logging.warning(f"Timeout waiting for {len(remaining_tasks)} tasks to cancel: {', '.join(remaining_names)}")
            
            # Log execution times in a readable format
            for task in tasks:
                if task.done():
                    name = task.get_name() if hasattr(task, 'get_name') else 'unnamed'
                    status = "cancelled" if task.cancelled() else "completed"
                    duration = time.time() - start_times[task]
                    logging.info(f"Task '{name}' {status} in {duration:.3f} seconds")
            
            # Clear the task set
            self.tasks.clear()

class MemoryMonitor:
    """Monitors memory usage and logs it periodically"""
    def __init__(self, interval: int = 60, logger=None):
        self.interval = interval
        self.running = False
        self._task = None
        self.logger = logger or logging.getLogger("memory_monitor")
        
    async def start_monitoring(self):
        """Start monitoring memory usage"""
        self.running = True
        self._task = asyncio.create_task(self._monitor())
        return self._task
        
    async def _monitor(self):
        """Monitor memory usage and log it"""
        while self.running:
            try:
                # Force garbage collection
                gc.collect()
                
                # Get memory snapshot
                current, peak = tracemalloc.get_traced_memory()
                
                # Log memory usage
                self.logger.info(f"Current memory usage: {current / 1024 / 1024:.2f} MB, "
                                f"Peak: {peak / 1024 / 1024:.2f} MB")
                
                # Get top memory consumers
                snapshot = tracemalloc.take_snapshot()
                top_stats = snapshot.statistics('lineno')
                
                self.logger.info("Top 5 memory consumers:")
                for stat in top_stats[:5]:
                    self.logger.info(f"{stat}")
                    
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in memory monitoring: {e}", exc_info=True)
                await asyncio.sleep(self.interval)
    
    def stop(self):
        """Stop memory monitoring"""
        self.running = False
        if self._task and not self._task.done():
            self._task.cancel()

class ResourceManager:
    """Manages proper cleanup of system resources"""
    def __init__(self):
        self.resources = []
        self._cleanup_lock = asyncio.Lock()
        self._cleaned_up = False
        
    def register(self, resource, cleanup_method=None):
        """Register a resource for cleanup"""
        # Don't register None resources
        if resource is None:
            return
            
        self.resources.append((resource, cleanup_method))
        
    async def cleanup_all(self):
        """Clean up all registered resources with proper locking to prevent double cleanup"""
        # Use a lock to prevent concurrent cleanup
        async with self._cleanup_lock:
            # Check if already cleaned up
            if self._cleaned_up:
                logging.info("Resources already cleaned up, skipping")
                return
                
            # Mark as cleaned up to prevent future calls
            self._cleaned_up = True
            
            # Process resources in reverse order (LIFO)
            for resource, cleanup_method in reversed(self.resources):
                try:
                    # Skip None resources
                    if resource is None:
                        continue
                        
                    logging.debug(f"Cleaning up resource: {resource.__class__.__name__}")
                    
                    if cleanup_method:
                        if asyncio.iscoroutinefunction(cleanup_method):
                            await asyncio.wait_for(cleanup_method(), timeout=5.0)
                        else:
                            cleanup_method()
                    elif hasattr(resource, 'close'):
                        if asyncio.iscoroutinefunction(resource.close):
                            await asyncio.wait_for(resource.close(), timeout=5.0)
                        else:
                            resource.close()
                    elif hasattr(resource, 'cleanup'):
                        if asyncio.iscoroutinefunction(resource.cleanup):
                            await asyncio.wait_for(resource.cleanup(), timeout=5.0)
                        else:
                            resource.cleanup()
                    elif hasattr(resource, 'stop'):
                        if asyncio.iscoroutinefunction(resource.stop):
                            await asyncio.wait_for(resource.stop(), timeout=5.0)
                        else:
                            resource.stop()
                except asyncio.TimeoutError:
                    logging.error(f"Timeout while cleaning up resource: {resource.__class__.__name__}")
                except Exception as e:
                    logging.error(f"Error cleaning up resource {resource.__class__.__name__}: {e}", exc_info=True)

# Retry decorator with backoff
def async_retry(max_retries=3, backoff_factor=2, initial_delay=1):
    """Retry decorator with exponential backoff for async functions"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            retry_count = 0
            delay = initial_delay
            
            while True:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    retry_count += 1
                    if retry_count > max_retries:
                        logging.error(f"Max retries ({max_retries}) reached for {func.__name__}", exc_info=True)
                        raise
                    
                    logging.warning(f"Retrying {func.__name__} after error: {e}, "
                                   f"retry {retry_count}/{max_retries}, "
                                   f"waiting {delay}s")
                    await asyncio.sleep(delay)
                    delay *= backoff_factor
        
        return wrapper
    return decorator

# Main application class
class DeviceApplication:
    """Main application class with improved error handling and resource management"""
    def __init__(self, config_path: str):
        self.logger = get_logger()
        self.task_registry = TaskRegistry()
        self.resource_manager = ResourceManager()
        self.memory_monitor = MemoryMonitor(interval=600, logger=self.logger)  # Check memory every 10 minutes
        self.config_path=config_path
        # Load configuration with proper error handling
        try:
            self.config = ConfigManager(config_path)
            if not self.config.config:
                raise ValueError(f"Failed to load configuration from {config_path}")
        except Exception as e:
            self.logger.critical(f"Failed to load configuration: {e}", exc_info=True)
            raise
            
        # Initialize components with proper resource management
        self.dashboard = None
        self.pin_manager = None
        self.buzzer = None
        self.click_tracker = None
        self.button = None
        self.websocket_service = None
        self.test_reuploader = None
        self.rabbitmq_service = None
        self.firmware_updater = None
        self.battery_service = None
        self.camera_scanner = None
        self.menu_handler = None
        
        # Initialize all components
        self._init_components()
        
    def _init_components(self):
        """Initialize all application components with proper error handling"""
        try:
            # Initialize hardware components
            self.dashboard = DashboardAnimation()
            self.resource_manager.register(self.dashboard)
            
            self.dashboard.addConfig(self.config.config)
            
            self.pin_manager = PinManager(self.config.config)
            self.resource_manager.register(self.pin_manager)
            
            buzzer_pin = self.pin_manager.get_pin(PinConfig.BUZZER)
            self.buzzer = BuzzerController(buzzer_pin)
            self.resource_manager.register(self.buzzer)
            
            device_id = self.config.config.get('DEVICE_SETTINGS', 'device_id')
            self.click_tracker = ClickTracker(device_id=device_id)
            
            button_pin = self.pin_manager.get_pin(PinConfig.MAIN_BUTTON)
            self.button = Button(
                button_pin,
                debounce_time=0.08,
                click_threshold=0.25,
                long_press_threshold=1.2
            )
            self.resource_manager.register(self.button)
            
            # Initialize services with proper resource management
            ws_uri = self.config.config.get('WEBSOCKET', 'remote_uri')
            self.websocket_service = WebSocketService(ws_uri, device_id)
            self.resource_manager.register(self.websocket_service)
            
            self.test_reuploader = TestRetryWorker(config=self.config.config)
            self.resource_manager.register(self.test_reuploader)
            
            amq_url = self.config.config.get('RABBITMQ_QUEUE', 'amq_url')
            self.rabbitmq_service = RabbitMQService(amq_url, device_id, buzzer=self.buzzer)
            self.resource_manager.register(self.rabbitmq_service)
            
            self.firmware_updater = FirmwareUpdater(config_path=self.config_path)
            self.resource_manager.register(self.firmware_updater)
            
            self.battery_service = BatteryService(dashboard=weakref.proxy(self.dashboard))
            self.battery_service.setLogger(self.logger)
            self.resource_manager.register(self.battery_service)
            
            self.camera_scanner = CameraScannerService(
                device_id=device_id,
                config=self.config.config,
                dashboard=weakref.proxy(self.dashboard)
            )
            self.resource_manager.register(self.camera_scanner)
            
            # Register event handlers
            self.rabbitmq_service.register_handler(
                "TEST_RESULTS", 
                self.camera_scanner.show_test_results
            )
            
            # Initialize menu handler
            self.menu_handler = MenuHandler(self.click_tracker, weakref.proxy(self.dashboard))
            self.menu_handler.addScanner(self.camera_scanner)
            self.menu_handler.addUpdater(self.firmware_updater)
            
            # Show initial screen
            self.dashboard.show_homescreen()
            
        except Exception as e:
            self.logger.critical(f"Failed to initialize components: {e}", exc_info=True)
            raise
    
    @async_retry(max_retries=3)
    async def start_services(self, loop):
        """Start all services with proper error handling and retries"""
        try:
            # Add event loop to battery service
            self.battery_service.addLoop(loop)
            
            # Start file uploads with proper error handling
            self.task_registry.register_task(
                asyncio.create_task(self._safe_execute(
                    "camera_scanner.start_file_uploads",
                    self.camera_scanner.start_file_uploads()
                ))
            )
            
            # Start test reuploader with proper error handling
            self.task_registry.register_task(
                asyncio.create_task(self._safe_execute(
                    "test_reuploader.start",
                    self.test_reuploader.start()
                ))
            )
            
            # Start memory monitoring
            self.task_registry.register_task(
                await self.memory_monitor.start_monitoring()
            )
            
            # Show initial screen
            self.dashboard.show_homescreen()
            
            # Note: Additional services will be started in run()
            
        except Exception as e:
            self.logger.error(f"Failed to start services: {e}", exc_info=True)
            raise
    
    async def _safe_execute(self, name, coro):
        """Safely execute a coroutine with error handling and execution time tracking"""
        start_time = time.time()
        
        try:
            result = await coro
            execution_time = time.time() - start_time
            
            # Only log longer operations to avoid log spam
            if execution_time > 0.5:
                self.logger.debug(f"Task '{name}' completed successfully in {execution_time:.3f} seconds")
                
            return result
            
        except asyncio.CancelledError:
            execution_time = time.time() - start_time
            self.logger.info(f"Task '{name}' was cancelled after {execution_time:.3f} seconds")
            raise
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(
                f"Error in '{name}' after {execution_time:.3f} seconds: {e}",
                exc_info=True
            )
            return f"{name} failed: {e}"
    
    async def run(self):
        """Run the application with proper error handling and resource management"""
        # Create a stop event for controlled shutdown
        self._stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        
        # Create a bounded queue with max size
        battery_queue = asyncio.Queue(maxsize=100)
        
        try:
            # Start all services first
            await self.start_services(loop)
            
            # Run periodic garbage collection
            gc_task = self.task_registry.register_task(
                asyncio.create_task(self._periodic_gc())
            )
            gc_task.set_name("periodic_gc")
            
            # Register core tasks with descriptive names
            button_task = self.task_registry.register_task(asyncio.create_task(
                self._safe_execute("button.watch", self.button.watch(
                    single_click_callback=self.menu_handler.handle_short_press,
                    double_click_callback=self.menu_handler.handle_double_press,
                    long_press_callback=self.menu_handler.handle_long_press
                ))
            ))
            button_task.set_name("button_watch")
            
            battery_monitor_task = self.task_registry.register_task(asyncio.create_task(
                self._safe_execute("battery_service.power_monitor", 
                                  self.battery_service.power_monitor(loop, battery_queue))
            ))
            battery_monitor_task.set_name("battery_power_monitor")
            
            battery_led_task = self.task_registry.register_task(asyncio.create_task(
                self._safe_execute("battery_service.power_led",
                                  self.battery_service.power_led())
            ))
            battery_led_task.set_name("battery_power_led")
            
            rabbitmq_task = self.task_registry.register_task(asyncio.create_task(
                self._safe_execute("rabbitmq_service.start",
                                  self.rabbitmq_service.start())
            ))
            rabbitmq_task.set_name("rabbitmq_service")
            
            # Create a single waiting task for shutdown signal
            # This avoids problems with waiting on multiple tasks directly
            await self._stop_event.wait()
            self.logger.info("Stop event received, initiating shutdown")
            
        except asyncio.CancelledError:
            self.logger.info("Application task cancelled")
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}", exc_info=True)
        finally:
            # Cleanup phase - stop all services in reverse order with proper timeouts
            try:
                self.logger.info("Shutting down services...")
                
                # Use asyncio.shield to protect the cleanup process from cancellation
                await asyncio.shield(self._perform_cleanup())
                
                self.logger.info("Shutdown complete")
                
            except Exception as e:
                self.logger.error(f"Error during shutdown: {e}", exc_info=True)
    
    async def _perform_cleanup(self):
        """Perform cleanup operations with proper timeouts"""
        try:
            # First stop the memory monitor
            if hasattr(self, 'memory_monitor'):
                self.memory_monitor.stop()
            
            # Cancel all registered tasks with timeout
            await asyncio.wait_for(
                self.task_registry.cancel_all(),
                timeout=15.0
            )
            
            # Clean up resources with timeout
            await asyncio.wait_for(
                self.resource_manager.cleanup_all(),
                timeout=15.0
            )
            
            # Final GPIO cleanup
            if IS_RPI:
                try:
                    GPIO.cleanup()
                except RuntimeError as e:
                    if "set pin numbering mode" in str(e):
                        self.logger.warning("GPIO cleanup called without setting mode — skipping cleanup.")
                    else:
                        raise
        except asyncio.TimeoutError:
            self.logger.error("Timeout during cleanup operations")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}", exc_info=True)
    
    def request_shutdown(self):
        """Signal the application to shut down"""
        if hasattr(self, '_stop_event'):
            self._stop_event.set()
    
    async def _periodic_gc(self, interval=300):
        """Run garbage collection periodically"""
        while True:
            try:
                await asyncio.sleep(interval)
                
                # Log memory before GC
                current_before, peak_before = tracemalloc.get_traced_memory()
                self.logger.debug(f"Memory before GC: {current_before / 1024 / 1024:.2f} MB")
                
                # Run garbage collection
                collected = gc.collect()
                
                # Log memory after GC
                current_after, peak_after = tracemalloc.get_traced_memory()
                self.logger.info(f"GC collected {collected} objects. "
                               f"Memory: {current_after / 1024 / 1024:.2f} MB "
                               f"(freed: {(current_before - current_after) / 1024 / 1024:.2f} MB)")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in periodic GC: {e}", exc_info=True)
                await asyncio.sleep(interval)

async def main():
    """Main entry point with proper error handling"""
    # Use absolute path to config to avoid path-related issues
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.abspath(os.path.join(script_dir, "../config/config.ini"))
    
    # Create a cleanup completion event
    cleanup_event = asyncio.Event()
    app = None
    
    try:
        # Create application
        app = DeviceApplication(config_path)
        
        # Setup signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()
        
        # Use a more reliable way to handle shutdown signals
        for signal_name in ('SIGINT', 'SIGTERM'):
            try:
                # Create a lambda that captures the current app variable
                loop.add_signal_handler(
                    getattr(signal, signal_name),
                    lambda app=app: asyncio.create_task(graceful_shutdown(app, cleanup_event))
                )
            except (NotImplementedError, AttributeError):
                # Windows doesn't support POSIX signals
                pass
        
        # Run the application
        await app.run()
        
    except asyncio.CancelledError:
        # Handle cancellation gracefully
        logging.info("Main task cancelled")
        if app:
            # Wait for cleanup to complete if it's in progress
            await graceful_shutdown(app, cleanup_event)
            await cleanup_event.wait()
    except Exception as e:
        logging.critical(f"Fatal error in main: {e}", exc_info=True)
        # Attempt cleanup even after fatal error
        if app:
            try:
                await app.task_registry.cancel_all()
                await app.resource_manager.cleanup_all()
            except Exception as cleanup_err:
                logging.error(f"Error during emergency cleanup: {cleanup_err}", exc_info=True)
        sys.exit(1)

async def graceful_shutdown(app, cleanup_event=None):
    """Improved graceful shutdown handler"""
    if not app:
        return
        
    logging.info("Graceful shutdown initiated")
    try:
        # Cancel all tasks first
        await app.task_registry.cancel_all()
        
        # Then clean up resources
        await app.resource_manager.cleanup_all()
        
        logging.info("Graceful shutdown completed")
    except Exception as e:
        logging.error(f"Error during graceful shutdown: {e}", exc_info=True)
    finally:
        # Signal that cleanup is done
        if cleanup_event:
            cleanup_event.set()

async def shutdown(app):
    """Graceful shutdown handler"""
    logging.info("Shutdown signal received")
    try:
        # Cancel all tasks but don't stop the loop directly
        await app.task_registry.cancel_all()
        # Signal main to exit instead of stopping the loop directly
        asyncio.current_task().cancel()
    except Exception as e:
        logging.error(f"Error during shutdown: {e}", exc_info=True)

if __name__ == "__main__":
    import sys
    import signal
    
    # Set up a custom exception hook to catch unhandled exceptions
    def custom_except_hook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Don't log stack trace for keyboard interrupts
            logging.info("Application terminated by keyboard interrupt")
        else:
            # Log the exception with traceback for other exceptions
            logging.critical("Unhandled exception", 
                            exc_info=(exc_type, exc_value, exc_traceback))
        # Call the original exception handler
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    
    # Install the custom exception hook
    sys.excepthook = custom_except_hook
    
    try:
        # Use a policy that properly handles task cancellation during shutdown
        # This is important for fixing the "Event loop stopped before Future completed" error
        if sys.version_info >= (3, 8):
            asyncio.run(main(), debug=True)
        else:
            # For Python 3.7 and earlier
            loop = asyncio.get_event_loop()
            loop.set_debug(True)
            try:
                loop.run_until_complete(main())
            finally:
                try:
                    # Cancel all tasks
                    tasks = asyncio.all_tasks(loop=loop)
                    for task in tasks:
                        task.cancel()
                    
                    # Wait for tasks to respond to cancellation
                    if tasks:
                        loop.run_until_complete(
                            asyncio.gather(*tasks, return_exceptions=True)
                        )
                finally:
                    loop.close()
    except KeyboardInterrupt:
        # This is handled by the exception hook, so no need to do anything here
        pass
    except asyncio.CancelledError:
        # This is expected during shutdown
        logging.info("Main task cancelled during shutdown")
    except Exception as e:
        logging.critical(f"Unhandled exception in main: {e}", exc_info=True)
        sys.exit(1)