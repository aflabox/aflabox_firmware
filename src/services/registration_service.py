import os
import platform
import socket
import subprocess
import psutil
import socket
from datetime import datetime
from services import gps_service,battery_service
from utils.helpers import get_last_known_location,get_last_known_battery
import pytz
import json
import requests
import logging
from  utils.helpers import update_config,read_config,create_qr_on_custom_image

class DeviceManager:
    """
    A class to manage device registration, configuration and system updates.
    """
    

    API_BASE_URL = "https://api.aflabox.ai"
    
    def __init__(self,update_hostname=False, log_level=logging.INFO):
        """
        Initialize the DeviceManager with logging setup.
        
        Args:
            log_level: The logging level (default: logging.INFO)
        """
        # Setup logging
        self.setup_logging(log_level)
        self.update_hostname=update_hostname
        self.logger = logging.getLogger('DeviceManager')
        
    def setup_logging(self, log_level):
        """
        Configure logging for the application.
        
        Args:
            log_level: The logging level to use
        """
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('device_manager.log')
            ]
        )
    
    
    def _run_command(self, command, shell=False):
        """
        Helper method to run shell commands safely.
        
        Args:
            command: The command to run (list or string)
            shell: Whether to use shell execution
            
        Returns:
            tuple: (success, output)
        """
        try:
            if shell:
                result = subprocess.run(command, capture_output=True, text=True, shell=True, check=True)
            else:
                result = subprocess.run(command, capture_output=True, text=True, check=True)
            return True, result.stdout.strip()
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.SubprocessError) as e:
            self.logger.warning(f"Command execution failed: {str(e)}")
            return False, f"Error: {str(e)}"
    
    def get_device_details(self):
        """
        Collect and return comprehensive device information.
        
        Returns:
            dict: Device information dictionary
        """
        try:
            # OS Name and Version
            os_name = platform.system()
            os_version = platform.release()
            pretty_name = platform.version()
    
            # Hardware Info
            hardware_info = platform.machine()
    
            # Serial Number
            serial_number = "Unknown"
            try:
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if line.startswith("Serial"):
                            serial_number = line.split(":")[1].strip()
            except FileNotFoundError:
                self.logger.warning("Could not read CPU info file")
    
            # Firmware Version
            firmware_version = read_config("FIRMWARE_MANAGEMENT","current_version")
           
    
            # UUID (Short and Long Format)
            short_uuid = "Unknown"
            uuid = "Unknown"
            
            success, short_uuid_output = self._run_command(
                ["lsblk", "-o", "UUID", "-n", "/dev/mmcblk0p1"]
            )
            if success:
                short_uuid = short_uuid_output
            
            success, uuid_output = self._run_command(
                ["lsblk", "-o", "UUID", "-n", "/dev/mmcblk0p2"]
            )
            if success:
                uuid = uuid_output
    
            # Timezone
            timezone = "Unknown"
            try:
                timezone = datetime.now(pytz.timezone('Etc/UTC')).astimezone().tzname()
            except Exception as e:
                self.logger.warning(f"Could not determine timezone: {str(e)}")
    
            # MAC Address
            mac_address = "Unknown"
            for iface in ["eth0", "wlan0"]:
                path = f"/sys/class/net/{iface}/address"
                if os.path.exists(path):
                    try:
                        with open(path, "r") as f:
                            mac_address = f.read().strip()
                            break
                    except Exception as e:
                        self.logger.warning(f"Could not read MAC address from {iface}: {str(e)}")

            # IP Address (robust fallback method)
            ip_address = "Unknown"
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.connect(("8.8.8.8", 80))  # No actual packet is sent
                    ip_address = s.getsockname()[0]
            except socket.error as e:
                self.logger.warning(f"Could not determine IP address: {str(e)}")
    
            # Uptime
            uptime = "Unknown"
            try:
                with open("/proc/uptime", "r") as f:
                    uptime_seconds = float(f.readline().split()[0])
                    uptime = str(datetime.utcfromtimestamp(uptime_seconds).strftime("%H:%M:%S"))
            except FileNotFoundError:
                self.logger.warning("Could not read uptime from proc file")
    
            # Disk Usage
            try:
                disk_usage = psutil.disk_usage('/')
                disk_total = f"{disk_usage.total / (1024 ** 3):.2f}GB"
                disk_used = f"{disk_usage.used / (1024 ** 3):.2f}GB"
                disk_free = f"{disk_usage.free / (1024 ** 3):.2f}GB"
            except Exception as e:
                self.logger.warning(f"Could not determine disk usage: {str(e)}")
                disk_total = "Unknown"
                disk_used = "Unknown" 
                disk_free = "Unknown"
    
            # Device name based on UUID
            device_name = f"Aflabox-{short_uuid}"
            
            # Current timestamp in ISO format
            current_time = datetime.now().isoformat()
            geo =battery= {}
            try:
      
               geo = get_last_known_location()
            except Exception:
                pass
            try:
                battery = get_last_known_battery()
            except Exception:
                pass
            
            
            # Formatted JSON Output
            device_info = {
                "name": device_name,
                "device_version": pretty_name,
                "firmware_version": firmware_version,
                "device_type": hardware_info,
                "serial_number": serial_number,
                "description": "Device details and system information",
                "is_active": True,
                "last_lat": geo.latitude if geo else 0.00,
                "last_long": geo.longitude if geo else 0.00,
                "last_bat_level": battery["BatteryPercentage"] if "BatteryPercentage" in battery else 0.00,
                "ip_address": str(ip_address),
                "mac_address": mac_address,
                "sold_date": current_time,
                "status": "active",
                "inventory_status": "inventory",
                "cost_currency": "USD",
                "cost_price": 0,
                "config": {
                    "os_name": os_name,
                    "os_version": os_version,
                    "short_uuid": short_uuid,
                    "long_uuid": uuid,
                    "timezone": timezone,
                    "uptime": uptime,
                    "disk_total": disk_total,
                    "disk_used": disk_used,
                    "disk_free": disk_free,
                }
            }
            print(device_info)
            self.logger.info("Device details collected successfully")
            return device_info
    
        except Exception as e:
            self.logger.error(f"Error collecting device details: {str(e)}")
            return {"error": str(e)}
    
    def update_system_hostname(self, new_hostname):
        """
        Update the system's hostname.
        
        Args:
            new_hostname: The new hostname to set
            
        Returns:
            bool: True if hostname update was successful, False otherwise
        """
        current_hostname = socket.gethostname()
        if current_hostname != new_hostname:
            try:
                # Write the new hostname to /etc/hostname
                with open("/etc/hostname", "w") as hostname_file:
                    hostname_file.write(new_hostname)
                
                # Update /etc/hosts
                with open("/etc/hosts", "r") as hosts_file:
                    lines = hosts_file.readlines()
                
                with open("/etc/hosts", "w") as hosts_file:
                    for line in lines:
                        if "127.0.1.1" in line:
                            hosts_file.write(f"127.0.1.1\t{new_hostname}\n")
                        else:
                            hosts_file.write(line)
    
                # Apply the new hostname using hostnamectl
                success, output = self._run_command(f"sudo hostnamectl set-hostname {new_hostname}", shell=True)
                suc_cess, output = self._run_command(f"sudo systemctl restart systemd-hostnamed", shell=True)
                if not success:
                    self.logger.error(f"Failed to set hostname: {output}")
                    return False
                    
                self.logger.info(f"Hostname updated to {new_hostname}")
                return True
                
            except Exception as e:
                self.logger.error(f"Error updating hostname: {str(e)}")
                return False
        else:
            self.logger.info("Hostname is already set correctly")
            return True
            
    def assign_user(self, device_id):
        """
        Assign a user to the device.
        
        Args:
            device_id: The device ID to assign
            
        Returns:
            bool: True if assignment was successful, False otherwise
        """
        try:
            url = f"{self.API_BASE_URL}/device/assign/user"
            
            # Set headers
            headers = {
                "Content-Type": "application/json"
            }
            
            # Prepare data payload
            data = {
                "user_id": 1,
                "device_id": device_id,
                "assigned_date": datetime.now().isoformat()
            }
            
            # Send the POST request
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code in (200, 201):
                self.logger.info(f"Device {device_id} assigned to user successfully")
                return True
            else:
                self.logger.error(f"Device assignment failed with status code: {response.status_code}")
                self.logger.debug(f"Response: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error during user assignment request: {str(e)}")
            return False
    def notify_upgrade(self):
        try:
            device_info = self.get_device_details()
            if "error" in device_info:
                return {"error": f"Failed to collect device details: {device_info['error']}"}
             # Define the API endpoint
            code = read_config("DEVICE_SETTINGS","device_id")
            url = f"{self.API_BASE_URL}/device/{code}"
            # Set headers
            headers = {
                "Content-Type": "application/json"
            }
            
           
            keys = ['last_lat',"name", 'last_lat','last_bat_level','mac_address','serial_number','device_type','firmware_version','device_version']

            subset = {k: device_info[k] for k in keys if k in device_info}

        
            # Send the POST request
            response = requests.put(url, json=subset, headers=headers)
    
            # Check if request was successful
            if response.status_code not in (200, 201):
                error_msg = f"API request failed with status code: {response.status_code}-{response.text}"
                self.logger.error(error_msg)
                self.logger.debug(f"Response: {response.text}")
                return {"error": error_msg}
                
            # Parse response
            result = response.json()
            return result
            
            
        except Exception as e:
            error_msg = f"Error during device registration: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg}
        
    def register_device(self):
        """
        Register the device with the API and update local configuration.
        
        Returns:
            dict: The response from the API with device details,
                  or an error dictionary if registration failed
        """
        try:
            # Get device details
            device_info = self.get_device_details()
            if "error" in device_info:
                return {"error": f"Failed to collect device details: {device_info['error']}"}
    
            # Define the API endpoint
            url = f"{self.API_BASE_URL}/device/add"
    
            # Set headers
            headers = {
                "Content-Type": "application/json"
            }
    
            # Send the POST request
            response = requests.post(url, json=device_info, headers=headers)
    
            # Check if request was successful
            if response.status_code not in (200, 201):
                error_msg = f"API request failed with status code: {response.status_code}-{response.text}"
                self.logger.error(error_msg)
                self.logger.debug(f"Response: {response.text}")
                return {"error": error_msg}
                
            # Parse response
            result = response.json()
            
            # Extract device details
            device_name = result.get("name", "Unknown")
            device_id = result.get("id", "Unknown")
            status = result.get("status", "Unknown")
            uuid = result.get("guid", "Unknown")
            serial_number = result.get("serial_number", "Unknown")
            current_firmware = result.get("current_firmware",None)
            next_firmware = result.get("next_firmware", None)
            current_timezone= result.get("next_firmware", None)
            number_of_battery=2
            battery_capacity=number_of_battery*2500
            try:
               config = result.get("config", {})
               number_of_battery = config.get("number_of_battery",2)
               battery_capacity = config.get("battery_capacity",battery_capacity)
            except Exception:
                pass
            
            
            # Log the successful registration
            self.logger.info(f"Device registered successfully with ID: {device_id}")
            
            # Assign user to device
            assignment_success = self.assign_user(device_id)
            if not assignment_success:
                self.logger.warning(f"User assignment failed for device {device_id}")
            
            # Update configuration
            config_success = update_config(
                section="DEVICE_SETTINGS",
                serial_assigned=True,
                device_name=device_name,
                serial_number=serial_number,
                device_id=device_id,
                current_firmware=current_firmware,
                next_firmware=next_firmware,
                current_timezone=current_timezone,
                number_of_battery=number_of_battery,
                battery_capacity=battery_capacity
                
            )
            
            if not config_success:
                self.logger.warning("Failed to update device configuration")
            
            # Update hostname
            if self.update_hostname:
                hostname_success = self.update_system_hostname(f"qbox{device_id}")
                if not hostname_success:
                    self.logger.warning(f"Failed to update hostname to qbox{device_id}")
            
            # Create a dictionary with device details
            details = {
                "Device Name": device_name,
                "Device ID": device_id,
                "Status": status,
                "UUID": uuid,
                "Serial Number": serial_number
            }
            
            # # Save details to JSON file
            # file_name = "device_details.json"
            # with open(file_name, "w") as json_file:
            #     json.dump(details, json_file, indent=4)
                
            # self.logger.info(f"Device details saved to {file_name}")
            
            # Return the device details
            return details
    
        except Exception as e:
            error_msg = f"Error during device registration: {str(e)}"
            self.logger.error(error_msg)
            return {"error": error_msg}


