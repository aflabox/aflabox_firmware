import requests,os
import json,time
from tinydb import TinyDB, Query
from pydantic import BaseModel
from utils.thread_locks import get_db
from utils.logger import get_logger
from db.crop_test_db import CropTestDB
logger = get_logger(__file__)

class CropTestManager:
    def __init__(self, config, tinydb_path='core.db'):
        """
        Initialize CropTestManager with config and TinyDB storage for retries.

        :param config: Dictionary containing 'ENDPOINTS' configuration.
        :param tinydb_path: Path to TinyDB file to store retry data.
        """
        

        self.config = config
        self.db = CropTestDB(tinydb_path)
        
        base_url = self.config.get('ENDPOINTS','base_url')
        create_test_endpoint = self.config.get('ENDPOINTS','createTest')
        self.url = f"{base_url}{create_test_endpoint}"
        self.url = "https://api.aflabox.ai/crop/tests"
    
    def create_test(self, crop_test_data):
        """
        Sends crop test data to the API. If it fails, saves to TinyDB for retry.
        
        :param crop_test_data: Dictionary representing the crop test data.
        """
        headers = {'Content-Type': 'application/json'}
        start_time = time.time()
        # Convert data to JSON string
        
        data_json = crop_test_data.model_dump(mode="json", by_alias=True)
        try:
            response = requests.post(self.url, json=data_json, headers=headers)
            duration  = round(time.time() - start_time, 2)
            if response.status_code==200:
                res = response.json()
                return res.get("id",crop_test_data.reference),True,duration
            else:
                logger.error(f"Failed to create test with status code {response.status_code}")
                
        except Exception:
            logger.error("Error Creating Online Data.",exc_info=True)
            duration  = round(time.time() - start_time, 2)
        try:
            self.save_for_retry(data_json)
        except Exception as e:
            logger.error("Error Saving for retry...",exc_info=True)
        
        
        return crop_test_data.reference,False,duration
        

    def save_for_retry(self, data_json):
        """
        Save failed crop test data to TinyDB for future retry.

        :param crop_test_data: Dictionary representing the crop test data.
        """
        reference = data_json.get('reference')
        if not reference:
            raise ValueError("Crop test data must have a 'reference' field to be saved for retry.")

        # Add to TinyDB with 'reference' acting as a unique key
       
        existing = self.db.get_test_by_reference(reference)

        if existing:
            print(f"Data with reference '{reference}' already exists in retry queue.")
        else:
            self.db.insert_test(reference,data_json)
            print(f"Saved data with reference '{reference}' to retry queue.")

    def retry_failed_tests(self):
        """
        Retry all failed tests stored in TinyDB.
        """
        headers = {'Content-Type': 'application/json'}
        

        for item in self.db.get_all_tests():
            reference = item['reference']
            data_json = json.dumps(item)

            response = requests.post(self.url, data=data_json, headers=headers)
            print(f"Retry POST {self.url} for reference '{reference}' status: {response.text}")

            if response.status_code == 200:
                self.db.remove(doc_ids=[item.doc_id])
                print(f"Successfully resent and removed reference '{reference}' from retry queue.")
            else:
                print(f"Retry failed for reference '{reference}', will retry later.")

