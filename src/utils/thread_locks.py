import json
import os
import uuid
import threading
from tinydb import TinyDB
from tinydb.storages import JSONStorage,Storage
from .db import TinySqliteDB,Query
from tinydb.storages import Storage
from atomicwrites import atomic_write
import portalocker
from datetime import datetime

import sqlite3
from threading import local

# Create a thread-local storage for SQLite connections
thread_local = local()


class ACIDStorage(Storage):
    def __init__(self, path, **kwargs):
        self.path = os.path.abspath(path)
        self.lock = threading.Lock()
        self.large_data = kwargs.get('large_data', False)

        if os.path.exists(self.path):
            self._check_for_corruption()

        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not os.path.exists(self.path):
            self._create_new_db()

    def _check_for_corruption(self):
        try:
            with open(self.path, 'r', encoding='utf-8') as file:
                json.load(file)
        except (json.JSONDecodeError, ValueError):
            self._backup_and_recreate()

    def read(self):
        with self.lock, portalocker.Lock(self.path, 'r', timeout=10) as db_file:
            if self.large_data:
                return self._stream_read(db_file)
            return json.load(db_file)

    def write(self, data):
        with self.lock, portalocker.Lock(self.path, 'r+', timeout=10) as db_file:
            # 1. Validate structure: data must be { "1": { ... }, "2": { ... } }
            for doc_id, doc in data.items():
                if not doc_id.isdigit():
                    raise ValueError(f"Invalid document ID {doc_id}. Expected integer-like string.")

                if not isinstance(doc, dict):
                    raise ValueError(f"Invalid document format for doc_id {doc_id}. Expected dict, got {type(doc)}.")

                # 2. Enforce UUID `_id` inside each document body (not at the table level)
                if '_id' not in doc:
                    doc['_id'] = str(uuid.uuid4())

            # 3. Write to temporary file, then atomically replace
            temp_path = self.path + '.tmp'
            with atomic_write(temp_path, overwrite=True, encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            os.replace(temp_path, self.path)

            # 4. Ensure data is flushed to disk
            with open(self.path, 'r+') as final_file:
                final_file.flush()
                os.fsync(final_file.fileno())




    def _stream_read(self, file_obj):
        file_obj.seek(0)
        return json.load(file_obj)

    def _backup_and_recreate(self):
        base_dir = os.path.dirname(self.path)
        backup_dir = os.path.join(base_dir, 'backup')
        os.makedirs(backup_dir, exist_ok=True)

        filename = os.path.basename(self.path)
        backup_path = os.path.join(backup_dir, f"{filename}.{self._timestamp()}.bkp")

        print(f"[DEBUG] Backing up to {backup_path}")
        os.rename(self.path, backup_path)
        self._create_new_db()

    def _create_new_db(self):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump({}, f)

    def _timestamp(self):
        return datetime.now().strftime("%Y%m%d%H%M%S")

    def close(self):
        pass


class ThreadSafeJSONStorage(JSONStorage):
    _lock = threading.Lock()

    def write(self, data):
        with self._lock:
            super().write(data)

    def read(self):
        with self._lock:
            return super().read()
def get_sqlite_db(path)->TinySqliteDB:
    db_path = get_db_path(path)
    return TinySqliteDB(db_path)  
def get_db_path(path):
    cache_dir = os.path.expanduser("~/.qbox_data")
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir,path)
           
def get_db(path):
    db_path = get_db_path(path)
    return TinyDB(db_path, storage=ThreadSafeJSONStorage)

def get_db_connection(path):
    db_path = get_db_path(path)
    if not hasattr(thread_local, 'connection'):
        thread_local.connection = sqlite3.connect(path)
    return thread_local.connection