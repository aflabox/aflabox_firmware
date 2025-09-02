from services import gps_service
import json
if __name__ == "__main__":
    manager = gps_service.GPSPowerManager()

    try:
        data=manager.query_and_print()
        print(json.dumps(data,indent=4))
    except Exception as e:
        print(f"Error: {e}")
