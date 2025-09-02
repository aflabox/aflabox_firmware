import time
from utils.thread_locks import get_db_path,get_db
from raspi_tools import GPSManager,GPSData
from datetime import datetime, timezone, timedelta
from utils.helpers import get_last_known_location


# Example usage
timestamp = "2025-03-02T05:31:59.500Z"



class GPSPowerManager:
    def __init__(self, power_pin=20, gps_acquire_time=5, gps_check_timeout=300):
        """
        Initializes the GPS power manager.
        :param power_pin: GPIO pin used to control power to the GPS module.
        :param gps_acquire_time: Time to wait for GPS to acquire satellites after power-on (in seconds).
        :param gps_check_timeout: How long to wait for a valid fix (in seconds).
        """
        self.power_pin = power_pin
        self.gps_acquire_time = gps_acquire_time
        self.gps_check_timeout = gps_check_timeout
        path = "gps_data.json"
        self.db = get_db(path)
        self.gps_manager = GPSManager(db_path=get_db_path(path),timeout=self.gps_check_timeout)

     
    def is_recent_utc(self,timestamp_str, minutes=5):
        # Convert timestamp to datetime object
        utc_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

        # Current UTC time
        now = datetime.now(timezone.utc)

        # Check if the timestamp is within the last `minutes`
        return now - utc_time <= timedelta(minutes=minutes)

    def get_gps_data(self):
       
      
        return self.gps_manager.run()
    def get_last_known_location(self):
       
            return get_last_known_location()
        
        

    def query_and_print(self):
        try:
          

            print(f"Waiting {self.gps_acquire_time} seconds for GPS to acquire satellites...")
            time.sleep(self.gps_acquire_time)

            gps_data = self.get_gps_data()
            print("DATA",gps_data)
            if gps_data:
                
                return {
                    "success":True,
                    "timestamp": gps_data.date_created,
                    "latitude": gps_data.latitude,
                    "longitude": gps_data.longitude,
                    "altitude": gps_data.altitude,
                    "is_recent":self.is_recent_utc(gps_data.date_created)
                }

            else:
                return {
                    "success":False,
                    "error": [
                              ["GPS", "Connected"],
                              ["Alert","No Signal"],
                              ["Try", "Taking outside"],
                        ],
                }
        except Exception as e:
            print(f"{e}")
            return {
                    "success":False,
                    "error": [
                              ["GPS", "Disconnected"],
                              ["Alert","No Signal"]
                        ],
                }
        finally:
            pass
            


