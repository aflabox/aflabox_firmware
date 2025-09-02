import os
import json
import time
import configparser
from datetime import datetime
from utils.thread_locks import get_db_path
from services.file_service import QueueFileService  # assuming you saved the class in queue_file_service.py


config_path=os.path.abspath("../config/config.ini")
config_ = configparser.ConfigParser()
config_.read(config_path)
config = dict(config_.items('QUEUE_FILE_SERVICE'))


def uploaded_callback(data):
    print(f"[UPLOAD CALLBACK] {json.dumps(data, indent=2)}")

def test_save_camera_results():
    service = QueueFileService(uploaded_callback=uploaded_callback,config=config)
    file = get_db_path(f"test_file_{time.time()}.zip")
    results = {
        "zip": {
            "path": file,
            "file_size": 1024,
            "meta": "test metadata"
        }
    }

    # Create test file
   
    with open(file, "w") as f:
        f.write("Test zip content")

    batch_id = service.save_camera_results(results)
    print(f"Saved batch: {batch_id}")

    # Verify database saved the file correctly
    files = service.db.search_files({"batch_id": batch_id})
   
    assert len(files) == 1
    assert files[0]["file_name"] ==os.path.basename(file)
    assert files[0]["status"] == "queued"
    print("✅ File saved and verified in DB.")


def test_background_service():
    service = QueueFileService(uploaded_callback=uploaded_callback,config=config)

    
    pending_files = service.db.search_files({"status":[service.STATUS_QUEUED,service.STATUS_UPLOADING]})
    service.start_background_service()

    # Let the worker pick it up
    time.sleep(10)
    pending_files_ = service.db.search_files({"status":[service.STATUS_QUEUED,service.STATUS_UPLOADING]})
    print(f"File record before {len(pending_files)} and after {len(pending_files_)} processing:")
    # Check if file was processed (may still fail since FTP will fail unless mocked)
    # file_record = service.db.search_files({"batch_id": batch_id})[0]
    # assert len(pending_files)==len(pending_files_)==0
    print(f"File record after processing:")
    print(json.dumps(service.db.get_file_status_summary(),indent=4))

    service.stop_background_service()
    

    # os.remove(file)

def test_retry_failed_upload():
    service = QueueFileService(uploaded_callback=uploaded_callback,config=config)
    file = get_db_path("non_existing_file.zip")
    with open(file, "wb") as f:
        f.write(os.urandom(1024))
    # Insert a fake failed file for testing retry
    file = {
        "batch_id": "test_batch",
        "reference": "test_reference",
        "file_path": file,
        "file_name": "non_existing_file.zip",
        "file_type": "zip",
        "sub_type": "archive",
        "file_size": 1024,
        "resolution": None,
        "status": "failed",
        "priority": 2,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "metadata": "{}",
    }
    service.db.insert_file(file)

    file_record = service.db.search_files({"batch_id": "test_batch"})[0]
    file_id = file_record["id"]

    print(f"Retrying file ID: {file_id}")
    success = service.retry_upload(file_id)
    assert success
    print("✅ Retry triggered successfully.")

def test_query_batches():
    service = QueueFileService(uploaded_callback=uploaded_callback,config=config)
    files = service.db.search_files({})
    print(f"All files in DB:\n{json.dumps([dict(f) for f in files], indent=2)}")

if __name__ == "__main__":
    # test_save_camera_results()
    # test_background_service()
    # test_retry_failed_upload()
    # test_query_batches()
    # print("✅ All tests completed.")
    files = QueueFileService(None,None)
    queue = files.get_queue_status()
    print(queue)
