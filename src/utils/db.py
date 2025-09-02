import sqlite3
import json
import re
from datetime import datetime


class Query:
    def __init__(self, field=None):
        self.field = field
        self._exists = False
        self._regex = None
        self._custom_test = None
        self._search_text = None
        self._test_params = None
        self._any_values = None
        self._all_values = None

    def exists(self):
        self._exists = True
        return self

    def matches(self, regex, flags=0):
        self._regex = re.compile(regex, flags)
        return self

    def search(self, text):
        self._search_text = text.lower()
        return self

    def test(self, func, *args):
        self._custom_test = func
        self._test_params = args
        return self

    def any(self, values):
        self._any_values = set(values)
        return self

    def all(self, values):
        self._all_values = set(values)
        return self

    def __eq__(self, value):
        return lambda r: r.get(self.field) == value

    def __ne__(self, value):
        return lambda r: r.get(self.field) != value

    def __lt__(self, value):
        return lambda r: r.get(self.field) < value

    def __le__(self, value):
        return lambda r: r.get(self.field) <= value

    def __gt__(self, value):
        return lambda r: r.get(self.field) > value

    def __ge__(self, value):
        return lambda r: r.get(self.field) >= value

    def __getattr__(self, item):
        return Query(f"{self.field}.{item}" if self.field else item)

    def evaluate(self, record):
        value = record
        for part in self.field.split('.'):
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                value = None
                break

        if self._exists:
            return value is not None

        if self._regex:
            return bool(self._regex.fullmatch(value or ''))

        if self._search_text:
            return self._search_text in (value or '').lower()

        if self._custom_test:
            return self._custom_test(value, *self._test_params)

        if self._any_values:
            if not isinstance(value, list):
                return False
            return bool(self._any_values.intersection(value))

        if self._all_values:
            if not isinstance(value, list):
                return False
            return self._all_values.issubset(value)

        raise ValueError("Invalid query - no comparison provided.")


class TinySqliteDB:
    def __init__(self, db_file):
        self.db_file = db_file

    def _connect(self):
        return sqlite3.connect(self.db_file)

    def _create_table_if_not_exists(self, table):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,
            created_at TEXT
        )
        """)
        conn.commit()
        conn.close()

    def insert(self, table, record):
        self._create_table_if_not_exists(table)
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(f"""
        INSERT INTO {table} (data, created_at) VALUES (?, ?)
        """, (json.dumps(record), datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()

    def all(self, table):
        self._create_table_if_not_exists(table)
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(f"SELECT data FROM {table}")
        records = [json.loads(row[0]) for row in cursor.fetchall()]
        conn.close()
        return records

    def search(self, table, query):
        return [r for r in self.all(table) if query.evaluate(r)]

    def update(self, table, updates, query):
        records = self.all(table)
        updated_records = []
        for record in records:
            if query.evaluate(record):
                record.update(updates)
            updated_records.append(record)

        self.truncate(table)
        for record in updated_records:
            self.insert(table, record)

    def remove(self, table, query):
        records = self.all(table)
        remaining_records = [r for r in records if not query.evaluate(r)]

        self.truncate(table)
        for record in remaining_records:
            self.insert(table, record)

    def truncate(self, table):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {table}")
        conn.commit()
        conn.close()
