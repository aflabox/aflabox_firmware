from utils.gpio_helper import GPIOManager,logger,asyncio,GPIO,sys
from utils.memory_monitor import MemoryMonitor
# Example usage in a main function
async def example_usage():
    # Get the GPIO manager instance
    gpio_manager = GPIOManager()
    
    # Setup a pin for output
    pin = 17  # Example pin
    success = await gpio_manager.setup_pin(pin, GPIO.OUT)
    if success:
        logger.info(f"Pin {pin} setup successful")
        
        # Set the pin high
        await gpio_manager.set_pin_value(pin, GPIO.HIGH)
        logger.info(f"Set pin {pin} to HIGH")
        
        # Wait a bit
        await asyncio.sleep(1)
        
        # Set the pin low
        await gpio_manager.set_pin_value(pin, GPIO.LOW)
        logger.info(f"Set pin {pin} to LOW")
        
        # Release the pin
        await gpio_manager.release_pin(pin)
        logger.info(f"Released pin {pin}")
    else:
        logger.error(f"Failed to setup pin {pin}")
    
    # Clean up all pins at the end
    gpio_manager.cleanup_all()


# Example usage
async def example_memory_usage():
    # Create a memory monitor instance
    monitor = MemoryMonitor(
        interval=10,  # Check every 10 seconds
        alert_threshold_mb=100,  # Alert if memory usage exceeds 100 MB
        enable_tracemalloc=True,  # Enable detailed tracking
        log_dir="./memory_logs"  # Save logs to this directory
    )
    
    # Start monitoring
    task = await monitor.start_monitoring()
    
    # Create some memory allocations to monitor
    big_list = []
    
    # Run for a while
    for i in range(5):
        # Allocate some memory
        big_list.append([0] * 1000000)  # Allocate about 8 MB each time
        
        # Take a manual snapshot
        monitor.log_snapshot(f"allocation_{i}")
        
        # Wait a bit
        await asyncio.sleep(15)
    
    # Stop monitoring
    monitor.stop()
    
    # Get a summary
    summary = monitor.get_summary()
    logger.info(f"Memory monitoring summary: {summary}")

if __name__ == "__main__":
    # Example of how to use the MemoryMonitor
    logger.info("Running MemoryMonitor example")
    
    try:
        # Run the async example
        asyncio.run(example_memory_usage())
        
        logger.info("Example completed successfully")
    except KeyboardInterrupt:
        logger.info("Example interrupted by user")
    except Exception as e:
        logger.error(f"Error in example: {e}")
        
        
# if __name__ == "__main__":
#     # Example of how to use the GPIOManager
#     logger.info("Running GPIOManager example")
    
#     try:
#         # Run the async example
#         if 'asyncio' in sys.modules:
#             asyncio.run(example_usage())
#         else:
#             logger.info("Asyncio not available, skipping example")
            
#         logger.info("Example completed successfully")
#     except KeyboardInterrupt:
#         logger.info("Example interrupted by user")
#     except Exception as e:
#         logger.error(f"Error in example: {e}")
#     finally:
#         # Ensure cleanup happens
#         GPIOManager().cleanup_all()
        