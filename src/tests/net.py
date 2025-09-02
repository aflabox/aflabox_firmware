from utils.internet_monitor import InternetMonitor

if __name__ == "__main__":
    import argparse
    monitor = InternetMonitor()

    parser = argparse.ArgumentParser(description="Internet connection quality monitor")
    parser.add_argument("--mode", choices=["minute", "hour", "continuous"], default="continuous", 
                      help="Run mode: single minute check, single hour check, or continuous monitoring")
    args = parser.parse_args()

    if args.mode == "minute":
        monitor.every_minute_check()
    elif args.mode == "hour":
        monitor.every_hour_full_check()
    elif args.mode == "continuous":
        try:
            monitor.monitor_loop()
        except KeyboardInterrupt:
            print("Monitoring stopped")
    
    # Show current status
    combined_score = monitor.get_combined_score()
    print(f"📊 Combined Internet Quality Score: {combined_score:.1f}%")
    
    last = monitor.get_last_known(30)
    if last:
        # Adjust display based on connection type
        is_hotspot = last.get("is_hotspot", False)
        connection_type = "📱 Mobile Hotspot" if is_hotspot else "🔵 Normal WiFi"
        
        # Get stability assessment
        stability = last.get("stability_score", monitor.estimate_stability())
        stability_desc = "Stable" if stability > 70 else "Variable" if stability > 40 else "Unstable"
        
        # Score and quality assessment based on connection type
        score = last['strength_score']
        
        if is_hotspot:
            # Hotspot quality scale
            if score >= 60:
                quality = "Excellent for hotspot"
            elif score >= 45:
                quality = "Good for hotspot"
            elif score >= 30:
                quality = "Fair for hotspot"
            else:
                quality = "Poor connection"
                
            print(f"📊 Current Status: {score:.1f}% ({connection_type}, {stability_desc}, {quality})")
        else:
            # WiFi quality scale - adjusted to be more balanced
            if score >= 75:
                quality = "Excellent"
            elif score >= 60:
                quality = "Good"
            elif score >= 50:
                quality = "Fair"
            else:
                quality = "Needs improvement"
                
            print(f"📊 Current Status: {score:.1f}% ({connection_type}, {stability_desc}, {quality})")
            
            # Add actionable advice for WiFi improvements if score is below threshold
            if score < 60:
                print("\nWiFi Improvement Tips:")
                if signal_strength := last.get('signal_strength', None):
                    if signal_strength < -70:
                        print("- Move closer to your router or reduce physical barriers")
                if stability < 50:
                    print("- Check for interference from other devices or networks")
                if ping := last.get('ping', None):
                    if ping > 80:
                        print("- Your connection has high latency - try resetting your router")
                if packet_loss := last.get('packet_loss', None):
                    if packet_loss > 1:
                        print(f"- Packet loss detected ({packet_loss:.1f}%) - check for network congestion")