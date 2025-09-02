from utils.click_tracker import ClickTracker
import asyncio
from hardware.power import Powerpi
# if __name__ == "__main__":
#     tracker = ClickTracker(device_id="device_123")
#     tracker.save_threshold("click", 0.23)
#     tracker.save_threshold("click", 0.25)
#     print("Summary for 'click':", tracker.get_summary_details("click"))
#     tracker.cleanup()




async def main():
    power = Powerpi()

    # Simulate a read
    status = power.read_status()
    if status:
        print("Current Status:")
        for key, value in status.items():
            print(f"  {key}: {value}")

    # Check last 5 records (if any)
    records = power.get_last_n_records(5)
    print("\nLast 5 Records:")
    for record in records:
        print(record)

    # Start monitoring for a brief period (15 seconds) to test threading
    print("\nStarting monitor for 15 seconds...")
    loop = asyncio.get_running_loop()
    power.start_monitoring(loop)

    try:
        await asyncio.sleep(15)  # Let the monitor thread run for 15 seconds
    finally:
        power.stop_monitoring()

    # Check if records were inserted
    records = power.get_last_n_records(5)
    print("\nAfter Monitoring - Last 5 Records:")
    for record in records:
        print(record)

    power.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
