import sqlite3
import threading
from queue import Queue
from typing import Any, Optional

class ThreadSafeSQLitePool:
    def __init__(self, database: str, max_connections: int = 5):
        """
        Initialize a thread-safe SQLite connection pool.
        
        :param database: Path to the SQLite database file
        :param max_connections: Maximum number of connections in the pool
        """
        self.database = database
        self.max_connections = max_connections
        self.connections = Queue(maxsize=max_connections)
        self.lock = threading.Lock()

    def get_connection(self) -> sqlite3.Connection:
        """
        Get a database connection from the pool.
        Creates a new connection if the pool is empty.
        
        :return: SQLite database connection
        """
        with self.lock:
            try:
                # Try to get an existing connection from the pool
                return self.connections.get_nowait()
            except Queue.Empty:
                # If pool is empty, create a new connection
                return sqlite3.connect(self.database)

    def release_connection(self, connection: sqlite3.Connection) -> None:
        """
        Release a connection back to the pool.
        
        :param connection: SQLite database connection to release
        """
        with self.lock:
            try:
                # Try to put the connection back in the pool if not full
                if self.connections.qsize() < self.max_connections:
                    self.connections.put_nowait(connection)
                else:
                    # If pool is full, close the connection
                    connection.close()
            except Queue.Full:
                # Fallback to closing the connection if pool is full
                connection.close()

    def execute_query(self, query: str, params: Optional[tuple] = None) -> list:
        """
        Execute a SELECT query with thread-safe connection management.
        
        :param query: SQL query to execute
        :param params: Optional query parameters
        :return: Query results
        """
        connection = self.get_connection()
        try:
            cursor = connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            results = cursor.fetchall()
            return results
        finally:
            # Always release the connection back to the pool
            self.release_connection(connection)

    def execute_write(self, query: str, params: Optional[tuple] = None) -> int:
        """
        Execute an INSERT, UPDATE, or DELETE query with thread-safe connection management.
        
        :param query: SQL query to execute
        :param params: Optional query parameters
        :return: Number of affected rows
        """
        connection = self.get_connection()
        try:
            cursor = connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            connection.commit()
            return cursor.rowcount
        except sqlite3.Error as e:
            connection.rollback()
            raise e
        finally:
            # Always release the connection back to the pool
            self.release_connection(connection)

# Example usage demonstrating thread-safe database operations
def example_usage():
    # Initialize the connection pool
    db_pool = ThreadSafeSQLitePool('example.db', max_connections=3)

    # Create table (only needs to be done once)
    db_pool.execute_write('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER
        )
    ''')

    # Example of inserting data in a thread-safe manner
    def insert_user(name: str, age: int):
        db_pool.execute_write(
            'INSERT INTO users (name, age) VALUES (?, ?)',
            (name, age)
        )

    # Example of querying data in a thread-safe manner
    def get_users_over_age(min_age: int) -> list:
        return db_pool.execute_query(
            'SELECT * FROM users WHERE age > ?',
            (min_age,)
        )

    # Simulate concurrent operations (for demonstration)
    threads = []
    for i in range(10):
        thread = threading.Thread(target=insert_user, args=(f'User{i}', 20 + i))
        threads.append(thread)
        thread.start()

    # Wait for all insert threads to complete
    for thread in threads:
        thread.join()

    # Query and print results
    users = get_users_over_age(25)
    print("Users over 25:", users)

# Run the example
# if __name__ == '__main__':
#     example_usage()