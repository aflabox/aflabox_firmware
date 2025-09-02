import os
import subprocess
import sys
import uuid
import time
import socket
import asyncio
import platform
import subprocess
import re
import glob
import configparser
import signal
from datetime import datetime,timezone
from typing import Tuple, Optional, List, Dict, Any
from aiormq.exceptions import ChannelInvalidStateError
from aio_pika.exceptions import AMQPConnectionError, AMQPChannelError
from enum import Enum
import qrcode
from PIL import Image, ImageDraw, ImageFont
import io
from utils.thread_locks import get_db
import json
import aio_pika
from utils.logger import get_logger
import aiohttp
from pathlib import Path
from tinydb import TinyDB, Query
import os
import glob
import psutil
import signal
import time


try:
   from raspi_tools import GPSData
except Exception:
   pass
   

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Directory containing this file
CONFIG_PATH = os.path.abspath(os.path.join(BASE_DIR, "../../config/config.ini"))

logger = get_logger(__name__)


class LightType(Enum):
    """Enumeration for different types of lighting."""
    WHITE = "white"
    UV_365 = "uv_365"
    IR = "infrared"

class StorageUnit(Enum):
    """Enumeration for storage units."""
    BYTES = 1
    KB = 1024
    MB = 1024 * 1024
    GB = 1024 * 1024 * 1024

class DeviceStatus(Enum):
    """Enumeration for device status."""
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    ERROR = "error"
def get_last_known_battery(n=1):
    db = get_db("battery_data.json")
       
    return db.all()[-n:]
def get_last_known_location():
        """Retrieve the last entered GPS data using the metadata last_record_id."""
        try:
            db = get_db("gps_data.json")
            metadata = db.search(Query().type == 'metadata')
            if not metadata:
                print("No last_record_id metadata found.")
                return None

            last_record_id = metadata[0].get('last_record_id')
            if not last_record_id:
                print("last_record_id is missing.")
                return None

            # Retrieve the record with the highest ID
            last_record = db.get(Query().id == last_record_id)
            return GPSData(last_record)
        except Exception as e:
            print(f"Error retrieving GPS data: {e}")
            return None
def safe_run(coro):
    """
    Runs an async coroutine safely, whether inside an existing event loop
    or in a completely new environment (where no loop exists yet).

    - If called inside an async function (event loop is running), it uses `asyncio.create_task()`.
    - If called from synchronous code (no running event loop), it creates a new loop and runs the coroutine.

    This handles both main-thread and worker-thread scenarios.

    :param coro: The coroutine to run.
    """
    try:
        try:
            # Case 1: Called inside a running async context (event loop is already running)
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
        except RuntimeError:
            # Case 2: No event loop (e.g., called from worker thread or sync code)
            asyncio.run(coro)
    except Exception as e:
        logger.exception(f"Failed to safely run coroutine: {e}")


       
        
async def publish_to_exchange(exchange:str,message:dict,routing_key:str,type=aio_pika.ExchangeType.TOPIC, durable=True):
        
       try:
          
            conf =  read_config("RABBITMQ_QUEUE")
       
            connection = await aio_pika.connect_robust(conf['amq_url'])
            async with connection:
                channel = await connection.channel()
                exchange = await channel.declare_exchange(exchange, type, durable=durable)
                
                message_body =json.dumps(message).encode()
                
                message = aio_pika.Message(
                    body=message_body,
                    content_type='application/json',
                    headers={'x-auth': conf.get('QUEUE', 'amq_url')},
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                )
               
                
                res= await exchange.publish(
                    message,
                    routing_key=routing_key
                )
                logger.info(f"Message published {res}")
                return res
                
       except Exception as e:
           logger.error(f"Issue {e}",exc_info=True)
def now():
    return datetime.now(timezone.utc)
           
def generate_reference(length: int = 8) -> str:
    """Generate a unique reference string."""
    return uuid.uuid4().hex[:length].upper()

def get_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.utcnow().isoformat()

def parse_size(size_str: str) -> int:
    """
    Parse size string with unit (e.g., '100MB') to bytes.
    
    Args:
        size_str: String containing size and unit (e.g., '100MB')
        
    Returns:
        int: Size in bytes
        
    Raises:
        ValueError: If the size string is invalid
    """
    size_str = size_str.strip().upper()
    if not size_str:
        raise ValueError("Empty size string")

    # Parse number and unit
    for unit in StorageUnit:
        if size_str.endswith(unit.name):
            try:
                number = float(size_str[:-len(unit.name)])
                return int(number * unit.value)
            except ValueError:
                raise ValueError(f"Invalid number format in size string: {size_str}")

    # If no unit specified, assume bytes
    try:
        return int(float(size_str))
    except ValueError:
        raise ValueError(f"Invalid size format: {size_str}")

async def get_free_space(path: str) -> int:
    """Get free space in bytes for given path."""
    stats = os.statvfs(path)
    return stats.f_frsize * stats.f_bavail
def delete_all_screenshots(directory="screenshots"):
    if os.path.exists(directory):
        # Remove all files inside the directory
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        
        print(f"All files in '{directory}' have been deleted.")
    else:
        print(f"Directory '{directory}' does not exist.")
async def check_internet_connection(timeout: float = 5) -> bool:
    """
    Check internet connectivity by attempting to connect to reliable hosts.
    
    Args:
        timeout: Connection timeout in seconds
        
    Returns:
        bool: True if internet is available, False otherwise
    """
    hosts = ['8.8.8.8', '1.1.1.1']  # Google DNS, Cloudflare DNS
    port = 53  # DNS port

    for host in hosts:
        try:
            async with asyncio.timeout(timeout):
                # Create socket connection
                future = asyncio.get_event_loop().create_connection(
                    lambda: asyncio.Protocol(), host, port)
                await future
                return True
        except (asyncio.TimeoutError, OSError):
            continue
    return False

def get_device_info() -> Dict[str, Any]:
    """Get comprehensive device information."""
    try:
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
    except socket.error:
        hostname = "unknown"
        ip_address = "unknown"

    return {
        "system": platform.system(),
        "node_name": platform.node(),
        "host_name": hostname,
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "ip_address": ip_address,
        "python_version": platform.python_version(),
        "timezone": datetime.now().astimezone().strftime('%Z:%z')
    }

def format_bytes(bytes_: int) -> str:
    """Format bytes into human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_ < 1024:
            return f"{bytes_:.2f}{unit}"
        bytes_ /= 1024
    return f"{bytes_:.2f}PB"

async def ensure_dir(path: str) -> None:
    """Ensure directory exists, create if it doesn't."""
    Path(path).mkdir(parents=True, exist_ok=True)

class RetryDecorator:
    """Decorator for retrying functions with exponential backoff."""
    def __init__(self, max_retries: int = 3, base_delay: float = 1,
                 max_delay: float = 60, exponential: float = 2):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential = exponential

    def __call__(self, func):
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(self.max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < self.max_retries - 1:
                        delay = min(
                            self.base_delay * (self.exponential ** attempt),
                            self.max_delay
                        )
                        await asyncio.sleep(delay)
            raise last_exception
        return wrapper

class RateLimiter:
    """Rate limiter implementation using token bucket algorithm."""
    def __init__(self, rate: float, capacity: int):
        self.rate = rate  # tokens per second
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.monotonic()
        self.lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> bool:
        async with self.lock:
            now = time.monotonic()
            # Add new tokens based on time passed
            elapsed = now - self.last_update
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.rate
            )
            self.last_update = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

class FileRotator:
    """Handles file rotation based on size or time."""
    def __init__(self, base_path: str, max_size: int,
                 max_files: int = 5, base_name: str = ""):
        self.base_path = Path(base_path)
        self.max_size = max_size
        self.max_files = max_files
        self.base_name = base_name

    async def rotate_if_needed(self, current_file: str) -> str:
        """Rotate file if it exceeds max size."""
        if not os.path.exists(current_file):
            return current_file

        if os.path.getsize(current_file) < self.max_size:
            return current_file

        # Rotate existing files
        for i in range(self.max_files - 1, 0, -1):
            old_file = f"{current_file}.{i}"
            new_file = f"{current_file}.{i + 1}"
            if os.path.exists(old_file):
                os.rename(old_file, new_file)

        # Rename current file
        os.rename(current_file, f"{current_file}.1")
        return current_file

# Example usage:
async def example_usage():
    # Generate reference
    ref = generate_reference()
    print(f"Generated reference: {ref}")

    # Check internet
    if await check_internet_connection():
        print("Internet connection available")

    # Parse size
    size_bytes = parse_size("100MB")
    print(f"Parsed size: {format_bytes(size_bytes)}")

    # Use rate limiter
    limiter = RateLimiter(10, 100)  # 10 tokens per second, max 100 tokens
    if await limiter.acquire():
        print("Rate limit not exceeded")

    # Use retry decorator
    @RetryDecorator(max_retries=3)
    async def example_function():
        # Function implementation
        pass

    # Use file rotator
    rotator = FileRotator("/var/log/device", 1024 * 1024)  # 1MB max size
    log_file = await rotator.rotate_if_needed("/var/log/device/current.log")


import subprocess
import sys

def run_sudo_shutdown_no_password():
    """
    Execute sudo shutdown without password prompt
    Assumes the user has NOPASSWD sudo privileges for shutdown
    """
    try:
        # Check the operating system
        if sys.platform.startswith('darwin'):
            # macOS
            subprocess.run(["sudo", "shutdown", "-h", "now"])
            
        elif sys.platform.startswith('linux'):
            # Linux
            subprocess.run(["sudo", "shutdown", "-h", "now"])
            
        elif sys.platform.startswith('win'):
            # Windows (doesn't use sudo)
            subprocess.run(["shutdown", "/s", "/t", "0"])
            
        else:
            print(f"Unsupported operating system: {sys.platform}")
            
    except subprocess.SubprocessError as e:
        print(f"Error executing shutdown command: {e}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")

def update_config(section="DEVICE_SETTINGS", **kwargs):
        """
        Update any section of the config.ini file with provided key-value pairs.
        
        Args:
            section: The section to update (default: "settings")
            **kwargs: Key-value pairs to update in the specified section
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            # Check if the config file exists
            if not os.path.exists(CONFIG_PATH):
                logger.error(f"Configuration file not found at {CONFIG_PATH}")
                raise FileNotFoundError(f"Configuration file not found at {CONFIG_PATH}")
            
            # Create config directory if it doesn't exist
            config_dir = os.path.dirname(CONFIG_PATH)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
                logger.info(f"Created config directory: {config_dir}")
            
            # Initialize the config parser
            config = configparser.ConfigParser()
            
            # Read existing config if file exists
            if os.path.exists(CONFIG_PATH):
                config.read(CONFIG_PATH)
    
            # Ensure the specified section exists
            if section not in config:
                config[section] = {}
                logger.info(f"Created new section: [{section}]")
    
            # Update values if provided
            if not kwargs:
                logger.warning("No values provided for update")
                return False
                
            # Update all provided key-value pairs
            for key, value in kwargs.items():
                config[section][key] = str(value)
                logger.debug(f"Updated [{section}][{key}] = {value}")
    
            # Write the changes back to the file
            with open(CONFIG_PATH, "w") as config_file:
                config.write(config_file)
                
            logger.info(f"Configuration section [{section}] updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error updating configuration: {str(e)}")
            return False
            
def read_config(section=None, key=None):
        """
        Read configuration values from the config.ini file.
        
        Args:
            section: The section to read (if None, returns all sections)
            key: The specific key to read (if None, returns all keys in section)
            
        Returns:
            dict, str, or None: Configuration values or None if not found
        """
        try:
            # Check if the config file exists
            if not os.path.exists(CONFIG_PATH):
                logger.error(f"Configuration file not found at {CONFIG_PATH}")
                return None
            
            # Initialize the config parser
            config = configparser.ConfigParser()
            config.read(CONFIG_PATH)
            
            
            # Return the entire configuration
            if section is None:
                return {s: dict(config[s]) for s in config.sections()}
            
            # Check if the section exists
            if section not in config.sections():
                logger.warning(f"Section [{section}] not found in config")
                return None
                
            # Return the specific key if requested
            if key is not None:
                if key in config[section]:
                    return config[section][key]
                else:
                    # self.logger.warning(f"Key '{key}' not found in section [{section}]")
                    return None
            
            # Return all keys in the section
            return dict(config[section])
            
        except Exception as e:
            # self.logger.error(f"Error reading configuration: {str(e)}")
            return None


def create_qr_with_text(data="https://example.com", 
                       text="QR Code Example",
                       qr_color=(0, 0, 0),
                       bg_color=(255, 255, 255),
                       output_file="qrcode_with_text.png"):
    """
    Create a QR code with text beneath it using Python Pillow
    
    Args:
        data: The data to encode in the QR code
        text: The text to display beneath the QR code
        qr_color: Color of the QR code (RGB tuple)
        bg_color: Background color (RGB tuple)
        output_file: Output filename
    """
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=5,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    # Create QR code image
    qr_img = qr.make_image(fill_color=qr_color, back_color=bg_color).convert('RGB')
    qr_width, qr_height = qr_img.size
    
    # Create a larger image to hold QR code and text
    padding = 5
    text_height = 30
    img_width = qr_width + (2 * padding)
    img_height = qr_height + text_height + (2 * padding)
    
    # Create background image
    background = Image.new('RGBA', (img_width, img_height), bg_color)
    
    # Paste QR code onto background
    qr_position = ((img_width - qr_width) // 2, padding)
    background.paste(qr_img, qr_position)
    
    # Add text beneath QR code
    draw = ImageDraw.Draw(background)
    
    # Try to load a font, fall back to default if not available
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except IOError:
        font = ImageFont.load_default()
    
    # Get text size and position
    text_width = draw.textlength(text, font=font)
    text_position = ((img_width - text_width) // 2, qr_height + padding + 10)
    
    # Draw text
    draw.text(text_position, text, fill=qr_color, font=font)
    
    # Save the image
    background.save(output_file)
    print(f"QR code image saved as {output_file}")
    return background

# Example usage
# if __name__ == "__main__":
#     # Create a QR code with custom data and text
#     qr_image = create_qr_with_text(
#         data="https://github.com/python-pillow/Pillow",
#         text="Python Pillow QR Code - github.com/python-pillow/Pillow",
#         output_file="pillow_qrcode.png"
#     )
    
#     # You can also display the image directly if working in a notebook environment
#     # qr_image.show()


def create_qr_on_custom_image(qr_data,text=None,output_path=None):
    """
    Create a QR code and place it in the middle of a custom background image
    
    Args:
        qr_data: Data to encode in the QR code
        background_image_path: Path to the background image
        output_path: Path to save the final image
        text: Optional text to add beneath the QR code
    """
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    # Create QR code image with transparent background
    qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGBA')
    qr_img=addText(qr_img=qr_img,output_path=output_path,text=text)
    
    return qr_img,qr_img.size
def addText(text,qr_img,output_path=None):
    w,h =qr_img.size
    background = Image.new("RGBA", (w+5, h+10), "white")
    # # Resize QR code to be proportional to background (e.g., 1/3 of the width)
    bg_width, bg_height = background.size
    qr_size = min(bg_width, bg_height) // 3
    qr_img = qr_img.resize((qr_size, qr_size), Image.LANCZOS)
    qr_width, qr_height = qr_img.size
    
    # # Calculate position to place QR code in the center
    position = ((bg_width - qr_width) // 2, (bg_height - qr_height) // 2)
    
    # # Create a new image for the result
    result = background.copy()
    result.paste(qr_img, position, qr_img)
    
    # Add text if provided
    if text:
        draw = ImageDraw.Draw(result)
        try:
            font = ImageFont.truetype("arial.ttf", bg_width // 10)
        except IOError:
            font = ImageFont.load_default()
        
        text_width = draw.textlength(text, font=font)
        text_position = ((bg_width - text_width) // 2, 
                         position[1] + qr_height + 5)
        
        # Add a semi-transparent background behind text for readability
        text_bg = Image.new('RGBA', result.size, (255, 255, 255, 0))
        text_bg_draw = ImageDraw.Draw(text_bg)
        text_bg_rect = (
            text_position[0] - 10,
            text_position[1] - 5,
            text_position[0] + text_width + 10,
            text_position[1] + 20
        )
        text_bg_draw.rectangle(text_bg_rect, fill=(255, 255, 255, 180))
        result = Image.alpha_composite(result, text_bg)
        
        # Draw text on the result
        draw = ImageDraw.Draw(result)
        draw.text(text_position, text, fill=(0, 0, 0, 255), font=font)
    
    # Convert back to RGB and save
    result = result.convert('RGB')
    
    return result
def free_camera_resources():
    current_pid = os.getpid()
    print(f"Freeing camera resources (current PID: {current_pid})...")

    # Find video devices
    video_devices = glob.glob("/dev/video*")
    if not video_devices:
        print("No video devices found.")
        return True

    print(f"Found video devices: {video_devices}")

    safe_pids = set()

    # Scan all processes for open file handles
    for proc in psutil.process_iter(["pid", "name", "open_files"]):
        try:
            if proc.pid == current_pid or proc.pid < 100:  # skip system + self
                continue

            if proc.info["open_files"]:
                for f in proc.info["open_files"]:
                    if f.path and f.path.startswith("/dev/video"):
                        safe_pids.add(proc.pid)
                        break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    print(f"PIDs using camera resources: {list(safe_pids)}")

    # Terminate only camera-related processes
    for pid in safe_pids:
        try:
            proc = psutil.Process(pid)
            pname = proc.name().lower()

            if any(x in pname for x in ["camera", "v4l", "gst", "uvc"]):
                print(f"Sending SIGTERM to process {pid} ({pname})")
                proc.terminate()
                try:
                    proc.wait(timeout=1)  # wait 1s for clean exit
                except psutil.TimeoutExpired:
                    print(f"Process {pid} did not exit, sending SIGKILL")
                    proc.kill()
            else:
                print(f"Skipping process {pid} ({pname}) - not camera related")
        except Exception as e:
            print(f"Error terminating process {pid}: {e}")

    return True
def free_camera_resources__():
    current_pid = os.getpid()
    print(f"Freeing camera resources (current PID: {current_pid})...")
    
    try:
        # Check if any video devices exist
        video_devices = glob.glob("/dev/video*")
        if not video_devices:
            print("No video devices found.")
            return True
            
        print(f"Found video devices: {video_devices}")
        
        # Use fuser to find processes using video devices
        all_pids = set()
        for device in video_devices:
            try:
                # Run fuser without sudo (use sudo in sudoers file if needed)
                result = subprocess.run(
                    ["fuser", device],
                    capture_output=True,
                    text=True
                )
                
                # Parse output (fuser outputs PIDs on stdout separated by spaces)
                if result.stdout:
                    device_pids = [int(pid) for pid in result.stdout.strip().split() if pid.isdigit()]
                    all_pids.update(device_pids)
            except Exception as e:
                print(f"Error checking {device}: {e}")
        
        # Remove current PID from the list
        if current_pid in all_pids:
            all_pids.remove(current_pid)
            
        # Filter out system PIDs (below 100) for safety
        safe_pids = [pid for pid in all_pids if pid > 100]
        
        print(f"PIDs using camera resources: {safe_pids}")
        
        # Attempt to terminate processes gracefully first
        for pid in safe_pids:
            try:
                # Check process name before killing
                proc_name = subprocess.run(
                    ["ps", "-p", str(pid), "-o", "comm="],
                    capture_output=True,
                    text=True
                ).stdout.strip()
                
                # Only kill camera-related processes
                if "camera" in proc_name.lower() or "v4l" in proc_name.lower() or "gst" in proc_name.lower():
                    print(f"Sending SIGTERM to process {pid} ({proc_name})")
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(0.5)  # Give process time to terminate
                else:
                    print(f"Skipping process {pid} ({proc_name}) - not camera related")
            except Exception as e:
                print(f"Error terminating process {pid}: {e}")
                
        # Release V4L2 devices explicitly 
        try:
            subprocess.run(["v4l2-ctl", "--all"], capture_output=True)  # Reset V4L2 state
        except:
            pass  # Ignore if v4l2-ctl is not available
            
        return True
        
    except Exception as e:
        print(f"Error freeing camera resources: {e}")
        return False

def free_camera_resources_():
    """
    Check for and kill processes using camera resources except for the current process.
    Returns True if successful, False otherwise.
    """
    

    current_pid = os.getpid()
    print(f"Freeing camera resources (current PID: {current_pid})...")
    
    try:
        # First, check if any video devices exist
        video_devices = glob.glob("/dev/video*")
        if not video_devices:
            print("No video devices found.")
            return True
            
        print(f"Found video devices: {video_devices}")
        
        # Use shell=True to allow wildcard expansion or pass the list of devices directly
        result = subprocess.run(
            ["sudo", "fuser", "-v"] + video_devices,
            capture_output=True,
            text=True
        )
        
        # Print output for debugging
        print("fuser command stdout:")
        print(result.stdout)
        print("fuser command stderr:")
        print(result.stderr)
            
        # Extract PIDs from stdout (space-separated numbers)
        pids = set()
        if result.stdout:
            # Split by whitespace and convert to integers
            for pid_str in result.stdout.strip().split():
                if pid_str.isdigit():
                    pid = int(pid_str)
                    if pid != current_pid:
                        pids.add(pid)
        
        # Also try to extract PIDs from stderr as a backup
        if result.stderr and not pids:
            # Try to extract PIDs from the stderr table format
            for line in result.stderr.strip().split('\n'):
                if "USER" in line and "PID" in line:
                    continue
                    
                # Look for numbers in the line that could be PIDs
                numbers = re.findall(r'\d+', line)
                for num in numbers:
                    pid = int(num)
                    if pid != current_pid:
                        pids.add(pid)
        
        print(f"PIDs using camera resources: {list(pids)}")
        
        if not pids:
            print("No other processes found using camera resources.")
            return True
            
        # Kill processes using camera
        for pid in pids:
            try:
                # Get process name before killing
                proc_info = subprocess.run(
                    ["ps", "-p", str(pid), "-o", "comm="],
                    capture_output=True,
                    text=True
                )
                process_name = proc_info.stdout.strip()
                print(f"Killing process {pid} ({process_name}) that's using camera resources")
                
                # Kill the process
                kill_result = subprocess.run(
                    ["sudo", "kill", "-9", str(pid)],
                    capture_output=True,
                    text=True
                )
                print(f"Kill command result: {kill_result.stdout}")
                if kill_result.stderr:
                    print(f"Kill command error: {kill_result.stderr}")
                    
            except Exception as e:
                print(f"Error killing process {pid}: {e}")
        
        print("Camera resources should now be free")
        return True
        
    except Exception as e:
        print(f"Error freeing camera resources: {e}")
        import traceback
        traceback.print_exc()
        return False

