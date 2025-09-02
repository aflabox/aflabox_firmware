import sqlite3
from datetime import datetime
import json
from utils.thread_locks import get_db_path
from utils.base_db import BaseDB

class CropTestDB(BaseDB):
    def __init__(self, db_path="crop_tests.db"):
        super().__init__(get_db_path(db_path))
        # self.conn = sqlite3.connect(get_db_path(db_path))
        # self.conn.row_factory = sqlite3.Row
        # self.conn.execute("PRAGMA auto_vacuum = INCREMENTAL")
        # self.conn.execute('PRAGMA journal_mode=WAL')
        self._create_table()

    def _create_table(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS crop_tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference TEXT UNIQUE,
                data TEXT, 
                created_at TEXT,
                last_retry_at TEXT NULL
            )
        ''')
        self.conn.commit()
    def get_test_by_reference(self, reference):
        """Retrieve a single crop test by its reference."""
        cursor = self.conn.execute('''
            SELECT * FROM crop_tests WHERE reference = ?
        ''', (reference,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def insert_test(self, reference, data):
        data_json = json.dumps(data)
        created_at = datetime.utcnow().isoformat()

        self.conn.execute('''
            INSERT OR REPLACE INTO crop_tests (reference, data, created_at)
            VALUES (?, ?, ?)
        ''', (reference, data_json, created_at))
        self.conn.commit()

    def get_all_tests(self):
        cursor = self.conn.execute('SELECT * FROM crop_tests')
        return [dict(row) for row in cursor.fetchall()]

    def delete_test(self, reference):
        self.conn.execute('DELETE FROM crop_tests WHERE reference = ?', (reference,))
        self.conn.commit()

    def update_retry_timestamp(self, reference):
        self.conn.execute('''
            UPDATE crop_tests 
            SET last_retry_at = ?
            WHERE reference = ?
        ''', (datetime.utcnow().isoformat(), reference))
        self.conn.commit()
