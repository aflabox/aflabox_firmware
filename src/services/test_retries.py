import json
import asyncio
import threading
from tinydb import Query
from utils.thread_locks import get_db
import aiohttp

class TestRetryWorker:
    def __init__(self,config, db_path='retry_queue.json', retry_interval=60):
        self.db = get_db(db_path)
        self.config = config
        create_test_endpoint = self.config.get('ENDPOINTS','createTest')
        #ToDo ensure we have this entry in yaml
        base_url = self.config.get('ENDPOINTS','base_url')
        self.url = f"{base_url}{create_test_endpoint}"
        self.url = "https://api.aflabox.ai/crop/tests"
        
        self.retry_interval = retry_interval
        
        self.stop_event = threading.Event()

    async def start(self):
        self.thread = threading.Thread(target=self.run_in_thread, daemon=True)
        self.thread.start()

    async def stop(self):
        self.stop_event.set()
        if self.thread.is_alive():
                self.thread.join(timeout=5)

    def run_in_thread(self):
        asyncio.run(self._async_main())

    async def _async_main(self):
        print(f"called _async_main")

        while not self.stop_event.is_set():
            await self.retry_failed_tests()
            await asyncio.sleep(self.retry_interval)

    async def retry_failed_tests(self):
        headers = {'Content-Type': 'application/json'}
        data = self.db.all()
        if len(data)==0:
            print("No tests to retry")
            return
        for item in data:
            reference = item.get('reference')
            data_json = json.dumps(item)

            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(self.url, data=data_json, headers=headers) as response:
                        status = response.status
                        print(f"Retry POST {self.url} for reference '{reference}' status: {status}")

                        if status == 200:
                            self.db.remove(doc_ids=[item.doc_id])
                            print(f"Successfully resent and removed reference '{reference}' from retry queue.")
                        else:
                            print(f"Retry failed for reference '{reference}', will retry later.")

                except Exception as e:
                    print(f"Exception during retry for reference '{reference}': {e}")

