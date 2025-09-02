import os
from utils.thread_locks import get_db_path
import sqlite3
from datetime import datetime, timedelta

class BaseDB:
    WAL_CHECKPOINT_THRESHOLD_MB = 10 
    
    def __init__(self, db_path):
        self.conn = sqlite3.connect(get_db_path(db_path))
        self.conn.row_factory = sqlite3.Row
        self.setup_database()
    def setup_database(self):
        self.conn.execute("PRAGMA auto_vacuum = INCREMENTAL")
        self.ensure_wal_mode()
        # self.checkpoint_wal()
        self.conditional_wal_checkpoint()
        

    def ensure_wal_mode(self):
        result = self.conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]
        if result.upper() != "WAL":
            raise RuntimeError(f"Failed to enable WAL mode (got {result})")

    def checkpoint_wal(self):
        self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    def run_incremental_vacuum(self,pages_to_vacuum=None):
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA freelist_count;")
        free_pages = cursor.fetchone()[0]

        if free_pages == 0:
            print("No free pages to vacuum.")
            return

        if pages_to_vacuum is None:
            pages_to_vacuum = free_pages  # reclaim all

        print(f"Vacuuming {pages_to_vacuum} out of {free_pages} free pages.")
        self.conn.execute(f"PRAGMA incremental_vacuum({pages_to_vacuum});")
        
    def conditional_wal_checkpoint(self):
        wal_path = self.db_path + "-wal"
        try:
            if os.path.exists(wal_path):
                size_mb = os.path.getsize(wal_path) / (1024 * 1024)
                if size_mb > self.WAL_CHECKPOINT_THRESHOLD_MB:
                    print(f"WAL file is {size_mb:.2f} MB — running checkpoint...")
                    self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                else:
                    print(f"WAL file is {size_mb:.2f} MB — checkpoint not needed.")
        except Exception as e:
            print(f"Warning: could not check WAL file size — {e}")