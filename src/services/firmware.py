import os
import json
import shutil
from time import sleep
import hashlib
import requests
from typing import Callable
import pyzipper
import subprocess
import configparser
from .registration_service import DeviceManager

class FirmwareUpdater:
    def __init__(self, config_path):
        self.config_path = config_path
        self.config = configparser.ConfigParser()
        self.config.read(config_path)
        self.base_dir = os.path.expanduser("~/.qbox_app")

        # Paths (fully dynamic from config)
        self.zip_path = self.config.get("FIRMWARE_MANAGEMENT", "zip_path_dir", fallback="/tmp/update.zip")
        self.extract_path = self.config.get("FIRMWARE_MANAGEMENT", "extract_path_dir", fallback="/tmp/extracted")

        # Server settings
        self.version_url = self.config.get("FIRMWARE_MANAGEMENT", "version_url")
        self.update_url = self.config.get("FIRMWARE_MANAGEMENT", "update_url")

        # Security settings
        self.zip_password = self.config.get("FIRMWARE_MANAGEMENT", "zip_password")
        self.device_id = self.config.get("DEVICE_SETTINGS", "device_id")

        # Allowed Commands for installation.json
        self.allowed_commands = {"mv", "cp"}

    def get_current_version(self):
        return self.config.get("FIRMWARE_MANAGEMENT", "current_version", fallback=None)

    def update_current_version(self, version):
        self.config.set("FIRMWARE_MANAGEMENT", "current_version", version)
        self.config.set("FIRMWARE_MANAGEMENT", "next_version", version)
        self._save_config()

    def save_hash_to_config(self, file_path):
        file_hash = self.calculate_file_hash(file_path)
        self.config.set("FIRMWARE_MANAGEMENT", "expected_hash", file_hash)
        self.config.set("FIRMWARE_MANAGEMENT", "expected_hash", file_hash)
        self._save_config()

    def _save_config(self):
        with open(self.config_path, "w") as configfile:
            self.config.write(configfile)

    def get_remote_version_and_hash(self):
        try:
            response = requests.get(self.version_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("version"), data.get("hash")
        except Exception as e:
            print(f"Failed to fetch remote version and hash: {e}")
            return None, None

    def download_file(self):
        print(f"Downloading update from {self.update_url}...")
        response = requests.get(self.update_url, stream=True)
        response.raise_for_status()

        with open(self.zip_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)

        print("Download complete.")

    def calculate_file_hash(self, file_path, algo="sha256"):
        hasher = hashlib.new(algo)
        with open(file_path, "rb") as file:
            while chunk := file.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()

    def extract_zip(self):
        print(f"Extracting {self.zip_path}...")
    
        # Create temp directory for config backup
        import tempfile
        import os
        import shutil
        
        tmp_dir = tempfile.mkdtemp()
      
        tmp_config_path = os.path.join(tmp_dir, "config.json")
        
        # Backup existing config if it exists
        if os.path.exists(self.config_path):
            print(f"Backing up existing config to {tmp_config_path}")
            shutil.copy2(self.config_path, tmp_config_path)
        
        # Extract the zip file
        with pyzipper.AESZipFile(self.zip_path, 'r') as zip_ref:
            zip_ref.pwd = self.zip_password.encode('utf-8')
            zip_ref.extractall(self.extract_path)
        
        # Restore the original config file if it was backed up
        if os.path.exists(tmp_config_path):
            print(f"Restoring original config file")
            shutil.copy2(tmp_config_path, self.config_path)
        
        # Clean up temp directory
        shutil.rmtree(tmp_dir)
        
        print(f"Extraction complete to {self.extract_path}")

    def process_instructions(self):
        instructions_file = os.path.join(self.extract_path,"update_firmware", "installation.json")
        
        if not os.path.exists(instructions_file):
            print("installation.json not found — skipping installation.")
            return

        with open(instructions_file, "r") as file:
            instructions = json.load(file)
        base_dir =instructions.get("base_dir", None)
        if base_dir:
            self.base_dir = os.path.expanduser(base_dir)
        
        config_file = os.path.expanduser(f"{self.base_dir}/config/config.ini")
        tmp_config = "/tmp/firmware_update.ini"
        
        print(f"Config File {config_file}")
        if os.path.isfile(config_file):
            shutil.copy2(config_file,tmp_config)
            print(f"Copied '{config_file}' to '{tmp_config}'")
            
        # Run optional global pre-commands
        for cmd in instructions.get("pre", []):
            self.execute_command(cmd)

        for folder, details in instructions.items():
            if folder in {"pre", "post","base_dir"}:  # Skip global commands
    
                continue

            cmd = details.get("cmd")
            destination = details.get("destination","").replace("~",self.base_dir)
            print(f"Destination {destination}")

            if cmd not in self.allowed_commands:
                print(f"Invalid command '{cmd}', skipping folder '{folder}'")
                continue

            source_path = os.path.join(self.extract_path,"update_firmware", folder)
            if not os.path.exists(source_path):
                print(f"Source folder '{folder}' missing — creating it.")
                os.makedirs(source_path, exist_ok=True)

            os.makedirs(destination, exist_ok=True)

            for item in os.listdir(source_path):
               
                src = os.path.join(source_path, item)
                dst = os.path.join(destination, item)

                if cmd == "mv":
                    if os.path.isdir(src):
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, dst)
                    
                    print(f"Moved '{src}' to '{dst}'")
                elif cmd == "cp":
                    if os.path.isdir(src):
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, dst)
                    print(f"Copied '{src}' to '{dst}'")

            for then_cmd in details.get("then", []):
                self.execute_command(then_cmd)
                
        if os.path.exists(tmp_config):
            shutil.copy2(tmp_config,config_file)
            os.remove(config_file)
            print(f"Copied '{config_file}' to '/tmp/firmware_update.ini'")
        # Run optional global post-commands
        for cmd in instructions.get("post", []):
            self.execute_command(cmd)
        

    @staticmethod
    def execute_command(cmd):
        print(cmd)
        try:
            
           
            print(f"Running: {cmd}")
            subprocess.run(cmd, check=True)
            print(f"Command '{cmd}' completed.")
        except subprocess.CalledProcessError as e:
            print(f"Command '{cmd}' failed: {e}")

    def cleanup(self):
        if os.path.exists(self.zip_path):
            os.remove(self.zip_path)
        if os.path.exists(self.extract_path):
            # shutil.rmtree(self.extract_path)
            pass
    def notify_server(self):
        device = DeviceManager()
        device.notify_upgrade()
    def run(self,callback:Callable = None):
        print("Starting firmware update process...")
        if callable(callback):
            callback([["Update","Starting.."]])
        current_version = self.get_current_version()
        remote_version, remote_hash = self.get_remote_version_and_hash()

        if not remote_version or not remote_hash:
            print("Could not fetch version or hash — exiting.")
            if callable(callback):
                callback([["Update","Network Error"]])
            return

        print(f"Current version: {current_version}")
        print(f"Remote version: {remote_version}")

        if current_version == remote_version:
            print("Firmware is already up-to-date.")
            if callable(callback):
                callback([["Version","Current"]])
            return

        print("New version found — downloading and verifying...")

        try:
            self.download_file()

            calculated_hash = self.calculate_file_hash(self.zip_path)
            if calculated_hash != remote_hash:
                print(f"Hash mismatch! Expected {remote_hash}, got {calculated_hash}")
                return

            print("Hash verified successfully.")
            if callable(callback):
                callback([["Upgrading to",f"v{remote_version}"]])
            self.extract_zip()
            self.process_instructions()
            self.update_current_version(remote_version)

            # Save the verified hash to config (audit trail)
            self.save_hash_to_config(self.zip_path)
            self.notify_server()
            if callable(callback):
                callback([["Updated",f"{remote_version}"],["Wait","Restarting"]],True)
                sleep(5)
                cmd = ["sudo", "supervisorctl", "restart", "qbox:*"]
                self.execute_command(cmd)
            print(f"Update successful — device now at version {remote_version}")
        except Exception as e:
            print(f"Update failed: {e}")
        finally:
            self.cleanup()
            print("Cleanup complete.")
