import sqlite3
from datetime import datetime
import statistics
import os
from db.click_tracker import ClickTrackerDB
DB_PATH = "core.db"




class ClickTracker:
    def __init__(self, device_id, db_path="button_thresholds.db"):
        self.device_id = device_id
        self.db = ClickTrackerDB()

    def save_threshold(self, event_type, value):
        if event_type not in ["click", "double_click", "long_press"]:
            print(f"Invalid event type: {event_type}")
            return
        self.db.save_threshold(self.device_id, event_type, value)
        print(f"Saved threshold for {event_type}: {value} (Device: {self.device_id})")

    def get_thresholds(self, event_type):
        return self.db.get_thresholds(self.device_id, event_type)

    def get_summary_details(self, event_type):
        values = self.get_thresholds(event_type)
        if not values:
            print(f"No data available for {event_type}")
            return {}

        return self.calculate_stats(values)

    def calculate_stats(self, values):
        precision = 8
        try:
            return {
                "mean": round(statistics.mean(values), precision),
                "median": round(statistics.median(values), precision),
                "std_dev": round(statistics.stdev(values), precision) if len(values) > 1 else 0,
                "variance": round(statistics.variance(values), precision) if len(values) > 1 else 0,
                "min": min(values),
                "max": max(values),
                "q1": round(statistics.quantiles(values, n=4)[0], precision),
                "q3": round(statistics.quantiles(values, n=4)[2], precision),
                "mode": statistics.mode(values) if len(set(values)) > 1 else "No mode",
                "iqr": round(statistics.quantiles(values, n=4)[2] - statistics.quantiles(values, n=4)[0], precision),
            }
        except Exception as e:
            print(f"Error calculating statistics: {e}")
            return {}

    def cleanup(self):
        self.db.cleanup()



