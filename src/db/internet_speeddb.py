import sqlite3
from datetime import datetime,timedelta
from utils.thread_locks import get_db_path
from utils.base_db import BaseDB

DB_PATH = "internet_speed.db"
class InternetMonitorDB(BaseDB):
    def __init__(self):
        super().__init__(get_db_path(DB_PATH))
        # self.conn = sqlite3.connect(get_db_path(DB_PATH))
        # self.conn.row_factory = sqlite3.Row
        # self.conn.execute('PRAGMA journal_mode=WAL')
        self._init_table()
    def _reconnect(self):
         self.conn = sqlite3.connect(get_db_path(DB_PATH))
    def _init_table(self):
        with self.conn:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS internet_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    type TEXT,
                    ping REAL,
                    packet_loss REAL,
                    signal_strength REAL,
                    estimated_speed REAL,
                    download REAL,
                    upload REAL,
                    strength_score REAL,
                    stability_score REAL,
                    is_hotspot INTEGER,
                    trend TEXT,
                    trend_change REAL,
                    estimated INTEGER
                )
            ''')
    def get_last_n_minutes(self,minutes=30,check_type="minute"):
        cutoff_time = (datetime.now() - timedelta(minutes=minutes)).isoformat()
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM internet_checks 
            WHERE timestamp >= ? AND
            type = ? 
            ORDER BY timestamp DESC
        ''', (cutoff_time,check_type,))
        
        return [dict(row) for row in cursor.fetchall()]

    def save_check(self, record, record_type):
        record["type"] = record_type

        # Ensure all fields are present (default to None)
        defaults = {
            "download": None,
            "upload": None,
            "trend": None,
            "trend_change": None,
            "estimated_speed": None,
            "estimated":False
        }
        for key, value in defaults.items():
            if key not in record:
                record[key] = value

        with self.conn:
           d= self.conn.execute('''
                INSERT INTO internet_checks (timestamp, type, ping, packet_loss, signal_strength,
                                            estimated_speed, download, upload, strength_score,
                                            stability_score, is_hotspot, trend, trend_change, estimated)
                VALUES (:timestamp, :type, :ping, :packet_loss, :signal_strength,
                        :estimated_speed, :download, :upload, :strength_score,
                        :stability_score, :is_hotspot, :trend, :trend_change, :estimated)
            ''', record)
          


    def get_last_record(self,new_db=True):
        db = None
        if new_db:
            db = sqlite3.connect(get_db_path(DB_PATH))
            cursor = db.cursor()
        else:
            cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM internet_checks ORDER BY timestamp DESC LIMIT 1')
        row = cursor.fetchone()
        if new_db and db:
            db.close()
        return dict(row) if row else None

    def get_recent_checks(self, check_type="minute", count=30):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM internet_checks WHERE type = ? ORDER BY timestamp DESC LIMIT ?', (check_type, count))
        return [dict(row) for row in cursor.fetchall()]

    def cleanup(self):
        self.conn.close()