import asyncio
import time
import json
import math,threading
from utils.logger import get_logger
from .file_service import QueueFileService
from hardware.camera import CameraController
from hardware.display import DashboardAnimation
from utils.lifo import LIFOStorage
from utils.helpers import free_camera_resources
from utils.gpio_helper import GPIOManager

logger = get_logger()

class CameraScannerService:
    def __init__(self,device_id,config, dashboard:DashboardAnimation,gpio:GPIOManager=None):
        """
        Manage file upload status updates using asyncio queue and loop.
        """
        self.camera=None
        self.gpio=gpio
        self.dashboard = dashboard
        self.config = config
        self.device_id=device_id
        self.status_queue = asyncio.Queue()
        self.crop_test_manager=None
        self.listener_task = None
        self.wait_for_data=True
        self.queue_service = QueueFileService(self.get_config('QUEUE_FILE_SERVICE'),self.callback_event)
        self.queue_service.addDeviceId(device_id)
        self.capture_duration=0
        self.upload_duration=0
        self.test_results=LIFOStorage(max_size=5)
        self.has_results=False
    def getResultsLogs(self)->LIFOStorage:
        return self.test_results     
    def get_config(self,section):
        # Try integer conversion
        def auto_convert(value):
            if value.isnumeric():
                return int(value)
            
            # Try float conversion (to handle things like '3.14')
            try:
                return float(value)
            except ValueError:
                pass

            # Fallback to plain string
            return value
        section_dict = dict(self.config.items(section))
        converted_dict = {k: auto_convert(v) for k, v in section_dict.items()}
        return converted_dict
    import json

    def extract_sample_data_json(self,data):
        # 'accuracy': 76.31539106369019,
        # 'aflotoxin_presence': 'Detected',
        # 'aflotoxin_concentration': None,
        # 'aflotoxin_type': None,
        # 'aflotoxin_units': 'ppb',
        print(type(data))
        for sample in data['results']['samples']:
            # No need to json.loads() here - `sample` is already a dict
            guid = sample['guid']
            aflotoxin = sample['aflotoxin_presence']
            level = sample['aflotoxin_concentration'] or "N/A"
            aflatoxin_type = sample['aflotoxin_type'] or "Unknown"

            quality_prams = sample.get('quality_prams', {})
            kennels = quality_prams.get('sample_kennel_count') or 0
            
          

            purity = "N/A"
            return {
                "Test#": "34",
                "Aflotoxin": aflotoxin,
                "Level": level,
                "Purity": purity,
                "Type": aflatoxin_type,
                "Kennels": 0
            }

    async def show_test_results(self,data):
        # if "test_id" in data:
        # data= self.extract_sample_data_json(data)
        # {"test_id": "47399920-d083-4748-8d82-a2c3d1b75aff", 
        # "results": {"model_used": "regression_aflatoxin", "accuracy": null, "aflotoxin_presence": null, "aflotoxin_concentration": null, "aflotoxin_type": null, "aflotoxin_units": "ppb",
        # "samples": [], "aflotoxin_level": null,
        # "error": {"message": "Invalid image", "status": "Rejected", "action": "Re-test"}}
        print(data['summary'])
            
        self.has_results=True
       
        ordered_keys = ["Test#", "Aflatoxin","Level","Purity","Type","Count"]
        
        def dict_to_ordered_key_value_list(item: dict, ordered_keys: list) -> list[list]:
            if "error" in item and isinstance(item["error"], dict):
                return [
                    ["Test#", item.get("Test#")],
                    ["Error", item["error"].get("message")],
                    ["Status", item["error"].get("status")],
                    ["Action", item["error"].get("action")]
                ]
            
            return [
                [key, value] for key in ordered_keys
                if (value := item.get(key)) not in [None, "", "N/A"] 
            ]


        
        filtered_data = dict_to_ordered_key_value_list(data['summary'],ordered_keys)
        if "error" in filtered_data:
            pass
        self.test_results.push(filtered_data)

        self.dashboard.show_table_screen(filtered_data) 
        await asyncio.sleep(10)
        self.has_results=False 
                 
    def callback_event(self, data):
        """
        Handle callbacks from the file upload process.
        
        Args:
            data (dict): Notification data from the uploader
        """
        try:
            # Log all callback data for debugging
            print(f"Callback received: {data}")
            
            # Only process notifications when not on home screen
            if "notification_type" in data and not self.dashboard.isHomeScreen():
                
                
                # Handle upload completion
                if data["notification_type"] == "UPLOAD_DONE":
                   
                    # Ensure upload_duration exists or provide default
                    duration = math.ceil(data.get('upload_duration', 0))
                    steps = [
                        ["Scanning", f"Done ({self.capture_duration}s)"],
                        ["Uploading", f"Done ({duration}s)"],
                        ["Analyzing", "wait..."]
                    ]
                    # Update UI in a thread-safe way
                    self.dashboard.show_table_screen(steps)
                    
                    
                    for i in range(45):
                        #wait for 30 seconds to see if server returns data 
                        if self.has_results:
                            break
                        print(f" Awaiting for results {i}....")
                        time.sleep(1)
                    self.wait_for_data = False
                    
                    
                # Handle upload progress
                elif data["notification_type"] == "UPLOAD_PROGRESS":
                    steps = [
                        ["Scanning", f"Done ({self.capture_duration}s)"],
                        ["Uploading", f"wait ({data.get('upload_progress', 0)}%)..."]
                    ]
                    # Update UI in a thread-safe way
                    self.dashboard.show_table_screen(steps)
            else:
                print(f"Ignored callback data: {data}")
        except Exception as e:
            logger.error(f"Error in callback_event: {str(e)}")
            # Log the error but don't crash
            
    def retry_failed_tests(self):
        if self.crop_test_manager:
            self.crop_test_manager.retry_failed_tests() 
    def switch_led_off(self):
        c  =  CameraController(self.device_id, self.get_config('CAMERA_CONTROLLER'),self.camera)
       
         
    async def start(self):
        """Start camera operation
        """
        try:
            steps=[["Scanning","wait.."]]
            self.dashboard.show_table_screen(steps)
            logger.info(f"Camera Started")
            with CameraController(self.device_id, self.get_config('CAMERA_CONTROLLER'),self.camera,self.gpio) as camera:
                result = await asyncio.to_thread(camera.capture_and_process)
                self.camera = camera.picam2
                self.crop_test_manager=camera.crop_test_manager
                if "metrics" in result:
                    self.capture_duration=result['metrics']['total_duration']
                    
                    steps=[["Scanning",f"Done ({self.capture_duration}s)"],["Uploading","wait..."]]
                    
                    self.dashboard.show_table_screen(steps)
                    self.wait_for_data=True
                    
                    batch_id = self.queue_service.save_camera_results(result, reference=result['session_id'])
                    print(f"Queued files with batch ID: {batch_id}")
                    from utils.helpers import check_internet_connection
                    if await check_internet_connection():
                        while self.wait_for_data:
                            await asyncio.sleep(3)
                            status = self.queue_service.get_queue_status()
                            logger.info(status)
                    else:
                        steps=[["Scanning",f"Done ({self.capture_duration}s)"],["Uploading","Queud"]]
                    
                        self.dashboard.show_table_screen(steps)
                        await asyncio.sleep(3)
                        
                        
                else:
                     steps=[["Scanning","Camera Error"]]
                     self.dashboard.show_table_screen(steps)
                     await asyncio.sleep(3)
            await asyncio.sleep(5)
        except Exception as e:
           steps=[["Scanning","Error e500"]]
           logger.error(f"{e} e500",exc_info=True)
           self.dashboard.show_table_screen(steps)
           await asyncio.sleep(3)
           success = free_camera_resources()
           if not success:
              print("WARNING: Failed to free camera resources. Camera may not work properly.")
                
            
         

    async def start_file_uploads(self):
        """Start listening for status updates."""
        self.queue_service.start_background_service()
        

    async def stop_file_uploads(self):
        """Stop listening."""
        self.queue_service.stop_background_service()
        if self.camera:
           self.camera.stop()

    
