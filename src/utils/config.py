import os
import logging
import configparser
from datetime import datetime


class ConfigManager:
    """
    Configuration manager for the camera system using INI format.
    Loads configuration from an INI file and provides access to component-specific configurations.
    """
    
    def __init__(self, config_path='config.ini'):
        """
        Initialize the configuration manager.
        
        Args:
            config_path (str): Path to the INI configuration file
        """
        self.config_path = config_path
        self.config = configparser.ConfigParser()
        self.logger = self._setup_logging()
        
        # Load configuration
        self.load_config()
    
    def _setup_logging(self):
        """Set up logging for the configuration manager."""
        log_dir = 'logs'
        os.makedirs(log_dir, exist_ok=True)
        
        logger = logging.getLogger('ConfigManager')
        logger.setLevel(logging.INFO)
        
        # Create handlers if they don't exist
        if not logger.handlers:
            log_filename = os.path.join(log_dir, f'config_{datetime.now().strftime("%Y%m%d")}.log')
            file_handler = logging.FileHandler(log_filename)
            console_handler = logging.StreamHandler()
            
            # Create formatter and add it to the handlers
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            # Add the handlers to the logger
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
        
        return logger
    
    def load_config(self):
        """Load configuration from the INI file."""
        try:
            if os.path.exists(self.config_path):
                self.config.read(self.config_path)
                self.logger.info(f"Configuration loaded from {self.config_path}")
            else:
                self.logger.warning(f"Configuration file {self.config_path} not found, using defaults")
                self._set_default_config()
                # Save default configuration
                self.save_config()
        except Exception as e:
            self.logger.error(f"Error loading configuration: {str(e)}")
            self._set_default_config()
    
    def save_config(self):
        """Save the current configuration to the INI file."""
        try:
            # Ensure directory exists
            config_dir = os.path.dirname(self.config_path)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir)
                
            with open(self.config_path, 'w') as f:
                self.config.write(f)
            self.logger.info(f"Configuration saved to {self.config_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving configuration: {str(e)}")
            return False
    
    def get_camera_controller_config(self):
        """
        Get configuration for the CameraController.
        
        Returns:
            dict: Camera controller configuration
        """
        if 'CAMERA_CONTROLLER' not in self.config:
            self._set_section_defaults('CAMERA_CONTROLLER')
        
        camera_config = {}
        
        # Basic settings
        camera_config['imgbb_api_key'] = self.config.get('CAMERA_CONTROLLER', 'imgbb_api_key', fallback='')
        camera_config['output_dir'] = self.config.get('CAMERA_CONTROLLER', 'output_dir', fallback='camera_output')
        camera_config['log_level'] = self.config.get('CAMERA_CONTROLLER', 'log_level', fallback='INFO')
        camera_config['stabilization_time'] = self.config.getfloat('CAMERA_CONTROLLER', 'stabilization_time', fallback=1.0)
        
        # Convert resolution settings to tuples
        camera_config['default_resolution'] = (
            self.config.getint('CAMERA_CONTROLLER', 'default_resolution_width', fallback=4056),
            self.config.getint('CAMERA_CONTROLLER', 'default_resolution_height', fallback=3040)
        )
        
        camera_config['thumbnail_resolution'] = (
            self.config.getint('CAMERA_CONTROLLER', 'thumbnail_resolution_width', fallback=1024),
            self.config.getint('CAMERA_CONTROLLER', 'thumbnail_resolution_height', fallback=1024)
        )
        
        # UV and white LED intensities
        camera_config['uv_intensity'] = [
            self.config.getfloat('CAMERA_CONTROLLER', 'uv_intensity_led1', fallback=0.7),
            self.config.getfloat('CAMERA_CONTROLLER', 'uv_intensity_led2', fallback=0.1)
        ]
        
        camera_config['white_intensity'] = self.config.getfloat('CAMERA_CONTROLLER', 'white_intensity', fallback=0.9)
        
        # Camera presets
        camera_config['camera_presets'] = self._get_camera_presets()
        
        return camera_config
    
    def _get_camera_presets(self):
        """
        Get camera presets from configuration.
        
        Returns:
            dict: Camera presets
        """
        presets = {}
        
        # Default preset
        if 'CAMERA_PRESET_DEFAULT' in self.config:
            presets['default'] = {
                'ExposureTime': self.config.getint('CAMERA_PRESET_DEFAULT', 'exposure_time', fallback=50000),
                'AnalogueGain': self.config.getfloat('CAMERA_PRESET_DEFAULT', 'analogue_gain', fallback=3.0),
                'AfMode': self.config.getint('CAMERA_PRESET_DEFAULT', 'af_mode', fallback=0),
                'LensPosition': self.config.getfloat('CAMERA_PRESET_DEFAULT', 'lens_position', fallback=6.8)
            }
        else:
            # Default preset values
            presets['default'] = {
                'ExposureTime': 50000,
                'AnalogueGain': 3.0,
                'AfMode': 0,
                'LensPosition': 6.8
            }
        
        # Bright preset
        if 'CAMERA_PRESET_BRIGHT' in self.config:
            presets['bright'] = {
                'ExposureTime': self.config.getint('CAMERA_PRESET_BRIGHT', 'exposure_time', fallback=30000),
                'AnalogueGain': self.config.getfloat('CAMERA_PRESET_BRIGHT', 'analogue_gain', fallback=2.0),
                'AfMode': self.config.getint('CAMERA_PRESET_BRIGHT', 'af_mode', fallback=0),
                'LensPosition': self.config.getfloat('CAMERA_PRESET_BRIGHT', 'lens_position', fallback=6.8)
            }
        else:
            # Default bright preset values
            presets['bright'] = {
                'ExposureTime': 30000,
                'AnalogueGain': 2.0,
                'AfMode': 0,
                'LensPosition': 6.8
            }
        
        # Dark preset
        if 'CAMERA_PRESET_DARK' in self.config:
            presets['dark'] = {
                'ExposureTime': self.config.getint('CAMERA_PRESET_DARK', 'exposure_time', fallback=80000),
                'AnalogueGain': self.config.getfloat('CAMERA_PRESET_DARK', 'analogue_gain', fallback=4.0),
                'AfMode': self.config.getint('CAMERA_PRESET_DARK', 'af_mode', fallback=0),
                'LensPosition': self.config.getfloat('CAMERA_PRESET_DARK', 'lens_position', fallback=6.8)
            }
        else:
            # Default dark preset values
            presets['dark'] = {
                'ExposureTime': 80000,
                'AnalogueGain': 4.0,
                'AfMode': 0,
                'LensPosition': 6.8
            }
        
        return presets
    
    def get_queue_service_config(self):
        """
        Get configuration for the QueueFileService.
        
        Returns:
            dict: Queue service configuration
        """
        if 'QUEUE_FILE_SERVICE' not in self.config:
            self._set_section_defaults('QUEUE_FILE_SERVICE')
        
        queue_config = {}
        
        # Basic settings
        queue_config['db_path'] = self.config.get('QUEUE_FILE_SERVICE', 'db_path', fallback='queue_service.json')
        queue_config['log_level'] = self.config.get('QUEUE_FILE_SERVICE', 'log_level', fallback='INFO')
        
        # FTP settings
        queue_config['ftp_host'] = self.config.get('QUEUE_FILE_SERVICE', 'ftp_host', fallback='localhost')
        queue_config['ftp_user'] = self.config.get('QUEUE_FILE_SERVICE', 'ftp_user', fallback='anonymous')
        queue_config['ftp_pass'] = self.config.get('QUEUE_FILE_SERVICE', 'ftp_pass', fallback='anonymous@')
        queue_config['ftp_remote_dir'] = self.config.get('QUEUE_FILE_SERVICE', 'ftp_remote_dir', fallback='/uploads')
        queue_config['use_tls'] = self.config.getboolean('QUEUE_FILE_SERVICE', 'use_tls', fallback=True)
        queue_config['verify_ssl'] = self.config.getboolean('QUEUE_FILE_SERVICE', 'verify_ssl', fallback=True)
        
        # Upload settings
        queue_config['max_retries'] = self.config.getint('QUEUE_FILE_SERVICE', 'max_retries', fallback=3)
        queue_config['retry_delay'] = self.config.getint('QUEUE_FILE_SERVICE', 'retry_delay', fallback=5)
        queue_config['worker_threads'] = self.config.getint('QUEUE_FILE_SERVICE', 'worker_threads', fallback=2)
        queue_config['check_interval'] = self.config.getint('QUEUE_FILE_SERVICE', 'check_interval', fallback=60)
        queue_config['retention_days'] = self.config.getint('QUEUE_FILE_SERVICE', 'retention_days', fallback=7)
        
        return queue_config
    
    def get_camera_system_config(self):
        """
        Get configuration for the CameraSystem.
        
        Returns:
            dict: Camera system configuration
        """
        if 'CAMERA_SYSTEM' not in self.config:
            self._set_section_defaults('CAMERA_SYSTEM')
        
        system_config = {}
        
        # Basic settings
        system_config['output_dir'] = self.config.get('CAMERA_SYSTEM', 'output_dir', fallback='camera_output')
        system_config['db_path'] = self.config.get('CAMERA_SYSTEM', 'db_path', fallback='camera_system.json')
        system_config['log_level'] = self.config.get('CAMERA_SYSTEM', 'log_level', fallback='INFO')
        system_config['worker_threads'] = self.config.getint('CAMERA_SYSTEM', 'worker_threads', fallback=2)
        system_config['retention_days'] = self.config.getint('CAMERA_SYSTEM', 'retention_days', fallback=7)
        
        # Available resolutions
        system_config['available_resolutions'] = self._get_available_resolutions()
        
        # Available thumbnail sizes
        system_config['available_thumbnail_sizes'] = self._get_available_thumbnails()
        
        return system_config
    
    def _get_available_resolutions(self):
        """
        Get available resolutions from configuration.
        
        Returns:
            list: List of resolution tuples
        """
        resolutions = []
        
        if 'AVAILABLE_RESOLUTIONS' in self.config:
            for key in self.config['AVAILABLE_RESOLUTIONS']:
                if key.startswith('resolution'):
                    try:
                        value = self.config['AVAILABLE_RESOLUTIONS'][key]
                        width, height = map(int, value.split(','))
                        resolutions.append((width, height))
                    except (ValueError, IndexError):
                        self.logger.warning(f"Invalid resolution format: {value}")
        
        # Add default resolutions if none specified
        if not resolutions:
            resolutions = [
                (4056, 3040),
                (2028, 1520),
                (1920, 1080),
                (1280, 720)
            ]
        
        return resolutions
    
    def _get_available_thumbnails(self):
        """
        Get available thumbnail sizes from configuration.
        
        Returns:
            list: List of thumbnail size tuples
        """
        thumbnails = []
        
        if 'AVAILABLE_THUMBNAILS' in self.config:
            for key in self.config['AVAILABLE_THUMBNAILS']:
                if key.startswith('thumbnail'):
                    try:
                        value = self.config['AVAILABLE_THUMBNAILS'][key]
                        width, height = map(int, value.split(','))
                        thumbnails.append((width, height))
                    except (ValueError, IndexError):
                        self.logger.warning(f"Invalid thumbnail format: {value}")
        
        # Add default thumbnail sizes if none specified
        if not thumbnails:
            thumbnails = [
                (1024, 1024),
                (512, 512),
                (256, 256)
            ]
        
        return thumbnails
    
    def update_config(self, section, key, value):
        """
        Update a specific configuration value.
        
        Args:
            section (str): Configuration section name
            key (str): Configuration key
            value: New value
            
        Returns:
            bool: Success status
        """
        try:
            if section not in self.config:
                self.config[section] = {}
            
            self.config[section][key] = str(value)
            self.save_config()
            self.logger.info(f"Updated config: {section}.{key} = {value}")
            return True
        except Exception as e:
            self.logger.error(f"Error updating configuration: {str(e)}")
            return False
    
    def _set_default_config(self):
        """Set default configuration values."""
        # Camera Controller section
        self._set_section_defaults('CAMERA_CONTROLLER')
        
        # Camera Presets
        self._set_section_defaults('CAMERA_PRESET_DEFAULT')
        self._set_section_defaults('CAMERA_PRESET_BRIGHT')
        self._set_section_defaults('CAMERA_PRESET_DARK')
        
        # Queue File Service
        self._set_section_defaults('QUEUE_FILE_SERVICE')
        
        # Camera System
        self._set_section_defaults('CAMERA_SYSTEM')
        
        # Available Resolutions
        self._set_section_defaults('AVAILABLE_RESOLUTIONS')
        
        # Available Thumbnails
        self._set_section_defaults('AVAILABLE_THUMBNAILS')
    
    def _set_section_defaults(self, section):
        """
        Set default values for a configuration section.
        
        Args:
            section (str): Section name
        """
        if section not in self.config:
            self.config[section] = {}
        
        # Camera Controller defaults
        if section == 'CAMERA_CONTROLLER':
            defaults = {
                'imgbb_api_key': '',
                'output_dir': 'camera_output',
                'default_resolution_width': '4056',
                'default_resolution_height': '3040',
                'thumbnail_resolution_width': '1024',
                'thumbnail_resolution_height': '1024',
                'uv_intensity_led1': '0.7',
                'uv_intensity_led2': '0.1',
                'white_intensity': '0.9',
                'stabilization_time': '1.0',
                'log_level': 'INFO'
            }
            for key, value in defaults.items():
                if key not in self.config[section]:
                    self.config[section][key] = value
        
        # Default camera preset
        elif section == 'CAMERA_PRESET_DEFAULT':
            defaults = {
                'exposure_time': '50000',
                'analogue_gain': '3.0',
                'af_mode': '0',
                'lens_position': '6.8'
            }
            for key, value in defaults.items():
                if key not in self.config[section]:
                    self.config[section][key] = value
        
        # Bright camera preset
        elif section == 'CAMERA_PRESET_BRIGHT':
            defaults = {
                'exposure_time': '30000',
                'analogue_gain': '2.0',
                'af_mode': '0',
                'lens_position': '6.8'
            }
            for key, value in defaults.items():
                if key not in self.config[section]:
                    self.config[section][key] = value
        
        # Dark camera preset
        elif section == 'CAMERA_PRESET_DARK':
            defaults = {
                'exposure_time': '80000',
                'analogue_gain': '4.0',
                'af_mode': '0',
                'lens_position': '6.8'
            }
            for key, value in defaults.items():
                if key not in self.config[section]:
                    self.config[section][key] = value
        
        # Queue File Service defaults
        elif section == 'QUEUE_FILE_SERVICE':
            defaults = {
                'db_path': 'queue_service.json',
                'log_level': 'INFO',
                'ftp_host': 'localhost',
                'ftp_user': 'anonymous',
                'ftp_pass': 'anonymous@',
                'ftp_remote_dir': '/uploads',
                'use_tls': 'true',
                'verify_ssl': 'true',
                'max_retries': '3',
                'retry_delay': '5',
                'worker_threads': '2',
                'check_interval': '60',
                'retention_days': '7'
            }
            for key, value in defaults.items():
                if key not in self.config[section]:
                    self.config[section][key] = value
        
        # Camera System defaults
        elif section == 'CAMERA_SYSTEM':
            defaults = {
                'output_dir': 'camera_output',
                'db_path': 'camera_system.json',
                'log_level': 'INFO',
                'worker_threads': '2',
                'retention_days': '7'
            }
            for key, value in defaults.items():
                if key not in self.config[section]:
                    self.config[section][key] = value
        
        # Available Resolutions defaults
        elif section == 'AVAILABLE_RESOLUTIONS':
            defaults = {
                'resolution1': '4056,3040',
                'resolution2': '2028,1520',
                'resolution3': '1920,1080',
                'resolution4': '1280,720'
            }
            for key, value in defaults.items():
                if key not in self.config[section]:
                    self.config[section][key] = value
        
        # Available Thumbnails defaults
        elif section == 'AVAILABLE_THUMBNAILS':
            defaults = {
                'thumbnail1': '1024,1024',
                'thumbnail2': '512,512',
                'thumbnail3': '256,256'
            }
            for key, value in defaults.items():
                if key not in self.config[section]:
                    self.config[section][key] = value

