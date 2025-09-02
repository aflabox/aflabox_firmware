import os,asyncio
import time
import threading
import subprocess
from datetime import datetime

class NetworkMonitor:
    """
    A comprehensive network monitoring class that tracks WiFi signal strength
    and internet connectivity on both macOS and Linux systems.
    
    This class uses system-level notifications and events rather than polling
    to efficiently monitor network status changes.
    """
    
    def __init__(self):
        """Initialize the NetworkMonitor"""
        self.os_type = os.uname().sysname
        self.running = False
        self.current_signal_strength = 0
        self.internet_available = False
        self.internet_quality = 0
        self.last_update_time = None
        self.history = []  # Store historical data
        self.max_history = 100  # Maximum history entries
        self.handler=None
        
        # Set default callback (can be overridden)
        self.on_network_changed = self._default_network_callback
    def set_on_network_changed(self,cb):
        self.on_network_changed = cb
    def _default_network_callback(self, signal_strength, internet_available, internet_quality):
        """Default callback when network status changes"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if internet_available:
            print(f"[{timestamp}] WiFi: {signal_strength}% | Internet: ✓ ({internet_quality}%)")
        else:
            print(f"[{timestamp}] WiFi: {signal_strength}% | Internet: ✗")
    
    def _run_command(self, command):
        """Run a shell command and return its output"""
        try:
            result = subprocess.check_output(command, shell=True, text=True).strip()
            return result
        except subprocess.CalledProcessError:
            return ""
        except Exception as e:
            print(f"Error running command '{command}': {str(e)}")
            return ""
    
    def get_wifi_signal_strength(self):
        """
        Get the current WiFi signal strength as a percentage.
        
        Returns:
            int: Signal strength as a percentage (0-100%)
        """
        if self.os_type == "Darwin":  # macOS
            # Get both RSSI and noise values on macOS
            rssi_output = self._run_command("/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -I | grep 'agrCtlRSSI' | awk '{print $2}'")
            noise_output = self._run_command("/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -I | grep 'agrCtlNoise' | awk '{print $2}'")
            
            try:
                rssi = int(rssi_output)
                noise = int(noise_output)
                
                # Calculate SNR (Signal-to-Noise Ratio)
                snr = rssi - noise
                
                # Calibrated to show full bars (100%) at SNR of 20 or higher
                if snr >= 20:
                    signal_strength = 100
                elif snr <= 5:  # Very poor SNR
                    signal_strength = 0
                else:
                    # Linear scaling between SNR 5 (0%) and SNR 20 (100%)
                    signal_strength = (snr - 5) * (100 / 15)
                
                return int(signal_strength)
            except (ValueError, TypeError):
                # Fall back to RSSI-only calculation
                pass
        
        # For Linux or fallback for macOS
        try:
            if self.os_type == "Darwin":
                wifi_output = rssi_output if 'rssi_output' in locals() else self._run_command("/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -I | grep 'agrCtlRSSI' | awk '{print $2}'")
            else:
                # Try different Linux commands depending on what's available
                wifi_output = self._run_command("iwconfig 2>/dev/null | grep -i --color 'signal level' | awk '{print $4}' | cut -d'=' -f2")
                if not wifi_output:
                    wifi_output = self._run_command("nmcli -f SIGNAL dev wifi | grep -v SIGNAL | sort -nr | head -1")
            
            rssi = int(wifi_output)
            
            # Adjust RSSI thresholds for more accurate percentage
            if rssi >= -65:  # Excellent signal, full bars
                signal_strength = 100
            elif rssi <= -90:  # Very poor signal
                signal_strength = 0
            else:
                # Linear scaling between -90 dBm (0%) and -65 dBm (100%)
                signal_strength = (rssi + 90) * 4  # 25 dBm range / 100% = 4
            
            return max(0, min(100, int(signal_strength)))
        except (ValueError, TypeError):
            return 50  # Default to 50% if an error occurs
    
    def check_internet_connectivity(self):
        """
        Check if internet is available and measure connection quality by pinging reliable servers.
        
        Returns:
            tuple: (bool, int) - (is_available, quality_percentage)
            where quality_percentage is 0-100 based on latency and packet loss
        """
        try:
            # Try multiple reliable servers
            servers = ["1.1.1.1", "8.8.8.8", "9.9.9.9"]
            best_latency = float('inf')
            packet_loss = 100  # Start with 100% loss
            
            for server in servers:
                if self.os_type == "Darwin":
                    ping_result = self._run_command(f"ping -c 3 -q {server} 2>/dev/null")
                else:
                    ping_result = self._run_command(f"ping -c 3 -q {server} 2>/dev/null")
                
                # Check if we got any response
                if ping_result and "min/avg/max" in ping_result:
                    # Extract latency stats
                    try:
                        # Look for the line with min/avg/max round-trip times
                        for line in ping_result.splitlines():
                            if "min/avg/max" in line:
                                # Extract just the avg value
                                stats_part = line.split("=")[1].strip()
                                values = stats_part.split("/")
                                avg_latency = float(values[1])  # avg is the second value
                                
                                if avg_latency < best_latency:
                                    best_latency = avg_latency
                        
                        # Look for packet loss percentage
                        for line in ping_result.splitlines():
                            if "packet loss" in line:
                                loss_part = line.split("%")[0].strip()
                                current_loss = int(loss_part.split()[-1])
                                packet_loss = min(packet_loss, current_loss)
                    except (ValueError, IndexError):
                        continue
            
            # Calculate internet quality percentage based on latency and packet loss
            is_available = best_latency != float('inf')
            
            if not is_available:
                return False, 0
            
            # Convert latency to a percentage (lower is better)
            # 0-20ms: 100%, 150ms+: 0%
            latency_score = max(0, min(100, 100 - (best_latency - 20) * (100 / 130)))
            
            # Convert packet loss to a percentage (lower is better)
            packet_score = 100 - packet_loss
            
            # Combine scores (weighing latency more)
            quality_percentage = int((latency_score * 0.7) + (packet_score * 0.3))
            
            return True, quality_percentage
        except Exception as e:
            return False, 0
    
    def update_network_status(self):
        """Update both WiFi signal strength and internet connectivity status"""
        # Update values
        old_strength = self.current_signal_strength
        old_internet = self.internet_available
        old_quality = self.internet_quality
        
        self.current_signal_strength = self.get_wifi_signal_strength()
        self.internet_available, self.internet_quality = self.check_internet_connectivity()
        self.last_update_time = datetime.now()
        
        # Add to history
        self.history.append({
            'timestamp': self.last_update_time,
            'signal_strength': self.current_signal_strength,
            'internet_available': self.internet_available,
            'internet_quality': self.internet_quality
        })
        
        # Trim history if needed
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        
        # Call handler only if values changed or if it's been over 60 seconds
        if (old_strength != self.current_signal_strength or 
            old_internet != self.internet_available or
            abs(old_quality - self.internet_quality) > 5 or
            (len(self.history) > 1 and 
             (self.last_update_time - self.history[-2]['timestamp']).total_seconds() > 60)):
            
            if self.on_network_changed:
                self.on_network_changed(self.current_signal_strength, self.internet_available, self.internet_quality)
    
    def register_macos_updates(self):
        """Register for network status updates on macOS"""
        try:
            import Foundation
            import objc
            from Cocoa import NSDistributedNotificationCenter, NSWorkspace
            
            # Create observer method to be called when WiFi status changes
            def wifi_changed_(self, notification):
                self.update_network_status()
            
            # Add method to the class
            self.__class__.wifi_changed_ = wifi_changed_
            
            # Register for system notifications about WiFi changes
            center = NSDistributedNotificationCenter.defaultCenter()
            
            # Register for all relevant network notifications
            notifications = [
                "com.apple.system.config.network_change",  # General network changes
                "com.apple.airport.powerstatechange",      # WiFi power state
                "com.apple.airport.linkchange",            # WiFi link status
                "com.apple.system.networkConnect",         # Connected to network
                "com.apple.system.networkDisconnect",      # Disconnected from network
                "com.apple.system.config.internet.on",     # Internet became available 
                "com.apple.system.config.internet.off"     # Internet became unavailable
            ]
            
            for notification_name in notifications:
                center.addObserver_selector_name_object_(
                    self,
                    objc.selector(self.wifi_changed_, signature=b'v@:@'),
                    notification_name,
                    None
                )
            
            # Also check periodically (as a backup)
            self._start_periodic_check()
            
            return True
        except ImportError:
            print("Could not import required macOS libraries")
            return False
    def get_active_connections(self,dbus):
        bus = dbus.SystemBus()
        nm_proxy = bus.get_object("org.freedesktop.NetworkManager", "/org/freedesktop/NetworkManager")
        
        try:
            nm_interface = dbus.Interface(nm_proxy, 'org.freedesktop.NetworkManager')
            # Try calling GetActiveConnections as a method (some systems may still expose it)
            active_connections = nm_interface.GetActiveConnections()
        except dbus.exceptions.DBusException as e:
            if "UnknownMethod" in str(e):
                # Fallback to reading the property
                props_iface = dbus.Interface(nm_proxy, 'org.freedesktop.DBus.Properties')
                active_connections = props_iface.Get('org.freedesktop.NetworkManager', 'ActiveConnections')
            else:
                raise  # Re-raise other unexpected DBus errors

        return active_connections
    def register_linux_updates(self):
        """Register for network updates on Linux using NetworkManager via DBus"""
        try:
            import dbus
            from dbus.mainloop.glib import DBusGMainLoop
            import gi
            gi.require_version('GLib', '2.0')
            from gi.repository import GLib
            
            # Initialize D-Bus main loop
            DBusGMainLoop(set_as_default=True)
            self.loop = GLib.MainLoop()
            
            # Connect to D-Bus
            self.bus = dbus.SystemBus()
            
            # NetworkManager signals for connectivity and properties
            nm_proxy = self.bus.get_object('org.freedesktop.NetworkManager', 
                                          '/org/freedesktop/NetworkManager')
            nm_interface = dbus.Interface(nm_proxy, 'org.freedesktop.NetworkManager')
            nm_properties = dbus.Interface(nm_proxy, 'org.freedesktop.DBus.Properties')
            
            # Set up signal handlers
            nm_properties.connect_to_signal('PropertiesChanged', 
                                           self._handle_nm_properties_changed)
            
            # Find active connections and monitor them
            
            try:
               for connection_path in self.get_active_connections(dbus):
                    self._monitor_connection(connection_path)
            except Exception:
                pass
            
            # Monitor for new connections
            nm_interface.connect_to_signal('StateChanged', self._handle_nm_state_changed)
            
            # Start monitoring in a separate thread
            self.dbus_thread = threading.Thread(target=self._run_dbus_loop)
            self.dbus_thread.daemon = True
            self.dbus_thread.start()
            
            # Also check periodically (as a backup)
            self._start_periodic_check()
            
            return True
        except ImportError:
            print("Could not import required Linux libraries (dbus, gi)")
            # Fall back to periodic checking only
            self._start_periodic_check()
            return False
    
    def _run_dbus_loop(self):
        """Run the GLib main loop for DBus signals in a separate thread"""
        self.loop.run()
    
    def _handle_nm_properties_changed(self, interface, changed_properties, invalidated_properties):
        """Handle NetworkManager property changes"""
        if 'State' in changed_properties or 'Connectivity' in changed_properties:
            self.update_network_status()
    
    def _handle_nm_state_changed(self, state):
        """Handle NetworkManager state changes"""
        self.update_network_status()
    
    def _monitor_connection(self, connection_path):
        """Monitor a specific network connection"""
        try:
            connection_proxy = self.bus.get_object('org.freedesktop.NetworkManager', connection_path)
            connection = dbus.Interface(connection_proxy, 'org.freedesktop.DBus.Properties')
            connection.connect_to_signal('PropertiesChanged', self._handle_connection_properties_changed)
        except:
            pass
    
    def _handle_connection_properties_changed(self, interface, changed_properties, invalidated_properties):
        """Handle connection property changes"""
        self.update_network_status()
    
    def _start_periodic_check(self):
        """Start a periodic check as a backup to event-based updates"""
        def periodic_check():
            while self.running:
                self.update_network_status()
                time.sleep(30)  # Check every 30 seconds as a backup
        
        self.check_thread = threading.Thread(target=periodic_check)
        self.check_thread.daemon = True
        self.check_thread.start()
    
    def register_network_updates(self):
        """Register for both WiFi signal strength and internet connectivity updates"""
        self.running = True
        
        # First update to initialize values
        self.update_network_status()
        
        # Register appropriate handlers based on OS
        if self.os_type == "Darwin":  # macOS
            return self.register_macos_updates()
        else:  # Linux and other Unix systems
            return self.register_linux_updates()
    
    def unregister_network_updates(self):
        """Clean up and unregister all network update listeners"""
        self.running = False
        
        if self.os_type == "Darwin":
            try:
                from Cocoa import NSDistributedNotificationCenter
                center = NSDistributedNotificationCenter.defaultCenter()
                center.removeObserver_(self)
            except:
                pass
        else:
            # Stop the DBus loop if it's running
            if hasattr(self, 'loop') and self.loop is not None:
                self.loop.quit()
    
    def get_status_info(self):
        """Get a dictionary with the current status information"""
        return {
            'signal_strength': self.current_signal_strength,
            'internet_available': self.internet_available,
            'internet_quality': self.internet_quality,
            'last_update': self.last_update_time,
            'history': self.history
        }
    
    def get_wifi_bars(self):
        """
        Convert signal percentage to visual WiFi bars (macOS style with 3 bars)
        
        Returns:
            str: Visual representation of signal strength with 3 bars
        """
        if self.current_signal_strength >= 70:  # 70-100%
            return "▮ ▮ ▮"  # All 3 bars (Excellent/Good)
        elif self.current_signal_strength >= 40:  # 40-69%
            return "▮ ▮ □"  # 2 bars (Fair)
        elif self.current_signal_strength > 0:   # 1-39%
            return "▮ □ □"  # 1 bar (Poor)
        else:
            return "□ □ □"  # 0 bars (No signal)
    
    def get_internet_indicator(self):
        """
        Generate an internet connectivity indicator
        
        Returns:
            str: Symbol indicating internet status
        """
        if not self.internet_available:
            return "⊘"  # No internet (circle with slash)
        elif self.internet_quality >= 70:
            return "●"  # Excellent
        elif self.internet_quality >= 40:
            return "◐"  # Good/Fair
        else:
            return "○"  # Poor but connected
    
    def get_signal_quality_description(self):
        """Get a text description of the current signal quality"""
        if self.current_signal_strength >= 80:
            return "Excellent"
        elif self.current_signal_strength >= 60:
            return "Good"
        elif self.current_signal_strength >= 40:
            return "Fair"
        elif self.current_signal_strength >= 20:
            return "Poor"
        else:
            return "Very Poor"
            
    def get_internet_quality_description(self):
        """Get a text description of the current internet quality"""
        if not self.internet_available:
            return "Not Available"
        elif self.internet_quality >= 80:
            return "Excellent"
        elif self.internet_quality >= 60:
            return "Good"
        elif self.internet_quality >= 40:
            return "Fair"
        elif self.internet_quality >= 20:
            return "Poor"
        else:
            return "Very Poor"
    
    def display_mac_style_status(self):
        """Display network status in a compact, macOS-like format"""
        wifi_bars = self.get_wifi_bars()
        internet_indicator = self.get_internet_indicator()
        
        # Get signal quality descriptions
        if self.current_signal_strength >= 80:
            wifi_quality = "Excellent"
        elif self.current_signal_strength >= 60:
            wifi_quality = "Good"
        elif self.current_signal_strength >= 40:
            wifi_quality = "Fair"
        elif self.current_signal_strength >= 20:
            wifi_quality = "Poor"
        else:
            wifi_quality = "Very Poor"
        
        # Format similar to macOS menu bar but with more info
        if self.internet_available:
            if self.internet_quality >= 80:
                internet_quality_desc = "Excellent"
            elif self.internet_quality >= 60:
                internet_quality_desc = "Good"
            elif self.internet_quality >= 40:
                internet_quality_desc = "Fair"
            elif self.internet_quality >= 20:
                internet_quality_desc = "Poor"
            else:
                internet_quality_desc = "Very Poor"
                
            return f"WiFi: {wifi_bars} ({self.current_signal_strength}% - {wifi_quality}) | Net: {internet_indicator} ({self.internet_quality}% - {internet_quality_desc})"
        else:
            return f"WiFi: {wifi_bars} ({self.current_signal_strength}% - {wifi_quality}) | Net: {internet_indicator} (Disconnected)"
    
    def start_monitoring(self):
        """Start monitoring network status"""
        if not self.running:
            return self.register_network_updates()
        return True
    
    async def monitor(self):
        # Start monitoring
        print(f"Starting network monitoring on {self.os_type}...")
        self.start_monitoring()
        
        # Keep the main program running
        print("Network monitor running. Press Ctrl+C to exit.")
        
        # If this is a console application, just wait for Ctrl+C
        while self.running:
           await asyncio.sleep(1)
    
    def stop_monitoring(self):
        """Stop monitoring network status"""
        if self.running:
            self.unregister_network_updates()
        return True