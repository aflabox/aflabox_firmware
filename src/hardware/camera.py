import time
import uuid
import os,gc
import json
import zipfile
import logging
from services.test_service import CropTestManager
from datetime import datetime
from models.models import initialize_empty_test
from uuid import uuid4
import requests
from models import models
from PIL import Image
from utils.gpio_helper import MixedPinFactory,GPIOManager

try:
    from gpiozero import Device
    from gpiozero import PWMLED,LED
except Exception:
    pass
try:
   from picamera2 import Picamera2
except Exception:
   from unittest.mock import MagicMock as Picamera2
try:
   from RPi import GPIO
except Exception:
   from .simulation import MockRPiGPIO as GPIO

class CameraController:
    """
    A comprehensive controller for Raspberry Pi Camera operations with UV and white light control.
    
    Features:
    - Configurable image resolution and quality
    - Multiple lighting modes (UV, white)
    - Image thumbnailing
    - Automatic file zipping
    - Detailed performance metrics
    - Optional cloud upload
    """
    
    def __init__(self,device_id,config=None,picamera=None,gpio=None):
        """
        Initialize the camera controller with configurable settings.
        
        Args:
            config (dict, optional): Configuration dictionary with the following optional keys:
                - imgbb_api_key (str): API key for ImgBB image hosting
                - output_dir (str): Directory to store captured images and zip files
                - default_resolution (tuple): Default resolution for capturing images (width, height)
                - thumbnail_resolution (tuple): Default resolution for thumbnails (width, height)
                - uv_intensity (tuple): Intensity values for UV LEDs (led1, led2) - values from 0 to 1
                - white_intensity (float): Intensity value for white  - value from 0 to 1
                - stabilization_time (float): Time to wait for lights to stabilize before capture
                - log_level (str): Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR')
        """
        
        # Set up logging
        self._setup_logging(config.get('log_level', 'INFO') if config else 'INFO')
        self.logger.info("Initializing CameraController")
        
        # Get configuration or use defaults
        self.config = config or {}
        self.crop_test_manager = CropTestManager(config=config)
        # API Key
        self.IMGBB_API_KEY = self.config.get('imgbb_api_key', '')
        self.device_id=device_id
        
        self.uv_led_1 = None
        self.uv_led_2 = None
        self.white_led_1 = None
        self.white_led_2 = None
        # Create the enhanced GPIO manager
        self.gpio_manager = gpio
    
         # Create the mixed factory
        self.factory = MixedPinFactory(self.gpio_manager)
        
        # Initialize pin factories
        self.logger.debug("Setting up GPIO")
        
        # Device.pin_factory = RPiGPIOFactory()
        
       
        
        #  intensity settings
        self.uv_intensity = self.config.get('uv_intensity', (0.7, 0.1))
        self.white_intensity = self.config.get('white_intensity', 1.0)
        self.stabilization_time = self.config.get('stabilization_time', 1.0)
        
        # Turn off all LEDs initially
        self.init_led()
        self.all_off()
        
        # Initialize Picamera2
        self.camera_pre_configured=False
        if picamera:
            self.logger.debug("Reusing camera")
            self.picam2 = picamera
            self.camera_pre_configured=True
        else:
            self.logger.debug("Initializing camera")
            self.picam2 = Picamera2()
            
        
        
        # Resolution settings
        self.default_resolution = self.config.get('default_resolution', (1920, 1080))
        self.thumbnail_resolution = self.config.get('thumbnail_resolution', (1024, 1024))
        
        # Output directory
        self.output_dir = self.config.get('output_dir', 'camera_output')
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Keep track of created files for easy cleanup
        self.created_files = []
        self.captured_images = []
        
        # Camera tuning presets
        self.camera_presets = {
            'default': {
                'ExposureTime': 50000,
                'AnalogueGain': 3.0,
                'AfMode': 0,
                "AwbMode":0,
                "AwbEnable":True,
                'LensPosition': 6.8
            },
            'bright': {
                'ExposureTime': 30000,
                'AnalogueGain': 2.0,
                'AfMode': 0,
                'LensPosition': 6.8
            },
            'dark': {
                'ExposureTime': 80000,
                'AnalogueGain': 4.0,
                'AfMode': 0,
                'LensPosition': 6.8
            }
        }
    def init_led(self):
        self.all_off()
        
        self.factory.use_native_for(7)  # LED will use NativeFactory
        self.factory.use_rpi_for([23,6,24])   
        
        # pin_factory = NativeFactory()
        self.uv_led_1 = PWMLED(23,pin_factory=self.factory)
        self.uv_led_2 = PWMLED(6,pin_factory=self.factory)
        self.white_led_1 = LED(7, pin_factory=self.factory)
        self.white_led_2 = PWMLED(24,pin_factory=self.factory)
        
    def _setup_logging(self, level='INFO'):
        """Set up logging for the camera controller."""
        log_dir = 'logs'
        os.makedirs(log_dir, exist_ok=True)
        
        # Create a logger
        self.logger = logging.getLogger('CameraController')
        self.logger.setLevel(getattr(logging, level))
        
        # Create handlers
        log_filename = os.path.join(log_dir, f'camera_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        file_handler = logging.FileHandler(log_filename)
        console_handler = logging.StreamHandler()
        
        # Create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add the handlers to the logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    def white_off(self):
        """Ensure all LEDs are off."""
        self.logger.debug("Turning off all white LEDs")
       
        try:
            
            for led in [self.white_led_1, self.white_led_2]:
                if led is not None and not led.closed:
                    led.close()
                    
            for pin in [23, 6, 7, 24]:
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW)
            
            
            
        except Exception as e:
            self.logger.error("Error Turning off all LEDs",exc_info=True)
    def uv_off(self):
        """Ensure all LEDs are off."""
        self.logger.debug("Turning off all white LEDs")
       
        try:
            
            for led in [self.uv_led_1, self.uv_led_2]:
                if led is not None and not led.closed:
                    led.close()
                    
            for pin in [23, 6, 7, 24]:
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW)
            
            
            
        except Exception as e:
            self.logger.error("Error Turning off all LEDs",exc_info=True)
              
    def all_off(self):
        """Ensure all LEDs are off."""
        self.logger.debug("Turning off all LEDs")
       
        try:
            
            for led in [self.uv_led_1, self.uv_led_2, self.white_led_1, self.white_led_2]:
                if led is not None and not led.closed:
                    led.close()
                    
            for pin in [23, 6, 7, 24]:
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW)
            
            
            
        except Exception as e:
            self.logger.error("Error Turning off all LEDs",exc_info=True)

        
    def configure_camera(self, resolution=None, preset='default'):
        """
        Configures the camera with the specified resolution and settings preset.
        
        Args:
            resolution (tuple, optional): Resolution as (width, height)
            preset (str, optional): Camera settings preset ('default', 'bright', 'dark')
        """
        if self.camera_pre_configured:
            return
        if resolution is None:
            resolution = self.default_resolution
        
        sensor_width = 4656
        sensor_height = 3496
            
        target_height = 1080
        sensor_aspect_ratio = sensor_width / sensor_height
        scaled_width = int(target_height * sensor_aspect_ratio)
        
        print(f"Using aspect-ratio preserving resolution: {scaled_width}x{target_height} with full FOV")
       
        
        self.logger.info(f"Configuring camera with resolution {resolution} and preset '{preset}'")
       
        config = self.picam2.create_still_configuration(
                                      main={"size": (2048, 1536)},
                                    #   lores={"size": (1920, 1080)},
                                    #   display="lores"
                                    #   main={"size": resolution},
                                      raw={"size": (4656, 3496)},
                                      display=None
                                    )
        self.picam2.configure(config)
        # self.picam2.zoom = (0.0, 0.0, 1.0, 1.0)
        # camera_config = self.picam2.camera_configuration()
        # Apply settings preset
        try:
            preset_settings = self.camera_presets.get(preset, self.camera_presets['default'])
            # preset_settings["ScalerCrop"]=(0, 0, 4656, 2620)
            self.picam2.set_controls(preset_settings)
            self.logger.info(f"Applied camera preset: {preset_settings}")
        except Exception as e:
            self.logger.error(f"Failed to apply camera settings: {e}")
    
    def get_meta(self,json_data):
        # Initialize FocusExposure
        
        try:
            focus_exposure_metadata = models.FocusExposure(
                AfState=json_data['AfState']  if "AfState" in json_data else 0,
                AfPauseState=json_data['AfPauseState'] if "AfPauseState" in json_data else 0,
                AeLocked=json_data['AeLocked'] if "AeLocked" in json_data else False,
                FocusFoM=json_data['FocusFoM'] if "FocusFoM" in json_data else 0.0,
                LensPosition=json_data['LensPosition'] if "LensPosition" in json_data else 0.0,
            )

            # Initialize SensorDetails
            sensor_details = models.SensorDetails(
                SensorTemperature=json_data['SensorTemperature'] if "SensorTemperature" in json_data else 0.0,
                SensorBlackLevels=json_data['SensorBlackLevels'] if "SensorBlackLevels" in json_data else (0,0,0,0)
            )
            # Initialize ImageQuality
            image_quality_metadata = models.ImageQuality(
                ColourGains=json_data['ColourGains'] if "ColourGains" in json_data else [0.0],
                ColourTemperature=json_data['ColourTemperature'] if "ColourTemperature" in json_data else 0,
                Lux=json_data['Lux'] if "Lux" in json_data else 0,
                ColourCorrectionMatrix=json_data['ColourCorrectionMatrix'] if "ColourCorrectionMatrix" in json_data else [0,0,0,0,0,0,0,0,0],
            )

            # Initialize CameraProperties
            camera_properties = models.CameraProperties(
                ScalerCropMaximum=json_data['ScalerCrop'] if "ScalerCrop" in json_data else  [0, 0, 0, 0]
            )
            return focus_exposure_metadata,sensor_details,image_quality_metadata,camera_properties
        except Exception:
            pass
        return None,None,None,None
    def stop_camera(self):
        self.picam2.stop()
    def capture_image(self, filename,guid, light_mode='white'):
        """
        Captures an image with the specified lighting mode and saves it to the filename.
        
        Args:
            filename (str): Output filename
            light_mode (str): Lighting mode ('uv', 'white', 'none')
            
        Returns:
            dict: Image information including path, size, and timing
        """
        start_time = time.time()
        self.logger.info(f"Capturing image with {light_mode} light mode")
        
        # Configure lighting
        try:
             # Initialize GPIO Pins for UV and White Lights
            self.init_led()
            if light_mode == 'uv':
                self.uv_led_1.value = self.uv_intensity[0]
                self.uv_led_2.value = self.uv_intensity[1]
                self.white_off()
            elif light_mode == 'white':
                self.uv_off()
                self.white_led_1.off()  # Using white_led_2 for consistent control
                self.white_led_2.value = self.white_intensity
            
               
              
            self.logger.debug(f"Lighting set to {light_mode}, stabilizing for {self.stabilization_time}s")
            time.sleep(self.stabilization_time)  # Allow light to stabilize
            
            try:
                # Start camera and capture
                if not self.camera_pre_configured:
                    self.picam2.start(show_preview=False)
                    time.sleep(0.5)  # Brief stabilization for camera
                # self.picam2.capture_file(filename)
                request = self.picam2.capture_request()
                # Main Image
                rgb_image = request.make_array("main")
                # cv2.imwrite(image_filename, rgb_image)
                try:
                  image = Image.fromarray(rgb_image, 'RGB')
                #   image = Image.new('RGB', (640, 480), color='white')
                  image.save(filename)    
                  # Metadata
                  metadata = request.get_metadata()
                
                except Exception as e:
                  self.logger.debug(f"Camera Capture Issue {e}s")
                  del image
                  del rgb_image
                  
               
            finally:
                request.release()
                gc.collect() 
            
            
            focus_exposure_metadata, sensor_details, image_quality_metadata, camera_properties = self.get_meta(metadata)
            
            # Create the CapturedImage object
            captured_image = models.CapturedImage(
                guid=guid,
                image_type=models.ImageType.JPG,
                path=filename,
                light_type=models.LightType.UV_365 if light_mode =="uv" else models.LightType.WHITE ,
                focus_exposure_metadata=focus_exposure_metadata,
                sensor_details=sensor_details,
                image_quality_metadata=image_quality_metadata,
                camera_properties=camera_properties
            )
            # captured_raw_image=CapturedImage(
            #     guid = raw_guid,
            #     image_type=ImageType.RAW,
            #     path=raw_filename,
            #     light_type=light_type,
            #     focus_exposure_metadata=focus_exposure_metadata,
            #     sensor_details=sensor_details,
            #     image_quality_metadata=image_quality_metadata,
            #     camera_properties=camera_properties
            # )
            
            # Add to created files list
            self.created_files.append(filename)
            self.captured_images.append(captured_image)
            
            import threading
            upload_thread = threading.Thread(target=self.upload_to_imgbb, args=(filename,))
            upload_thread.daemon = True
            upload_thread.start()
            
            # Turn off lights after capture
            self.all_off()
            
            end_time = time.time()
            capture_duration = round(end_time - start_time, 2)
            
            image_size = self.get_image_size(filename)
            file_size = os.path.getsize(filename)
            
            self.logger.info(f"Image captured: {filename}, size: {image_size}, duration: {capture_duration}s")
            
            return {
                "image": os.path.basename(filename),
                "path": filename,
                "resolution": image_size,
                "file_size": file_size,
                "duration": capture_duration
            }
            
        except Exception as e:
            self.logger.error(f"Error capturing image: {e}",exc_info=True)
            self.all_off()  # Safety measure
            raise e
    def upload_to_imgbb(self,image_path):
        """Uploads the image to Imgbb."""
        IMGBB_API_KEY = "5a1257239091f4cb1a7c6225085357af"
        import requests
        with open(image_path, "rb") as image_file:
            response = requests.post(
                f"https://api.imgbb.com/1/upload?key=5a1257239091f4cb1a7c6225085357af",
                files={"image": image_file}
            )
        if response.status_code == 200:
            uri = response.json().get("data", {}).get("url")
            self.logger.info(f"Image Uploaded to IMBB {uri}")
          
        else:
            raise Exception(f"Error uploading to Imgbb: {response.text}")
    def get_image_size(self, image_path):
        """Gets the dimensions of an image."""
        with Image.open(image_path) as img:
            return img.size
    
    def create_thumbnail(self, image_path, thumbnail_size=None, quality=85):
        """
        Creates a thumbnail of the specified image.
        
        Args:
            image_path (str): Path to the source image
            thumbnail_size (tuple, optional): Thumbnail dimensions (width, height)
            quality (int, optional): JPEG quality (1-100)
            
        Returns:
            dict: Thumbnail information
        """
        if thumbnail_size is None:
            thumbnail_size = self.thumbnail_resolution
            
        start_time = time.time()
        self.logger.info(f"Creating thumbnail of size {thumbnail_size} from {image_path}")
        
        filename_base = os.path.splitext(os.path.basename(image_path))[0]
        thumbnail_filename = os.path.join(
            self.output_dir, 
            f"thumbnail_{filename_base}_{thumbnail_size[0]}x{thumbnail_size[1]}.jpg"
        )
        
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if needed (in case of RGBA images)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Create a copy to avoid modifying the original
                thumb = img.copy()
                thumb.thumbnail(thumbnail_size)
                thumb.save(thumbnail_filename, "JPEG", quality=quality)
            
            # Add to created files list
            self.created_files.append(thumbnail_filename)
            
            end_time = time.time()
            thumbnail_duration = round(end_time - start_time, 2)
            
            thumbnail_size = self.get_image_size(thumbnail_filename)
            file_size = os.path.getsize(thumbnail_filename)
            
            self.logger.debug(f"Thumbnail created: {thumbnail_filename}")
            
            return {
                "image": os.path.basename(thumbnail_filename),
                "path": thumbnail_filename,
                "resolution": thumbnail_size,
                "file_size": file_size,
                "duration": thumbnail_duration
            }
            
        except Exception as e:
            self.logger.error(f"Error creating thumbnail: {e}")
            raise
    
    def zip_files(self, files, zip_filename=None):
        """
        Zips the specified files and returns the path to the zip file.
        
        Args:
            files (list): List of file paths to zip
            zip_filename (str, optional): Output zip filename
            
        Returns:
            dict: Zip file information
        """
        start_time = time.time()
        
        if not zip_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_filename = os.path.join(self.output_dir, f"images_{timestamp}_{uuid4()}.zip")
        
        self.logger.info(f"Creating zip file {zip_filename} with {len(files)} files")
        
        try:
            with zipfile.ZipFile(zip_filename, 'w') as zipf:
                for file in files:
                    if os.path.exists(file):
                        zipf.write(file, os.path.basename(file))
                        self.logger.debug(f"Added {file} to zip")
                    else:
                        self.logger.warning(f"File {file} not found, skipping")
            
            # Add to created files list
            self.created_files.append(zip_filename)
            
            end_time = time.time()
            zip_duration = round(end_time - start_time, 2)
            
            file_size = os.path.getsize(zip_filename)
            self.logger.info(f"Zip file created: {zip_filename}, size: {file_size} bytes")
            
            return {
                "file": os.path.basename(zip_filename),
                "path": zip_filename,
                "file_size": file_size,
                "files_count": len(files),
                "duration": zip_duration
            }
            
        except Exception as e:
            self.logger.error(f"Error creating zip file: {e}")
            raise
    def register_test_on_server():
        """
        Registers the test on the server.
        """
        
    def upload_to_imgbb(self, image_path):
        """
        Uploads the image to ImgBB.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            dict: Upload response information
        """
        if not self.IMGBB_API_KEY:
            self.logger.warning("No ImgBB API key provided, skipping upload")
            return {"url": None, "success": False, "error": "No API key provided"}
        
        self.logger.info(f"Uploading {image_path} to ImgBB")
        start_time = time.time()
            
        try:
            with open(image_path, "rb") as image_file:
                response = requests.post(
                    f"https://api.imgbb.com/1/upload?key={self.IMGBB_API_KEY}",
                    files={"image": image_file},
                    timeout=30  # Add timeout
                )
            
            end_time = time.time()
            upload_duration = round(end_time - start_time, 2)
            
            if response.status_code == 200:
                data = response.json().get("data", {})
                self.logger.info(f"Upload successful: {data.get('url')}")
                return {
                    "url": data.get("url"),
                    "delete_url": data.get("delete_url"),
                    "success": True,
                    "duration": upload_duration
                }
            else:
                self.logger.error(f"Upload failed: {response.status_code} - {response.text}")
                return {
                    "url": None, 
                    "success": False, 
                    "error": f"Error: {response.status_code}", 
                    "message": response.text,
                    "duration": upload_duration
                }
                
        except Exception as e:
            self.logger.error(f"Exception during upload: {e}")
            return {"url": None, "success": False, "error": str(e)}
    
    def capture_and_process(self, options=None):
        """
        Captures images under different lighting conditions and processes them.
        
        Args:
            options (dict, optional): Processing options
                - resolution (tuple): Image resolution
                - thumbnail_size (tuple): Thumbnail size
                - quality (int): JPEG quality
                - camera_preset (str): Camera settings preset
                - upload (bool): Whether to upload images to ImgBB
                - create_thumbnails (bool): Whether to create thumbnails
                
        Returns:
            dict: Comprehensive processing results
        """
        process_start_time = time.time()
        
        # Default options
        if options is None:
            options = {}
        
        resolution = options.get('resolution', self.default_resolution)
        thumbnail_size = options.get('thumbnail_size', self.thumbnail_resolution)
        quality = options.get('quality', 85)
        camera_preset = options.get('camera_preset', 'default')
        upload_images = options.get('upload', False)
        create_thumbnails = options.get('create_thumbnails', True)
        
        self.logger.info(f"Starting capture and process with resolution {resolution}")
        
        try:
            # Configure camera
            self.configure_camera(resolution, camera_preset)
            self.init_led()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_id = str(uuid4())[:8]
            
            crop_test,sample = initialize_empty_test(self.device_id)
            session_id=str(crop_test.guid)
            # Prepare result structure
            result = {
                "status": "success",
                "session_id": session_id,
                "timestamp": timestamp,
                "images": {},
                "server_info":{},
                "thumbnails": {} if create_thumbnails else None,
                "zip": None,
                "uploads": {} if upload_images else None,
                "metrics": {
                    "total_duration": None,
                    "resolution": resolution
                }
            }
            
            # Capture UV image
            uv_image_guid = uuid.uuid4()
            uv_image_path = os.path.join(
                self.output_dir, 
                f"{uv_image_guid}.jpg" #should prefix light source uv
            )
            uv_image_info = self.capture_image(uv_image_path,uv_image_guid, light_mode='uv')
            result["images"]["uv"] = uv_image_info
            
            # Capture white image
            white_image_guid = uuid.uuid4()
            white_image_path = os.path.join(
                self.output_dir, 
                f"{white_image_guid}.jpg"
            )
            white_image_info = self.capture_image(white_image_path,white_image_guid, light_mode='white')
            result["images"]["white"] = white_image_info
            
            # Create thumbnails if requested
            # if create_thumbnails:
            #     result["thumbnails"]["uv"] = self.create_thumbnail(
            #         uv_image_path, thumbnail_size, quality
            #     )
            #     result["thumbnails"]["white"] = self.create_thumbnail(
            #         white_image_path, thumbnail_size, quality
            #     )
            
            # Zip the files
            files_to_zip = [uv_image_path, white_image_path]
            
            self.logger.debug(files_to_zip)
            
            # if create_thumbnails:
            #     files_to_zip.append(result["thumbnails"]["uv"]["path"])
            #     files_to_zip.append(result["thumbnails"]["white"]["path"])
            
            #Send test results to server
            
            sample.images.extend(self.captured_images)
            crop_test.tests.append(sample)
            
            server_reference,server_data,server_duration = self.crop_test_manager.create_test(crop_test_data=crop_test)   
            
            result["server_info"]={
                "server_reference": server_reference,
                "posted_to_server": server_data,
                "server_duration": server_duration
            }
            #zip_file_name = f"{crop_test.guid}_{light_type}.zip"
            zip_filename = os.path.join(
                self.output_dir, 
                f"{crop_test.guid}_BOTH.zip"
            )
            zip_info = self.zip_files(files_to_zip, zip_filename)
            result["zip"] = zip_info
            
            # Upload to ImgBB if requested
            if upload_images:
                result["uploads"]["uv"] = self.upload_to_imgbb(uv_image_path)
                result["uploads"]["white"] = self.upload_to_imgbb(white_image_path)
                
                if create_thumbnails:
                    result["uploads"]["uv_thumbnail"] = self.upload_to_imgbb(
                        result["thumbnails"]["uv"]["path"]
                    )
                    result["uploads"]["white_thumbnail"] = self.upload_to_imgbb(
                        result["thumbnails"]["white"]["path"]
                    )
            
            # Calculate total duration
            process_end_time = time.time()
            total_duration = round(process_end_time - process_start_time, 2)
            result["metrics"]["total_duration"] = total_duration
            
            self.logger.info(f"Capture and process completed in {total_duration}s")
            return result
            
        except Exception as e:
            self.logger.error(f"Error in capture_and_process: {e}")
            return {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
            }
    def retry_failed_tests(self):
        if self.crop_test_manager:
            self.crop_test_manager.retry_failed_tests()
    def cleanup(self, delete_files=False):
        """
        Cleans up resources and optionally removes files.
        
        Args:
            delete_files (bool): Whether to delete created files
        """
        self.logger.info("Performing cleanup")
        try:
            # Turn off all LEDs
            self.all_off()
            
            # Close GPIO resources
            self.uv_led_1.close()
            self.uv_led_2.close()
            self.white_led_1.close()
            self.white_led_2.close()
            
            # Clean up files if requested
            if delete_files:
                self.logger.info(f"Deleting {len(self.created_files)} files")
                for file in self.created_files:
                    if os.path.exists(file):
                        os.remove(file)
                        self.logger.debug(f"Deleted: {file}")
                
            self.logger.info("Cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def __enter__(self):
        """Context manager entry point."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point with automatic cleanup."""
        self.cleanup()
        if exc_type:
            self.logger.error(f"Exception during context: {exc_val}",exc_info=True)
            return False  # Re-raise exception
        return True
