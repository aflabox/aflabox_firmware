from utils.network_monitor import NetworkMonitor,datetime,time


def main():
    """Main function to demonstrate the NetworkMonitor class"""
    # Create an instance of NetworkMonitor
    monitor = NetworkMonitor()
    
    # Define callback for network changes
    def network_changed(signal_strength, internet_available, internet_quality):
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Display in macOS style format
        status = monitor.display_mac_style_status()
        print(f"[{timestamp}] {status}")
        
        # Display warnings if needed
        if signal_strength < 30:
            print("⚠️  Warning: Low WiFi signal strength")
        
        if not internet_available:
            print("⚠️  Warning: No internet connectivity")
        elif internet_quality < 30:
            print("⚠️  Warning: Poor internet quality")
    
    # Register the callback
    monitor.on_network_changed = network_changed
    
    try:
        # Start monitoring
        print(f"Starting network monitoring on {monitor.os_type}...")
        monitor.start_monitoring()
        
        # Keep the main program running
        print("Network monitor running. Press Ctrl+C to exit.")
        
        # If this is a console application, just wait for Ctrl+C
        while monitor.running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping network monitoring...")
    finally:
        # Clean up
        monitor.stop_monitoring()
        print("Network monitoring stopped.")


if __name__ == "__main__":
    main()