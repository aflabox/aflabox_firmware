from utils.mock_factory import PydanticFactory
from models.models import CropTest
from db.crop_test_db import CropTestDB
from services.test_service import CropTestManager
import json,configparser,os

config_path=os.path.abspath("../config/config.ini")
config_ = configparser.ConfigParser()
config_.read(config_path)

if __name__ == "__main__":
    sample_data = PydanticFactory.generate_random_instance(CropTest)
    # print(sample_data.model_dump_json(indent=2))
    
    
    
    manager = CropTestManager(config_)
    # ref, success, duration = manager.create_test(sample_data)
    # print(f"Test Created: {ref}, Success: {success}, Duration: {duration}s")
    
    manager.retry_failed_tests()