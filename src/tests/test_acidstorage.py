import os
import json
import threading
import uuid
import time
from multiprocessing import Process, Queue
from tinydb import TinyDB
from utils.thread_locks import ACIDStorage,get_db_path
import pytest


DB_PATH = get_db_path('test_acid_db.json')

#  #ToDo PYTHONPATH=src pytest src/tests/test_acidstorage.py -v

# @pytest.fixture(autouse=True)
# def clean_db():
#     if os.path.exists(DB_PATH):
#         os.remove(DB_PATH)
#     for file in os.listdir('.'):
#         if file.startswith('test_acid_db.json.') and file.endswith('.bkp'):
#             os.remove(file)
#     yield
#     if os.path.exists(DB_PATH):
#         os.remove(DB_PATH)

@pytest.fixture
def shared_db():
    db = TinyDB(DB_PATH, storage=ACIDStorage)
    yield db
    db.close()

def test_storage_initializes():
    db = TinyDB(DB_PATH, storage=ACIDStorage)
    assert os.path.exists(DB_PATH)
    assert db.all() == []
    db.close()

def test_write_and_read():
    db = TinyDB(DB_PATH, storage=ACIDStorage)
    db.insert({'name': 'Alice', 'age': 30})
    db.insert({'name': 'Bob', 'age': 25})
    assert len(db.all()) == 2
    db.close()
    
def writer_process(index, q):
    db = TinyDB(DB_PATH, storage=ACIDStorage)
    doc = {'index': index}
    db.insert(doc)
    db.close()
    q.put(doc)

def test_multiprocess_safety():
    processes = []
    q = Queue()

    for i in range(10):
        p = Process(target=writer_process, args=(i, q))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

    # Read all docs from the DB after all processes finish
    db = TinyDB(DB_PATH, storage=ACIDStorage)
    docs = db.all()
    db.close()

    assert len(docs) == 10  # All inserts should succeed

    # Check that all the inserted docs match what the processes reported back
    inserted_docs = [q.get() for _ in range(10)]
    assert all(doc in docs for doc in inserted_docs)

def test_corruption_backup_and_recovery():
    db = TinyDB(DB_PATH, storage=ACIDStorage)
    db.insert({'name': 'Alice'})
    db.close()

    with open(DB_PATH, 'w') as f:
        f.write("CORRUPTED DATA")

    db = TinyDB(DB_PATH, storage=ACIDStorage)
    assert db.all() == []  # New empty db after recovery
    db.close()
    base_dir = os.path.dirname(DB_PATH)
    backup_dir = os.path.join(base_dir, 'backup')


    backups = [f for f in os.listdir(backup_dir) if f.startswith('test_acid_db.json.') and f.endswith('.bkp')]
    assert len(backups) == 1  # Backup should exist

def test_thread_safety(shared_db):
    lock = threading.Lock()

    def writer(index):
        with lock:
            shared_db.insert({'index': index})

    threads = []
    for i in range(10):
        t = threading.Thread(target=writer, args=(i,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    assert len(shared_db.all()) == 10

@pytest.mark.slow
def test_large_data_handling():
    db = TinyDB(DB_PATH, storage=ACIDStorage, storage_kwargs={'large_data': True})
    records = [{'id': i} for i in range(100)]
    db.insert_multiple(records)
    assert len(db.all()) == 100
    db.close()
