import sqlite3, json, threading, time
from datetime import datetime, timedelta
from utils.thread_locks import get_db_path
from utils.base_db import BaseDB

class QueueFileServiceDB(BaseDB):
    def __init__(self, db_path="file_queue.db"):
        self.db_path = get_db_path(db_path)
        super().__init__(self.db_path)   # ok even if BaseDB opens a conn; we won't use it
        self._local = threading.local()
        self._init_tables()

    # ---------- connection handling ----------
    def _conn(self):
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(
                self.db_path,
                timeout=15.0,            # initial wait for busy DB
                isolation_level=None,    # autocommit (no implicit BEGIN)
                check_same_thread=False
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA busy_timeout=10000;")
            conn.execute("PRAGMA foreign_keys=ON;")
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
                    time.sleep(delay); delay = min(delay * 2, 1.0)
                    continue
                raise

    # ---------- schema ----------
    def _init_tables(self):
        self._retry(lambda: self._conn().execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT,
                reference TEXT,
                file_path TEXT,
                file_name TEXT,
                file_type TEXT,
                sub_type TEXT,
                file_size INTEGER,
                resolution TEXT,
                status TEXT,
                priority INTEGER,
                created_at TEXT,
                updated_at TEXT,
                remote_path TEXT,
                remote_url TEXT,
                upload_attempts INTEGER DEFAULT 0,
                upload_progress INTEGER DEFAULT 0,
                upload_complete INTEGER DEFAULT 0,
                file_deleted INTEGER DEFAULT 0,
                metadata TEXT,
                file_error TEXT,
                upload_date TEXT,
                upload_success INTEGER DEFAULT 0,
                upload_error TEXT
            )
        '''))
        self._retry(lambda: self._conn().execute('''
            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER,
                batch_id TEXT,
                reference TEXT,
                file_name TEXT,
                file_type TEXT,
                remote_path TEXT,
                upload_date TEXT,
                success INTEGER,
                error TEXT,
                FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE
            )
        '''))

        # Useful indexes
        self._retry(lambda: self._conn().execute(
            "CREATE INDEX IF NOT EXISTS idx_files_status ON files(status)"
        ))
        self._retry(lambda: self._conn().execute(
            "CREATE INDEX IF NOT EXISTS idx_files_created ON files(created_at)"
        ))
        self._retry(lambda: self._conn().execute(
            "CREATE INDEX IF NOT EXISTS idx_files_updated ON files(updated_at)"
        ))
        self._retry(lambda: self._conn().execute(
            "CREATE INDEX IF NOT EXISTS idx_files_batch ON files(batch_id)"
        ))

    # ---------- CRUD ----------
    def insert_file(self, file_record: dict):
        # Ensure metadata is a JSON string
        metadata_json = json.dumps(file_record.get('metadata', {}))
        now_iso = datetime.now().isoformat()

        sql = '''
            INSERT INTO files (
                batch_id, reference, file_path, file_name, file_type, sub_type,
                file_size, resolution, status, priority, created_at, updated_at,
                remote_path, remote_url, upload_attempts, upload_progress,
                upload_complete, file_deleted, metadata, file_error,
                upload_date, upload_success, upload_error
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        args = (
            file_record.get('batch_id'),
            file_record.get('reference'),
            file_record.get('file_path'),
            file_record.get('file_name'),
            file_record.get('file_type'),
            file_record.get('sub_type'),
            file_record.get('file_size', 0),
            file_record.get('resolution'),
            file_record.get('status'),
            file_record.get('priority', 2),
            file_record.get('created_at', now_iso),
            file_record.get('updated_at', now_iso),
            file_record.get('remote_path'),
            file_record.get('remote_url'),
            file_record.get('upload_attempts', 0),
            file_record.get('upload_progress', 0),
            file_record.get('upload_complete', 0),
            file_record.get('file_deleted', 0),
            metadata_json,
            file_record.get('file_error'),
            file_record.get('upload_date'),
            file_record.get('upload_success', 0),
            file_record.get('upload_error'),
        )
        cur = self._retry(lambda: self._conn().execute(sql, args))
        inserted_id = cur.lastrowid
        # print(f"Inserted file record ID: {inserted_id}")
        return inserted_id

    def update_file(self, file_id: int, updates: dict):
        if not updates:
            return
        # Normalize metadata if provided
        if 'metadata' in updates and not isinstance(updates['metadata'], str):
            updates['metadata'] = json.dumps(updates['metadata'])
        updates['updated_at'] = datetime.now().isoformat()

        cols = ', '.join(f'{k} = :{k}' for k in updates.keys())
        updates['id'] = file_id
        self._retry(lambda: self._conn().execute(
            f'UPDATE files SET {cols} WHERE id = :id', updates
        ))

    def update_upload_status(self, file_id, remote_path=None, remote_url=None, success=True, error=None):
        upload_date = datetime.now().isoformat()
        params = {
            'remote_path': remote_path,
            'remote_url': remote_url,
            'upload_date': upload_date,
            'upload_complete': 1,
            'upload_success': 1 if success else 0,
            'upload_error': error,
            'updated_at': upload_date,
            'id': file_id,
        }
        self._retry(lambda: self._conn().execute('''
            UPDATE files
            SET remote_path = :remote_path,
                remote_url = :remote_url,
                upload_date = :upload_date,
                upload_complete = :upload_complete,
                upload_success = :upload_success,
                upload_error = :upload_error,
                updated_at = :updated_at
            WHERE id = :id
        ''', params))

    def increment_attempts(self, file_id: int, by: int = 1):
        self._retry(lambda: self._conn().execute(
            'UPDATE files SET upload_attempts = upload_attempts + ?, updated_at = ? WHERE id = ?',
            (by, datetime.now().isoformat(), file_id)
        ))

    def get_file(self, file_id: int):
        cur = self._conn().execute('SELECT * FROM files WHERE id = ?', (file_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_file_status_summary(self):
        cur = self._conn().execute('SELECT status, COUNT(*) AS count FROM files GROUP BY status')
        return {row['status']: row['count'] for row in cur.fetchall()}

    def search_files(self, filters: dict | None = None):
        filters = filters or {}
        query = ["SELECT * FROM files WHERE 1=1"]
        params = {}

        # Simple equality (AND)
        for field in ('batch_id', 'reference', 'file_type'):
            if field in filters:
                query.append(f"AND {field} = :{field}")
                params[field] = filters[field]

        # Status: str or list
        if 'status' in filters:
            if isinstance(filters['status'], (list, tuple)):
                placeholders = ','.join([f":status{i}" for i in range(len(filters['status']))])
                query.append(f"AND status IN ({placeholders})")
                for i, s in enumerate(filters['status']):
                    params[f"status{i}"] = s
            else:
                query.append("AND status = :status")
                params['status'] = filters['status']

        # Boolean-ish
        if 'upload_complete' in filters:
            query.append("AND upload_complete = :upload_complete")
            params['upload_complete'] = 1 if filters['upload_complete'] else 0

        # Date filters
        if 'created_at_before' in filters:
            query.append("AND created_at < :created_at_before")
            params['created_at_before'] = filters['created_at_before']
        if 'updated_at_before' in filters:
            query.append("AND updated_at < :updated_at_before")
            params['updated_at_before'] = filters['updated_at_before']
        if 'older_than_days' in filters and filters['older_than_days'] > 0:
            cutoff = (datetime.now() - timedelta(days=filters['older_than_days'])).isoformat()
            query.append("AND created_at < :older_than_cutoff")
            params['older_than_cutoff'] = cutoff

        # Sorting
        if 'sort_by' in filters:
            col = filters['sort_by']
            order = filters.get('sort_order', 'ASC').upper()
            if col in ('created_at', 'updated_at', 'file_size', 'priority', 'id'):
                query.append(f"ORDER BY {col} {order}")

        # Limit
        if 'limit' in filters:
            query.append("LIMIT :limit")
            params['limit'] = int(filters['limit'])

        sql = " ".join(query)
        cur = self._conn().execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

    def insert_upload_log(self, upload_log: dict):
        payload = {
            'file_id':        upload_log.get('file_id'),
            'batch_id':       upload_log.get('batch_id'),
            'reference':      upload_log.get('reference'),
            'file_name':      upload_log.get('file_name'),
            'file_type':      upload_log.get('file_type'),
            'remote_path':    upload_log.get('remote_path'),
            'upload_date':    upload_log.get('upload_date', datetime.now().isoformat()),
            'success':        1 if upload_log.get('success', False) else 0,
            'error':          upload_log.get('error')
        }
        self._retry(lambda: self._conn().execute('''
            INSERT INTO uploads (file_id, batch_id, reference, file_name, file_type, remote_path, upload_date, success, error)
            VALUES (:file_id, :batch_id, :reference, :file_name, :file_type, :remote_path, :upload_date, :success, :error)
        ''', payload))

    def close(self):
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None
