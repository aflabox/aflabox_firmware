import os
import subprocess
import json
from datetime import datetime
import sqlite3
import socket
import asyncio
from typing import Callable, List
from utils.logger import get_logger

logger = get_logger(__file__)

class InternetQualityMonitor:
    def __init__(self, db_path="~/internet_quality.db", socket_port=5001, check_interval=15):
        self.db_path = os.path.expanduser(db_path)
        
        self.subscribers: List[Callable[[], None]] = []
        self.socket_port = socket_port
        self._initialize_db()
        self.current_ssid = self.get_wifi_ssid()
        self.last_internet_status = self.has_internet()
       
        self.check_interval = check_interval
        

    def _initialize_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS internet_quality (
                timestamp TEXT,
                ssid TEXT,
                ping REAL,
                jitter REAL,
                packet_loss REAL,
                wifi_strength REAL,
                strength REAL,
                stability REAL,
                has_internet INTEGER
            )
        """)
        conn.commit()
        conn.close()
    def get_wifi_ssid(self):
        if os.uname().sysname == "Darwin":
            return self._run_command("/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -I | grep 'SSID' | awk '{print $2}'")
        else:
            return self._run_command("iwgetid -r")
    def subscribe(self, callback: Callable[[], None]):
        """Adds a function to be called when internet is lost."""
        self.subscribers.append(callback)

    def _run_command(self, command):
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            return result.stdout.strip()
        except Exception:
            return ""

    def get_ping_info(self):
        ping_output = self._run_command("ping -c 10 8.8.8.8 | tail -2")
        if not ping_output:
            return None, None, None

        lines = ping_output.split('\n')
        if len(lines) < 2:
            return None, None, None

        try:
            stats = lines[1].split('/')[4:7]
            avg_ping = float(stats[0])
            jitter = float(stats[1])
            packet_loss = float(lines[0].split(",")[2].split(" ")[1].replace('%', ''))
        except:
            return None, None, None

        return avg_ping, jitter, packet_loss

    def get_wifi_signal_strength(self):
        if os.uname().sysname == "Darwin":
            # Get both RSSI and noise values on macOS
            rssi_output = self._run_command("/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -I | grep 'agrCtlRSSI' | awk '{print $2}'")
            noise_output = self._run_command("/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -I | grep 'agrCtlNoise' | awk '{print $2}'")
            
            try:
                rssi = int(rssi_output)
                noise = int(noise_output)
                
                # Calculate SNR (Signal-to-Noise Ratio)
                snr = rssi - noise
                # Calibrated to your device: SNR of 20 or higher = 100%
                if snr >= 20:
                    signal_strength = 100
                elif snr <= 5:  # Very poor SNR
                    signal_strength = 0
                else:
                    # Linear scaling between SNR 5 (0%) and SNR 20 (100%)
                    signal_strength = (snr - 5) * (100 / 15)
                return int(signal_strength)
            except:
                pass  # Fall back to basic RSSI calculation below
        
        # For Linux or fallback for macOS if SNR calculation fails
        try:
            if os.uname().sysname == "Darwin":
                wifi_output = rssi_output  # Reuse already fetched RSSI
            else:
                wifi_output = self._run_command("iwconfig 2>/dev/null | grep -i --color 'signal level' | awk '{print $4}' | cut -d'=' -f2")
            
            rssi = int(wifi_output)
            
            # Improved scaling that better matches full bars on devices
            # Most devices show full bars around -55 to -50 dBm
            if rssi >= -50:
                signal_strength = 100
            elif rssi <= -100:
                signal_strength = 0
            else:
                # Linear scaling between -100 dBm (0%) and -50 dBm (100%)
                signal_strength = 2 * (rssi + 100)
            
            return int(signal_strength)
        except:
            return 50  # Default to 50% if an error occurs

    def calculate_quality(self, ping, jitter, packet_loss, wifi_strength):
        if ping is None:
            return 0, 0

        ping_threshold, jitter_threshold = 200, 100
        strength = 100 - ((ping / ping_threshold) * 100) - packet_loss
        strength = (strength + wifi_strength) / 2

        jitter_effect = (jitter / jitter_threshold) * 100
        if jitter > jitter_threshold:
            jitter_effect = 50 + (jitter_threshold / jitter) * 50

        stability = 100 - jitter_effect - packet_loss
        stability = (stability + wifi_strength) / 2

        return max(0, min(100, round(strength, 2))), max(0, min(100, round(stability, 2)))

    def save_to_db(self, timestamp, ssid, ping, jitter, packet_loss, wifi_strength, strength, stability, has_internet):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO internet_quality VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, ssid, ping, jitter, packet_loss, wifi_strength, strength, stability, has_internet))
        conn.commit()
        conn.close()
    def get_last_n_average(self, minutes):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT AVG(ping), AVG(jitter), AVG(packet_loss), AVG(wifi_strength), AVG(strength), AVG(stability) 
            FROM internet_quality WHERE timestamp >= datetime('now', '-' || ? || ' minutes') AND ssid = ?
        """, (minutes, self.current_ssid))
        averages = cursor.fetchone()
        conn.close()
        return tuple(0 if v is None else v for v in averages)
    def has_internet(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT has_internet FROM internet_quality WHERE ssid=? ORDER BY timestamp DESC LIMIT 1",(self.current_ssid,))
        result = cursor.fetchone()
        conn.close()
        return result is not None and result[0] == 1

    def notify_subscribers(self, message):
        """Notify all subscribed consumers via socket communication."""
        message = json.dumps(message)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(message.encode(), ("127.0.0.1", self.socket_port))

    def log_results(self):
        ping, jitter, packet_loss = self.get_ping_info()
        wifi_strength = self.get_wifi_signal_strength()
        ssid = self.get_wifi_ssid()
        has_internet = 1 if ping is not None else 0

        if has_internet != self.last_internet_status:
            if has_internet:
                self.notify_subscribers({
                    "type": "internet_available",  
                    "has_wifi":wifi_strength>1,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    
                                                         
                })
            else:
                self.notify_subscribers({
                    "type": "internet_unavailable",
                    "has_wifi":wifi_strength>1,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            self.last_internet_status = has_internet

        if not has_internet:
            for callback in self.subscribers:
                callback()
            strength, stability = 0, 0
        else:
            strength, stability = self.calculate_quality(ping, jitter, packet_loss, wifi_strength)
        data={
            "type": "internet_info",  
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),                                
            "wifi_strength": wifi_strength,
            "strength": strength,
            "stability": stability,
            "has_internet": has_internet,
            "has_wifi":wifi_strength>1
            }
        
                                                

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save_to_db(timestamp,ssid,ping, jitter, packet_loss, wifi_strength, strength, stability, has_internet)
        log_entry = f"{timestamp} | Ping: {ping if ping is not None else 'N/A'}ms | Jitter: {jitter if jitter is not None else 'N/A'}ms | Packet Loss: {packet_loss if packet_loss is not None else 'N/A'}% | WiFi Strength: {wifi_strength}% | Strength: {strength}% | Stability: {stability}% | Internet: {'Yes' if has_internet else 'No'}"
        print(log_entry)
        averages = self.get_last_n_average(10)
        self.notify_subscribers(averages)
        print(json.dumps(averages,indent=4))
        

    async def monitor(self):
        """Continuously monitors internet quality at a fixed interval."""
        while True:
            self.current_ssid = self.get_wifi_ssid()
            self.log_results()
            await asyncio.sleep(self.check_interval)

if __name__ == "__main__":
    monitor = InternetQualityMonitor()
    asyncio.run(monitor.monitor())
