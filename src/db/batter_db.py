import sqlite3
import threading
import time
from datetime import datetime, timedelta
from utils.thread_locks import get_db_path
from utils.base_db import BaseDB

DB_PATH = "battery.db"

class BatteryDB(BaseDB):
    def __init__(self):
        # Keep path for thread-local connections
        self.db_path = get_db_path(DB_PATH)
        # If BaseDB needs the path, pass it along (safe no-op otherwise)
        super().__init__(self.db_path)
        self._local = threading.local()
        self._init_table()

    # --- connection management (per-thread) ---
    def _conn(self):
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(
                self.db_path,
                timeout=15.0,           # initial busy wait
                isolation_level=None,   # autocommit; no implicit BEGIN
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row
            # Concurrency pragmas
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA busy_timeout=10000;")
            self._local.conn = conn
        return conn

    def _retry(self, fn, retries=6, base_delay=0.05):
        delay = base_delay
        for _ in range(retries):
            try:
                return fn()
            except sqlite3.OperationalError as e:
                msg = str(e).lower()
                if "locked" in msg or "busy" in msg:
                    time.sleep(delay)
                    delay = min(delay * 2, 1.0)
                    continue
                raise

    # --- schema ---
    def _init_table(self):
        self._retry(lambda: self._conn().execute('''
            CREATE TABLE IF NOT EXISTS battery_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                PowerInputStatus TEXT,
                InputVoltage REAL,
                ChargeStatus TEXT,
                BatteryVoltage REAL,
                BatteryPercentage INTEGER,
                ChargeCurrent REAL,
                TimeRemaining INTEGER,
                hasBattery INTEGER,
                BatteryColor TEXT,
                faults TEXT
            )
        '''))
        # helpful for cleanup/query performance
        self._retry(lambda: self._conn().execute(
            "CREATE INDEX IF NOT EXISTS idx_battery_data_timestamp ON battery_data(timestamp)"
        ))

    # --- writes (no `with self.conn:`) ---
    def insert_record(self, record: dict):
        sql = '''
            INSERT INTO battery_data (
                timestamp, PowerInputStatus, InputVoltage, ChargeStatus,
                BatteryVoltage, BatteryPercentage, ChargeCurrent,
                TimeRemaining, hasBattery, BatteryColor, faults
            )
            VALUES (
                :timestamp, :PowerInputStatus, :InputVoltage, :ChargeStatus,
                :BatteryVoltage, :BatteryPercentage, :ChargeCurrent,
                :TimeRemaining, :hasBattery, :BatteryColor, :faults
            )
        '''
        self._retry(lambda: self._conn().execute(sql, record))

    def delete_old_records(self, days=7):
        # Works lexicographically if your stored timestamps are ISO 8601 UTC
        cutoff_time = (datetime.utcnow() - timedelta(days=days)).isoformat()
        self._retry(lambda: self._conn().execute(
            'DELETE FROM battery_data WHERE timestamp < ?', (cutoff_time,)
        ))

    # --- reads ---
    def get_last_n_records(self, n=10):
        cur = self._conn().execute(
            'SELECT * FROM battery_data ORDER BY timestamp DESC LIMIT ?', (n,)
        )
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]

    # Close only this thread's connection (safe for background threads)
    def cleanup(self):
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None
