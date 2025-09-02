import json
import os
from datetime import datetime, timedelta
from .thread_locks import get_sqlite_db,get_db_path


class OldRecordMigrator:
    def __init__(self, db_file):
        self.db = get_sqlite_db(db_file)

        # Config: Each file defines its retention rules and timestamp fields
        self.files_config = {
            "battery_data.json": {
                "single_table": True,
                "table": "battery_data",
                "timestamp_field": "timestamp",
                "retention_period": timedelta(days=7)
            },
            "button_thresholds.json": {
                "single_table": False,
                "tables": {
                    "thresholds": {"retention_period": timedelta(hours=24), "timestamp_field": "timestamp"}
                }
            },
            "gps_data.json": {
                "single_table": True,
                "table": "gps_data",
                "timestamp_field": "timestamp",
                "retention_period": timedelta(days=3)
            },
            "internet_strength.json": {
                "single_table": False,
                "tables": {
                    "minute_checks": {"retention_period": timedelta(hours=24), "timestamp_field": "timestamp"},
                    "hourly_checks": {"retention_period": timedelta(days=7), "timestamp_field": "timestamp"},
                    "last_recorded": {"retention_period": timedelta(days=30), "timestamp_field": "timestamp"}
                }
            },
            "queue_service.json": {
                "single_table": False,
                "tables": {
                    "files": {"retention_period": timedelta(hours=24), "timestamp_field": "created_at"},
                    "uploads": {"retention_period": timedelta(days=7), "timestamp_field": "upload_date"},
                }
            }
        }

    def is_old_record(self, record, timestamp_field, retention_period):
        """Checks if a record is older than the specified retention period."""
        try:
            record_time = datetime.fromisoformat(record[timestamp_field])
            return record_time < (datetime.utcnow() - retention_period)
        except (KeyError, ValueError):
            print(f"⚠️ Skipping record with missing/invalid timestamp field '{timestamp_field}': {record}")
            return False

    def process_single_table_file(self, file_path, config):
        """Handles single-table JSON files."""
        table = config["table"]
        timestamp_field = config["timestamp_field"]
        retention_period = config["retention_period"]

        with open(file_path, "r") as f:
            try:
                data = json.load(f)
                if not isinstance(data, list):
                    raise ValueError(f"{file_path} must contain a list of records.")
            except json.JSONDecodeError:
                print(f"❌ Error parsing JSON in {file_path}")
                return

        old_records = [r for r in data if self.is_old_record(r, timestamp_field, retention_period)]
        new_records = [r for r in data if not self.is_old_record(r, timestamp_field, retention_period)]

        for record in old_records:
            self.db.insert(table, record)

        if old_records:
            print(f"✅ Migrated {len(old_records)} old records from {file_path} to table '{table}'")

        with open(file_path, "w") as f:
            json.dump(new_records, f, indent=2)

    def process_multi_table_file(self, file_path, config):
        """Handles multi-table JSON files."""
        with open(file_path, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"❌ Error parsing JSON in {file_path}")
                return

        for table, table_config in config["tables"].items():
            records = data.get(table, [])
            timestamp_field = table_config.get("timestamp_field", "timestamp")  # Default to 'timestamp' if not specified
            retention_period = table_config["retention_period"]

            old_records = [r for r in records if self.is_old_record(r, timestamp_field, retention_period)]
            new_records = [r for r in records if not self.is_old_record(r, timestamp_field, retention_period)]

            for record in old_records:
                self.db.insert(table, record)

            if old_records:
                print(f"✅ Migrated {len(old_records)} old records from {file_path} ({table}) to SQLite table '{table}'")

            data[table] = new_records  # Save only new records back to JSON

        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    def process_file(self, filename, config):
        """Determines whether to process a file as a single-table or multi-table JSON."""
        file_path = get_db_path(filename)

        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            print(f"⚠️ Skipping empty/missing file: {filename}")
            return

        try:
            if config["single_table"]:
                self.process_single_table_file(file_path, config)
            else:
                self.process_multi_table_file(file_path, config)
        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")

    def run_migration(self):
        """Processes all files in the configuration."""
        for filename, config in self.files_config.items():
            self.process_file(filename, config)
        print("✅ All files processed successfully.")

