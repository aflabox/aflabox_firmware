import os
import subprocess
import re
import platform
import time
import threading,random
from datetime import datetime, timedelta
from utils.thread_locks import get_db,get_db_path
from tinydb import TinyDB
import speedtest
import statistics
from db.internet_speeddb import InternetMonitorDB

# Config

TEST_FILE = "upload_test_file.bin"
FILE_SIZE_MB = 12

# Targets - adjusted based on more realistic expectations
TARGET_DOWNLOAD = 25.0  # Mbps - baseline for "good" internet
TARGET_UPLOAD = 10.0    # Mbps
MAX_PING = 150.0        # ms - increased to avoid overly harsh scoring
MAX_PACKET_LOSS = 5.0   # Percentage
IDEAL_SIGNAL_STRENGTH = -30.0  # dBm
MIN_SIGNAL_STRENGTH = -85.0    # dBm - adjusted to be less punishing

# Thresholds for lightweight checks
POOR_PING = 2200.0       # ms - increased slightly
SEVERE_PACKET_LOSS = 10.0  # Percentage
WEAK_SIGNAL = -70.0     # dBm - adjusted for more common signal strengths

# Import math for logarithmic calculations
import math

# History tracking
HISTORY_SIZE = 30       # Number of minute records to keep
TREND_WINDOW = 5        # Window size for trend detection

# Weights for scoring - adjusted to provide better balance
SPEED_WEIGHT = 0.35     # Reduced from 0.4
PING_WEIGHT = 0.25      # Reduced from 0.3
SIGNAL_WEIGHT = 0.3     # Kept the same
STABILITY_WEIGHT = 0.1  # Added explicit stability weight

# Passive measurement thresholds for lightweight checks
DNS_TIMEOUT = 1.0  # seconds
HTTP_TIMEOUT = 3.0  # seconds
TCP_TIMEOUT = 2.0   # seconds

UPLOAD_SERVICES = ['https://api.aflabox.ai/fileio/upload']

class InternetMonitor:
    def __init__(self):
        self.db = InternetMonitorDB()
        
        # self.db_minute = self.db.table("minute_checks")
        # self.db_hourly = self.db.table("hourly_checks")
        # self.db_last = self.db.table("last_recorded")
        
        # Maintain in-memory cache of recent measurements for quick calculations
        self.recent_pings = []
        self.recent_packet_loss = []
        self.recent_signal_strength = []
        self.passive_speeds = []
        
        # Last known speed values from full test
        self.last_download = None
        self.last_upload = None
        
        # Flag for hotspot detection
        self.hotspot_detected = False
        
        # Estimate stability
        self.jitter_values = []
        
        # Create test file if needed
        self.create_test_file()
        
        # Last full test time
        self.last_full_test = datetime.min

    def create_test_file(self):
        if not os.path.exists(TEST_FILE):
            with open(TEST_FILE, "wb") as f:
                f.write(os.urandom(FILE_SIZE_MB * 1024 * 1024))
                
    def get_average_signal_strength(self, lookback_minutes=30):
        """ Compute average signal strength over the last X minutes. """
        if self.recent_signal_strength:
            return statistics.mean(self.recent_signal_strength[-lookback_minutes:])
        
        recent_records = self.db.get_last_n_minutes(minutes=lookback_minutes)
        if not recent_records:
            return None  # No data yet
        
        average_signal = sum(r['signal_strength'] for r in recent_records) / len(recent_records)
        return average_signal

    def run_speedtest(self):
        """Run a full speedtest, but limit frequency to save resources"""
        now = datetime.now()
        
        # Only run full test if it's been at least 30 minutes since last test
        if (now - self.last_full_test).total_seconds() < 1800:
            # Return estimated values if available
            if self.last_download and self.last_upload:
                # Add a small random adjustment to simulate subtle changes
                variation = 0.95 + (random.random() * 0.1)  # Random factor between 0.95 and 1.05
                return {
                    "download": self.last_download * variation,
                    "upload": self.last_upload * variation,
                    "ping": statistics.mean(self.recent_pings) if self.recent_pings else 0,
                    "estimated": True
                }
        
        try:
            # First try Speedtest library (more accurate but can fail)
            try:
                st = speedtest.Speedtest(timeout=30)
                st.get_best_server()
                # Use a proper download test sample size
                download = st.download(threads=None)
                upload = st.upload(threads=None)
                results = st.results.dict()
                
                self.last_download = round(download / 1_000_000, 2)
                self.last_upload = round(upload / 1_000_000, 2)
                self.last_full_test = now
                
                # Validate results - sometimes speedtest returns unrealistically low values
                # due to server issues rather than actual connection problems
                if self.last_download < 1.0 and not self.recent_packet_loss:
                    # Suspiciously low result when network is otherwise responsive
                    passive_estimate = self.estimate_speed_passive()
                    if passive_estimate > self.last_download * 5:
                        # Likely a bad test - use passive estimate instead
                        self.last_download = passive_estimate
                
                return {
                    "download": self.last_download,
                    "upload": self.last_upload,
                    "ping": results["ping"],
                    "estimated": False
                }
            except Exception as e:
                print(f"Primary speedtest error: {e}")
                # If the main speedtest fails, try a simpler test method
                raise e
                
        except Exception as e:
            print(f"Speedtest error: {e}")
            # Return estimated values if available
            if self.last_download and self.last_upload:
                return {
                    "download": self.last_download,
                    "upload": self.last_upload,
                    "ping": statistics.mean(self.recent_pings) if self.recent_pings else 0,
                    "estimated": True
                }
                
            # Calculate baseline estimated speeds from ping times
            avg_ping = statistics.mean(self.recent_pings) if self.recent_pings else 150
            avg_packet_loss = statistics.mean(self.recent_packet_loss) if self.recent_packet_loss else 5
            
            # Estimate download speed based on ping and packet loss
            # Better ping generally correlates with better bandwidth on the same connection
            if avg_ping < 30:
                estimated_download = 50.0  # Excellent ping correlates with high-speed fiber
            elif avg_ping < 60:
                estimated_download = 30.0  # Very good ping
            elif avg_ping < 100:
                estimated_download = 20.0  # Good ping
            elif avg_ping < 200:
                estimated_download = 10.0  # Average ping
            else:
                estimated_download = 5.0   # Poor ping
                
            # Reduce estimates based on packet loss
            if avg_packet_loss > 10:
                estimated_download *= 0.5
            elif avg_packet_loss > 5:
                estimated_download *= 0.7
            elif avg_packet_loss > 2:
                estimated_download *= 0.9
            
            # Upload is typically lower than download
            estimated_upload = estimated_download * 0.4
            
            return {
                "download": estimated_download,
                "upload": estimated_upload,
                "ping": avg_ping,
                "estimated": True
            }

    def get_ping_and_packet_loss(self):
        """Run lightweight ping test to 8.8.8.8"""
        cmd = ["ping", "-c", "5", "8.8.8.8"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
            output = result.stdout
            
            # Extract average ping time
            ping_match = re.search(r'([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)', output)
            if ping_match:
                ping = float(ping_match.group(2))
                
                # Calculate jitter
                min_ping = float(ping_match.group(1))
                max_ping = float(ping_match.group(3))
                jitter = max_ping - min_ping
                self.jitter_values.append(jitter)
                if len(self.jitter_values) > HISTORY_SIZE:
                    self.jitter_values.pop(0)
            else:
                ping = 200.0
                
            # Extract packet loss
            loss_match = re.search(r'(\d+)% packet loss', output)
            packet_loss = float(loss_match.group(1)) if loss_match else 100.0
            
            # Update history
            self.recent_pings.append(ping)
            self.recent_packet_loss.append(packet_loss)
            
            # Maintain history size
            if len(self.recent_pings) > HISTORY_SIZE:
                self.recent_pings.pop(0)
            if len(self.recent_packet_loss) > HISTORY_SIZE:
                self.recent_packet_loss.pop(0)
                
            return ping, packet_loss
        except subprocess.TimeoutExpired:
            # Timeout indicates severe network issues
            self.recent_pings.append(500.0)
            self.recent_packet_loss.append(100.0)
            
            # Maintain history size
            if len(self.recent_pings) > HISTORY_SIZE:
                self.recent_pings.pop(0)
            if len(self.recent_packet_loss) > HISTORY_SIZE:
                self.recent_packet_loss.pop(0)
                
            return 500.0, 100.0
        except Exception as e:
            print(f"Ping error: {e}")
            return 300.0, 80.0
            
    def get_wifi_interface(self):
        """Identify the active WiFi interface"""
        try:
            if platform.system() == "Linux":
                result = subprocess.run(["iw", "dev"], capture_output=True, text=True, check=True)
                match = re.search(r'Interface (\w+)', result.stdout)
                return match.group(1) if match else "wlan0"
            else:
                return "wlan0"  # Default for non-Linux
        except:
            return "wlan0"  # Fallback
            
    def get_wifi_signal_strength(self):
        """Measure WiFi signal strength and attempt to detect hotspot"""
        system = platform.system()
        signal = -80.0  # Default value
        is_hotspot_likely = False
        ssid = "Unknown"

        if system == "Linux":
            iface = self.get_wifi_interface()
            try:
                # Get signal strength
                result = subprocess.run(["iw", "dev", iface, "link"], capture_output=True, text=True, check=True)
                match = re.search(r'signal: (-?\d+) dBm', result.stdout)
                signal = float(match.group(1)) if match else -80.0
                
                # Get SSID
                ssid_match = re.search(r'SSID: (.+)', result.stdout)
                if ssid_match:
                    ssid = ssid_match.group(1).strip()
                
                # Check frequency to detect 2.4GHz vs 5GHz
                freq_match = re.search(r'freq: (\d+)', result.stdout)
                if freq_match:
                    freq = int(freq_match.group(1))
                    # 2.4GHz frequency is common for hotspots
                    is_2ghz = freq < 3000
                    
                    # Check for typical hotspot SSIDs
                    is_hotspot_likely = (
                        is_2ghz and 
                        any(x in ssid.lower() for x in ['iphone', 'android', 'mobile', 'hotspot', 'mifi', 'mi_', 'phone'])
                    )
            except Exception as e:
                print(f"Error getting Linux WiFi info: {e}")
                signal = -80.0

        elif system == "Darwin":  # macOS
            try:
                # Get airport info
                result = subprocess.run(
                    ["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-I"],
                    capture_output=True, text=True, check=True
                )
                
                # Parse airport info
                output = result.stdout
                signal_match = re.search(r'agrCtlRSSI: (-?\d+)', output)
                signal = float(signal_match.group(1)) if signal_match else -80.0
                
                # Get SSID
                ssid_match = re.search(r' SSID: (.+)', output)
                if ssid_match:
                    ssid = ssid_match.group(1).strip()
                
                # Check channel for hotspot detection (2.4GHz channels are 1-14)
                channel_match = re.search(r' channel: (\d+)', output)
                if channel_match:
                    channel = int(channel_match.group(1))
                    is_2ghz = channel <= 14
                    
                    # Additional checks for common hotspot characteristics
                    is_hotspot_likely = (
                        is_2ghz and 
                        any(x in ssid.lower() for x in ['iphone', 'android', 'mobile', 'hotspot', 'mifi', 'mi_', 'phone'])
                    )
                    
                # Check for noise level - hotspots often have higher noise levels
                noise_match = re.search(r'agrCtlNoise: (-?\d+)', output)
                if noise_match:
                    noise = float(noise_match.group(1))
                    signal_to_noise = signal - noise
                    # Poor signal-to-noise ratio is common on hotspots
                    if signal_to_noise < 20:
                        is_hotspot_likely = True
                        
                # Look for transmit rate - hotspots often have lower rates
                tx_rate_match = re.search(r'lastTxRate: (\d+)', output)
                if tx_rate_match:
                    tx_rate = int(tx_rate_match.group(1))
                    if tx_rate < 100:  # Lower transmit rates suggest hotspot or congested network
                        is_hotspot_likely = True
                        
            except Exception as e:
                print(f"Error getting macOS WiFi info: {e}")
                signal = -80.0

        else:
            # Unsupported system
            signal = -80.0
            
        # Update history
        self.recent_signal_strength.append(signal)
        if len(self.recent_signal_strength) > HISTORY_SIZE:
            self.recent_signal_strength.pop(0)
            
        # Check ping stability as an additional hotspot indicator
        if len(self.recent_pings) >= 5:
            # Calculate ping variability - cellular connections often have more variable pings
            ping_stdev = statistics.stdev(self.recent_pings)
            ping_mean = statistics.mean(self.recent_pings)
            if ping_mean > 0:
                ping_variation = ping_stdev / ping_mean
                if ping_variation > 0.3:  # High variation common in cellular
                    is_hotspot_likely = True
            
            # Higher average ping is common on cellular connections
            if ping_mean > 80:
                is_hotspot_likely = True
        
        # Detect common cellular patterns
        if self.last_download and self.last_upload:
            # Upload often much lower than download on cellular
            if self.last_download > 0 and self.last_upload / self.last_download < 0.2:
                is_hotspot_likely = True
                
        # Save hotspot detection status
        self.hotspot_detected = is_hotspot_likely
        
        # Log detection info for debugging
        if is_hotspot_likely:
            print(f"Hotspot likely detected - SSID: {ssid}, Signal: {signal} dBm")
            
        return signal

    def estimate_speed_passive(self):
        """Estimate connection speed using passive techniques without running a full speedtest"""
        # Perform a quick DNS lookup as a basic connectivity test
        dns_start = time.time()
        dns_ok = False
        try:
            result = subprocess.run(["nslookup", "google.com"], capture_output=True, text=True, timeout=DNS_TIMEOUT)
            dns_ok = "Non-authoritative answer" in result.stdout
        except:
            pass
        dns_time = time.time() - dns_start
        
        # Test HTTP connectivity - try multiple sites for more reliable assessment
        http_times = []
        http_ok = False
        sites = ["https://www.google.com", "https://www.wikipedia.org", "https://www.cloudflare.com"]
        
        for site in sites:
            try:
                http_start = time.time()
                result = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", site], 
                                      capture_output=True, text=True, timeout=HTTP_TIMEOUT)
                if result.stdout.strip() == "200":
                    http_ok = True
                    http_times.append(time.time() - http_start)
            except:
                pass
        
        # Use the best (fastest) response time if we have multiple successful requests
        http_time = min(http_times) if http_times else HTTP_TIMEOUT
        
        # Calculate estimated speed based on response times
        if dns_ok and http_ok:
            # Baseline moderate estimate - adjusted higher to prevent underreporting
            speed_estimate = 15.0
            
            # Much more optimistic speed estimates based on response times
            if dns_time < 0.05 and http_time < 0.3:
                # Very fast responses - likely a good fiber/cable connection
                speed_estimate = 50.0
            elif dns_time < 0.1 and http_time < 0.5:
                # Fast responses - likely a good broadband connection
                speed_estimate = 35.0
            elif dns_time < 0.2 and http_time < 1.0:
                # Decent responses - likely a standard broadband connection
                speed_estimate = 25.0
            elif dns_time > 0.5 or http_time > 2.0:
                # Slow but functional connection
                speed_estimate = 10.0
            
            # Use historical data for stability if available
            if self.last_download:
                # Blend with previous full speedtest result to avoid wild fluctuations
                # but give more weight to actual measured speeds
                speed_estimate = (speed_estimate * 0.3) + (self.last_download * 0.7)
            
            self.passive_speeds.append(speed_estimate)
            if len(self.passive_speeds) > HISTORY_SIZE:
                self.passive_speeds.pop(0)
                
            return speed_estimate
        elif dns_ok:
            # DNS works but HTTP failed - partial connectivity but don't report extremely low
            return 5.0
        else:
            # Complete failure but still not zero (minimum usable connection)
            return 2.0
            
    def detect_connection_trends(self):
        """Analyze recent measurements to detect trends and anomalies"""
        if len(self.recent_pings) < TREND_WINDOW:
            return "insufficient_data", 0
            
        # Get recent values
        recent_pings = self.recent_pings[-TREND_WINDOW:]
        
        # Calculate linear trend (simple)
        first_values = recent_pings[:TREND_WINDOW//2]
        last_values = recent_pings[TREND_WINDOW//2:]
        
        first_avg = statistics.mean(first_values)
        last_avg = statistics.mean(last_values)
        
        # Calculate percent change
        if first_avg > 0:
            percent_change = ((last_avg - first_avg) / first_avg) * 100
        else:
            percent_change = 0
            
        # Determine trend
        if percent_change > 20:
            return "degrading", percent_change
        elif percent_change < -20:
            return "improving", percent_change
        else:
            return "stable", percent_change
            
    def estimate_stability(self):
        """Calculate a stability score based on jitter and variation in measurements"""
        if not self.jitter_values or not self.recent_pings:
            return 50  # Default middle value
            
        # Calculate coefficient of variation for ping times (lower is better)
        if len(self.recent_pings) >= 3:
            ping_mean = statistics.mean(self.recent_pings)
            if ping_mean > 0:
                ping_stdev = statistics.stdev(self.recent_pings)
                cv = (ping_stdev / ping_mean) * 100
                
                # Convert to a 0-100 score where 0 is bad (high variation) and 100 is good (low variation)
                cv_score = max(0, 100 - min(cv * 2, 100))
            else:
                cv_score = 0
        else:
            cv_score = 50  # Default
            
        # Average jitter score
        avg_jitter = statistics.mean(self.jitter_values) if self.jitter_values else 50
        jitter_score = max(0, 100 - min(avg_jitter * 2, 100))
        
        # Combine scores
        stability_score = (cv_score * 0.7) + (jitter_score * 0.3)
        return min(100, max(0, stability_score))

    def calculate_full_strength_score(self, download, upload, ping, packet_loss, signal_strength):
        """Calculate comprehensive score when full data is available"""
        # Adjust expectations for connection type
        is_hotspot = self.hotspot_detected
        
        # Adjust targets for hotspots - cellular connections have different baselines
        effective_download_target = TARGET_DOWNLOAD * 0.6 if is_hotspot else TARGET_DOWNLOAD
        effective_upload_target = TARGET_UPLOAD * 0.5 if is_hotspot else TARGET_UPLOAD
        effective_ping_target = MAX_PING * 1.5 if is_hotspot else MAX_PING
        
        # Speed score components
        dl_weight = 0.6  # Download is typically more important for user experience
        ul_weight = 0.4
        
        # Use square root scale for more forgiving curve at lower speeds
        download_score = min(100 * (download / effective_download_target)**0.5, 100)
        upload_score = min(100 * (upload / effective_upload_target)**0.5, 100)
        speed_score = (download_score * dl_weight) + (upload_score * ul_weight)
        
        # Responsiveness penalties - use logarithmic scale for more natural scaling
        # Higher tolerance for latency on hotspots
        ping_norm = max(1, min(ping, effective_ping_target*2))
        ping_penalty = min(30, 15 * (math.log10(ping_norm) / math.log10(effective_ping_target)))
        
        # More forgiving packet loss penalty for hotspots (cellular often has some packet loss)
        packet_loss_penalty = min(30, (packet_loss / (MAX_PACKET_LOSS * (1.5 if is_hotspot else 1))) * 30)
        
        # Quality factor from signal strength - use custom curve
        signal_mid = (MIN_SIGNAL_STRENGTH + IDEAL_SIGNAL_STRENGTH) / 2
        signal_range = IDEAL_SIGNAL_STRENGTH - MIN_SIGNAL_STRENGTH
        
        if signal_strength <= signal_mid:
            # Lower half of the range - scale more generously
            signal_factor = 40 + (signal_strength - MIN_SIGNAL_STRENGTH) / (signal_range/2) * 30
        else:
            # Upper half of the range
            signal_factor = 70 + (signal_strength - signal_mid) / (signal_range/2) * 30
            
        signal_strength_score = max(30, min(signal_factor, 100))  # Minimum 30% for any signal
        
        # Stability factor
        stability_score = self.estimate_stability()
        
        # Combine all factors - more forgiving weights for hotspot
        if is_hotspot:
            # Hotspot scoring - prioritize different factors
            combined_score = (
                0.45 * speed_score +           # Higher weight on raw speed
                0.2 * signal_strength_score +  # Lower weight on signal (variable for cellular)
                0.15 * stability_score -       # Higher weight on stability
                0.1 * ping_penalty -           # Lower penalty for ping (expected to be higher)
                0.1 * packet_loss_penalty      # Lower penalty for packet loss
            )
            
            # Add hotspot bonus to create a fairer comparison
            hotspot_bonus = 10  # Baseline bonus for hotspot connections
            combined_score += hotspot_bonus
        else:
            # Normal WiFi scoring
            combined_score = (
                SPEED_WEIGHT * speed_score +
                SIGNAL_WEIGHT * signal_strength_score + 
                0.1 * stability_score -
                PING_WEIGHT * ping_penalty -
                0.2 * packet_loss_penalty
            )
        
        # Final normalization
        return max(0, min(combined_score, 100))

    def calculate_realtime_strength_score(self):
        """Calculate lightweight score for frequent updates"""
        # Get current values with fallbacks to reasonable defaults
        ping = statistics.mean(self.recent_pings) if self.recent_pings else 100
        packet_loss = statistics.mean(self.recent_packet_loss) if self.recent_packet_loss else 0
        signal_strength = statistics.mean(self.recent_signal_strength) if self.recent_signal_strength else -75
        
        # Determine connection type
        is_hotspot = self.hotspot_detected
        
        # Estimated speed from passive measurements - use more optimistic baseline
        estimated_speed = statistics.mean(self.passive_speeds) if self.passive_speeds else 15
        
        # Apply a minimum baseline speed to prevent extremely low scores
        # when network is actually functional
        if ping < 200 and packet_loss < 10:  # If network is responsive
            estimated_speed = max(estimated_speed, 10)  # Minimum baseline speed of 10 Mbps
        
        # Scale target expectations based on connection type
        effective_download_target = TARGET_DOWNLOAD * 0.6 if is_hotspot else TARGET_DOWNLOAD
        
        # Calculate speed score with more forgiving curve
        # Square root transformation makes lower speeds score higher
        speed_score = min(100, 100 * (estimated_speed / effective_download_target)**0.5)
        
        # Add WiFi improvement factor - if you're on normal WiFi but scoring low
        if not is_hotspot and speed_score < 60:
            wifi_adjustment = 10  # Baseline boost for connected WiFi
            speed_score += wifi_adjustment
        
        # Calculate penalties with reduced impact and better scaling
        # Adjust ping expectations based on connection type
        effective_ping_target = MAX_PING * 1.5 if is_hotspot else MAX_PING
        
        # Use logarithmic scale for ping to be less punishing of moderate latency
        ping_norm = max(1, min(ping, effective_ping_target*2))  # Normalize and cap ping
        ping_penalty = min(30, 15 * (math.log10(ping_norm) / math.log10(effective_ping_target)))
        
        # Make packet loss penalty less severe for small amounts of loss
        # Higher tolerance for hotspots
        max_acceptable_loss = MAX_PACKET_LOSS * (1.5 if is_hotspot else 1)
        if packet_loss < 1:
            packet_loss_penalty = packet_loss * 2  # Minor penalty for minimal loss
        else:
            packet_loss_penalty = min(30, 10 + (packet_loss / max_acceptable_loss) * 20)
        
        # Signal quality factor - more forgiving curve for moderate signal strengths
        # Use a sigmoid-like curve that's more forgiving in the middle range
        signal_mid = (MIN_SIGNAL_STRENGTH + IDEAL_SIGNAL_STRENGTH) / 2
        signal_range = IDEAL_SIGNAL_STRENGTH - MIN_SIGNAL_STRENGTH
        
        if signal_strength <= signal_mid:
            # Lower half of the range - scale more generously
            signal_factor = 40 + (signal_strength - MIN_SIGNAL_STRENGTH) / (signal_range/2) * 30
        else:
            # Upper half of the range
            signal_factor = 70 + (signal_strength - signal_mid) / (signal_range/2) * 30
            
        signal_strength_score = max(30, min(signal_factor, 100))  # Minimum 30% for any signal
        
        # For WiFi, signal quality has a higher baseline
        if not is_hotspot:
            signal_strength_score = max(signal_strength_score, 50)  # WiFi signals typically decent
        
        # Compute trend factor
        trend, percent_change = self.detect_connection_trends()
        trend_factor = 0
        if trend == "improving":
            trend_factor = min(10, abs(percent_change) / 2)  # Bonus for improving trend
        elif trend == "degrading":
            trend_factor = -min(10, abs(percent_change) / 2)  # Penalty for degrading trend
        
        # Add bonus for consistently low packet loss and stable ping
        stability_bonus = 0
        if packet_loss < 0.5 and len(self.recent_pings) > 5:
            ping_stdev = statistics.stdev(self.recent_pings) if len(self.recent_pings) >= 2 else 0
            if ping_stdev < 10:
                stability_bonus = 5  # Bonus for stable connection
        
        # Combine factors with weights adjusted by connection type
        if is_hotspot:
            # Hotspot scoring
            strength_score = (
                0.45 * speed_score +           # Higher weight on raw speed
                0.2 * signal_strength_score -  # Lower weight on signal (variable for cellular)
                ping_penalty * 0.15 -          # Lower penalty for ping (expected to be higher)
                packet_loss_penalty * 0.1 +    # Lower penalty for packet loss
                trend_factor +
                stability_bonus + 
                8                              # Baseline bonus for hotspot context
            )
        else:
            # WiFi scoring - more balanced approach
            strength_score = (
                0.35 * speed_score +           # Balanced weight on speed
                0.3 * signal_strength_score -  # Higher weight on signal quality for WiFi
                ping_penalty * 0.15 -          # Moderate ping penalty
                packet_loss_penalty * 0.1 +    # Lower packet loss weight (less common issue)
                trend_factor +
                stability_bonus + 
                5                              # Small baseline adjustment for WiFi
            )
        
        # Apply a floor based on functionality - if basic internet works, 
        # score shouldn't be too low
        if ping < 200 and packet_loss < 10 and estimated_speed > 5:
            # Higher floor for WiFi than hotspot
            min_score = 50 if not is_hotspot else 40
            strength_score = max(strength_score, min_score)
            
        return max(0, min(strength_score, 100))

    def save_last_details(self, record):
        """Save the most recent reading"""
        # self.db_last.truncate()
        # self.db_last.insert(record)
        pass

    def every_minute_check(self):
        """Perform lightweight monitoring every minute"""
        # Get ping, packet loss
        ping, packet_loss = self.get_ping_and_packet_loss()
        
        # Get signal strength
        signal_strength = self.get_wifi_signal_strength()
        
        # Estimate speed using passive techniques
        estimated_speed = self.estimate_speed_passive()
        
        # Compute scores
        strength_score = self.calculate_realtime_strength_score()
        stability_score = self.estimate_stability()
        
        # Check for hotspot
        is_hotspot = self.hotspot_detected or signal_strength <= WEAK_SIGNAL
        
        # Detect connection trend
        trend, percent_change = self.detect_connection_trends()
        
        # Create record
        record = {
            "timestamp": datetime.now().isoformat(),
            "ping": ping,
            "packet_loss": packet_loss,
            "signal_strength": signal_strength,
            "estimated_speed": estimated_speed,
            "strength_score": strength_score,
            "stability_score": stability_score,
            "is_hotspot": is_hotspot,
            "trend": trend,
            "trend_change": percent_change,
            "type": "minute"
        }
        
        # Save to database
        self.db.save_check(record,"minute")
        # self.save_last_details(record)
        
        # Determine if we should trigger a full test
        should_run_full_test = False
        
        # If ping suddenly increased significantly
        if len(self.recent_pings) > 5:
            avg_previous = statistics.mean(self.recent_pings[:-1])
            if ping > avg_previous * 2 and ping > POOR_PING:
                should_run_full_test = True
                
        # If signal strength dropped significantly
        if len(self.recent_signal_strength) > 5:
            avg_previous_signal = statistics.mean(self.recent_signal_strength[:-1])
            if signal_strength < avg_previous_signal - 15:
                should_run_full_test = True
                
        # If packet loss is severe
        if packet_loss > SEVERE_PACKET_LOSS:
            should_run_full_test = True
            
        # Return whether a full test is recommended
        return should_run_full_test

    def every_hour_full_check(self):
        """Perform comprehensive check including speedtest"""
        try:
            # Run speedtest
            result = self.run_speedtest()
            
            # Get ping and packet loss
            ping, packet_loss = self.get_ping_and_packet_loss()
            
            # Get signal strength
            signal_strength = self.get_wifi_signal_strength()
            
            # Calculate stability
            stability_score = self.estimate_stability()
            
            # Calculate full strength score
            strength_score = self.calculate_full_strength_score(
                result["download"], result["upload"], ping, packet_loss, signal_strength
            )
            
            # Create record
            record = {
                "timestamp": datetime.now().isoformat(),
                "download": result["download"],
                "upload": result["upload"],
                "ping": ping,
                "packet_loss": packet_loss,
                "signal_strength": signal_strength,
                "strength_score": strength_score,
                "stability_score": stability_score,
                "is_hotspot": self.hotspot_detected,
                "estimated": result.get("estimated", False),
                "type": "hour"
            }
            
            # Save to database
            self.db.save_check(record,"hour")
            # self.save_last_details(record)
            
            return record
            
        except Exception as e:
            print(f"Error in hourly check: {e}")
            return None

    def get_last_known(self, minutes=30,new_db=True):
        """Get most recent reading within specified time window"""
        if new_db:
            db = InternetMonitorDB()
        else:
            db = self.db
        data= db.get_recent_checks(minutes)
        if new_db:
            db.cleanup()
        return data
    

    def get_combined_score(self):
        """Calculate overall connection quality considering all factors"""
        # Get recent minute records for real-time factors
        last_n_minutes = self.db.get_last_n_minutes(30)
        recent_minutes = last_n_minutes if len(last_n_minutes) >= 30 else self.db.get_recent_checks(count=100)
        
        # Get most recent hourly record for speed factors
        last_n_hour = self.db.get_last_n_minutes(30,"hour")
        recent_hour = last_n_hour if len(last_n_hour) > 0 else None

        # Calculate average of minute scores
        minute_avg = sum(r['strength_score'] for r in recent_minutes) / len(recent_minutes) if recent_minutes else 50
        
        # Calculate stability score
        stability = self.estimate_stability()
        
        # If we have hourly data with speed measurements
        if recent_hour:
            # Combine hourly (speed-based) and minute (responsiveness-based) scores
            return (recent_hour['strength_score'] * 0.6) + (minute_avg * 0.3) + (stability * 0.1)
        else:
            # No hourly data, use minute data with estimated speeds
            return (minute_avg * 0.8) + (stability * 0.2)

    def monitor_loop(self):
        """Run continuous monitoring loop"""
        next_hour_check = datetime.now() + timedelta(hours=1)
        
        while True:
            try:
                # Run minute check
                should_run_full = self.every_minute_check()
                
                # Check if it's time for hourly check
                now = datetime.now()
                if now >= next_hour_check or should_run_full:
                    self.every_hour_full_check()
                    next_hour_check = now + timedelta(hours=1)
                    
                # Get current status
                combined_score = self.get_combined_score()
                last = self.get_last_known(5)
                
                # Format status message
                if last:
                    # Adjust quality assessment based on connection type
                    if last.get("is_hotspot"):
                        # More forgiving thresholds for hotspot
                        status_type = "🟢 Excellent" if combined_score > 70 else "🟡 Good" if combined_score > 45 else "🟠 Fair" if combined_score > 30 else "🔴 Poor"
                        connection_type = "📱 Mobile Hotspot"
                    else:
                        # Standard thresholds for WiFi
                        status_type = "🟢 Excellent" if combined_score > 80 else "🟡 Good" if combined_score > 60 else "🟠 Fair" if combined_score > 40 else "🔴 Poor"
                        connection_type = "🖥️ WiFi"
                    
                    # Get trend information
                    trend = last.get("trend", "stable")
                    trend_icon = "↗️" if trend == "improving" else "↘️" if trend == "degrading" else "→"
                    
                    # Format status message with context
                    if last.get("is_hotspot"):
                        print(f"📊 Mobile Connection: {combined_score:.1f}% {status_type} {trend_icon} (For hotspot, this is {status_type.split()[1]} quality)")
                    else:
                        print(f"📊 Internet Quality: {combined_score:.1f}% {status_type} {connection_type} {trend_icon}")
                
                # Sleep until next check
                time.sleep(60)  # 1 minute interval
                
            except KeyboardInterrupt:
                print("Monitoring stopped by user")
                break
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Continue despite errors
