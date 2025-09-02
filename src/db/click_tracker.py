import os
import sqlite3
from datetime import datetime
from utils.thread_locks import get_db_path
from utils.base_db import BaseDB
DB_PATH = "clicks.db"

class ClickTrackerDB(BaseDB):
    def __init__(self):
        super().__init__(get_db_path(DB_PATH))
        # self.conn = sqlite3.connect(get_db_path(DB_PATH))
        # self.conn.row_factory = sqlite3.Row
        # self.conn.execute('PRAGMA journal_mode=WAL')
        self._init_table()

    def _init_table(self):
        with self.conn:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS click_thresholds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT,
                    event_type TEXT,
                    value REAL,
                    timestamp TEXT
                )
            ''')

    def save_threshold(self, device_id, event_type, value):
        with self.conn:
            self.conn.execute('''
                INSERT INTO click_thresholds (device_id, event_type, value, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (device_id, event_type, value, datetime.now().isoformat()))

    def get_thresholds(self, device_id, event_type):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT value FROM click_thresholds
            WHERE device_id = ? AND event_type = ?
        ''', (device_id, event_type))
        return [row['value'] for row in cursor.fetchall()]

    def cleanup(self):
        self.conn.close()