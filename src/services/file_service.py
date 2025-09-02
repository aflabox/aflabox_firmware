import os
import threading
import time
import logging
import queue
import asyncio
from datetime import datetime
from db.file_queuedb import QueueFileServiceDB
import traceback
import os
import time
import json
import ftplib
import threading
import queue,asyncio
import logging
import ssl
from datetime import datetime, timedelta


from utils.helpers import safe_run,publish_to_exchange
from utils.thread_locks import get_db
from utils.logger import get_logger

# local_storage = threading.local()
local_storage=QueueFileServiceDB()

def get_db_connection():
    # Create a new connection for this thread if it doesn't exist
    # if not hasattr(local_storage, 'db'):
    #     local_storage.db = QueueFileServiceDB()
    # return local_storage.db
    return local_storage

class QueueFileService:
    """
    A service for managing file upload queues and background processing.
    
    Features:
    - Persistent queue management using TinyDB
    - Background FTP upload service with retry logic
    - Priority-based uploading (thumbnails first)
    - Upload tracking and progress reporting
    - File retention management
    """
    
    # File status constants
    STATUS_QUEUED = 'queued'
    STATUS_UPLOADING = 'uploading'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    
    # File types for priority
    TYPE_THUMBNAIL = 'thumbnail'
    TYPE_IMAGE = 'image'
    TYPE_ZIP = 'zip'
    
    def __init__(self, config=None,uploaded_callback=None):
       
        # Default configuration
        self.config = {
            'db_path': 'queue_service.json',
            'log_level': 'INFO',
            'ftp_host': 'localhost',
            'ftp_user': 'anonymous',
            'ftp_pass': 'anonymous@',
            'ftp_remote_dir': '/',
            'use_tls': True,
            'verify_ssl': True,
            'max_retries': 3,
            'retry_delay': 5,
            'worker_threads': 2,
            'check_interval': 60,
            'retention_days': 7
        }
        
        self.device_id = None
        
        # Update with provided config
        if config:
            self.config.update(config)
        self.uploaded_callback=uploaded_callback
        
        # Set up logging
        self.logger = get_logger('QueueFileService')
        
     
        # Set up worker queue and threads
        self.upload_queue = queue.PriorityQueue()
        self.workers = []
        self.running = False
     
   
        
       
    
    def save_camera_results(self, results, reference=None):
        """
        Save camera capture results to the queue database.
        
        Args:
            results (dict): Camera capture results dictionary
            reference (str, optional): Reference identifier for this batch
            
        Returns:
            str: Batch ID for the saved results
        """
        if not reference:
            reference = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
        batch_id = reference
        timestamp = datetime.now().isoformat()
        
        self.logger.info(f"Saving camera results with batch_id: {batch_id}")
        db = get_db_connection()
        files_to_queue = []
        
        
        
        # Process zip file
        if 'zip' in results and 'path' in results['zip'] and os.path.exists(results['zip']['path']):
            zip_data = results['zip']
            file_record = {
                'batch_id': batch_id,
                'reference': reference,
                'file_path': zip_data['path'],
                'file_name': os.path.basename(zip_data['path']),
                'file_type': self.TYPE_ZIP,
                'sub_type': 'archive',
                'file_size': zip_data.get('file_size', os.path.getsize(zip_data['path'])),
                'resolution': None,
                'status': self.STATUS_QUEUED,
                'priority': 3,  # Low priority
                'created_at': timestamp,
                'updated_at': timestamp,
                'remote_path': None,
                'remote_url': None,
                'upload_attempts': 0,
                'upload_progress': 0,
                'upload_complete': False,
                'metadata': zip_data
            }
            files_to_queue.append(file_record)
        
        # Save records to database
        print(files_to_queue)
        for record in files_to_queue:
            record_id = db.insert_file(record)
            self.logger.debug(f"Queued file {record['file_name']} with ID {record_id}")
            
            # Add to upload queue with priority
            self.upload_queue.put((record['priority'], record_id))
        #db.close()
        self.logger.info(f"Added {len(files_to_queue)} files to queue for batch {batch_id}")
        return batch_id
    
    def start_background_service(self):
        """Start the background upload service with worker threads."""
        if self.running:
            self.logger.warning("Background service is already running")
            return False
            
        self.logger.info(f"Starting background service with {self.config['worker_threads']} workers")
        self.running = True
        
        # Create cleanup thread
        cleanup_thread = threading.Thread(
            target=self._cleanup_thread,
            name="CleanupThread",
            daemon=True
        )
        cleanup_thread.start()
        
        # Create worker threads
       
        for i in range(int(self.config['worker_threads'])):
            worker = threading.Thread(
                target=self._upload_worker,
                name=f"UploadWorker-{i+1}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
            
        # Queue any existing files that were queued previously
        self._requeue_pending_files()
        
        return True
    
    def stop_background_service(self):
        """Stop the background upload service."""
        if not self.running:
            self.logger.warning("Background service is not running")
            return False
            
        self.logger.info("Stopping background service")
        self.running = False
        
        # Wait for workers to finish current jobs
        for worker in self.workers:
            if worker.is_alive():
                worker.join(timeout=5)
                
        self.workers = []
        self.logger.info("Background service stopped")
        
        return True
    async def monitor_and_upload(self, interval=15):
        self.logger.info("Starting async file monitor and uploader...")
        self.running = True
        self._tick_counter = 0

        while self.running:
            try:
                pending_files = self._requeue_pending_files()
            except Exception as e:
                self.logger.error(f"Error in file monitoring loop: {e}", exc_info=True)
                pending_files = []

            if not pending_files:
                await asyncio.sleep(interval)
            else:
                await asyncio.sleep(interval * 0.5)

            if self._tick_counter % 10 == 0:
                self.logger.info("File monitor still running...")
            self._tick_counter += 1

    def _requeue_pending_files(self):
        """Requeue any files that were previously queued but not uploaded."""
        db = get_db_connection()
        pending_files = db.search_files({"status":[self.STATUS_QUEUED,self.STATUS_UPLOADING]})
        
        # Reset status for files that were being uploaded
        for file in pending_files:
            if file['status'] == self.STATUS_UPLOADING:
                db.update_file(file['id'],
                    {'status': self.STATUS_QUEUED, 'updated_at': datetime.now().isoformat()}
                )
                
            # Add to queue
            self.upload_queue.put((file['priority'], file['id']))
        #db.close()   
        self.logger.info(f"Requeued {len(pending_files)} pending files")
        return pending_files
    
    def _upload_worker(self):
        """Worker thread for uploading files."""
        self.logger.info(f"Upload worker {threading.current_thread().name} started")
        
        while self.running:
            try:
                db = get_db_connection()
                # Get next file to upload with priority
                try:
                    priority, doc_id = self.upload_queue.get(timeout=2)
                except queue.Empty:
                    continue
                
                # Get file details from database
                file_record = db.get_file(file_id=doc_id)
                if not file_record:
                    self.logger.warning(f"File record {doc_id} not found in database")
                    self.upload_queue.task_done()
                    continue
                
                # Check if file exists
                if not os.path.exists(file_record['file_path']):
                    self.logger.error(f"File not found: {file_record['file_path']}")
                    db.update_file(file_id=doc_id,
                        updates={
                            'status': self.STATUS_FAILED,
                            'updated_at': datetime.now().isoformat(),
                            'file_error': 'File not found'
                        }
                    )
                    self.upload_queue.task_done()
                    continue
                
                # Update status to uploading
                self.logger.error(f"File uploading: {file_record['file_path']}")
                db.update_file(file_id=doc_id,
                        updates={
                            'status': self.STATUS_UPLOADING,
                            'updated_at': datetime.now().isoformat(),
                        }
                    )
                
                
                self.logger.info(f"Uploading file {file_record['file_name']} (Priority: {priority})")
                
                # Upload the file
                try:
                    start_time=time.time()
                    success, remote_path, error = self._upload_file(file_record)
                    duration = time.time()-start_time
                    
                    if success:
                        # Update status to completed
                        
                        
                        db.update_file(doc_id,
                            {
                                'status': self.STATUS_COMPLETED,
                                'remote_path': remote_path,
                                'remote_url': f"ftp://{self.config['ftp_host']}/{remote_path}",
                                'upload_progress': 100,
                                'upload_complete': True,
                                'updated_at': datetime.now().isoformat(),
                                'remote_path': remote_path,
                                'upload_date': datetime.now().isoformat(),
                                'upload_success': True
                            })
                        
                        self.logger.info(f"Successfully uploaded {file_record['file_name']}")
                        if callable(self.uploaded_callback):
                            callback_data={
                                'file_name': file_record['file_name'],
                                'remote_path': remote_path,
                                'upload_duration': duration,
                                "notification_type":"UPLOAD_DONE"
                                
                            }
                            try:
                                self.uploaded_callback(callback_data)
                                
                                pass
                            except Exception as e:
                                import inspect

                                print("🔍 Callback Info:")
                                print("➡️ Name:", self.uploaded_callback.__name__)
                                print("➡️ Type:", type(self.uploaded_callback))
                                print("➡️ Args:", inspect.signature(self.uploaded_callback))
                                print("➡️ Source location:", inspect.getsourcefile(self.uploaded_callback))
                                self.logger.error(f"uploaded_callback Error: {e}")
                      
                    else:
                        # Check if we should retry
                        attempts = file_record['upload_attempts'] + 1
                        if attempts < int(self.config['max_retries']):
                            # Requeue with lower priority
                            new_priority = min(5, priority + 1)  # Max priority is 5
                            db.update_file(doc_id,
                                {
                                    'status': self.STATUS_QUEUED,
                                    'upload_attempts': attempts,
                                    'priority': new_priority,
                                    'file_error': error,
                                    'updated_at': datetime.now().isoformat()
                                }
                            )
                            self.logger.warning(
                                f"Upload failed for {file_record['file_name']}, "
                                f"retrying later (Attempt {attempts}/{self.config['max_retries']})"
                            )
                            
                            # Add back to queue with delay
                            time.sleep(int(self.config['retry_delay']))
                            self.upload_queue.put((new_priority, doc_id))
                        else:
                            # Mark as failed
                            db.update_file(doc_id,
                                {
                                    'status': self.STATUS_FAILED,
                                    'upload_attempts': attempts,
                                    'updated_at': datetime.now().isoformat(),
                                    'upload_success': False,
                                    'upload_error': error
                                }
                            )
                            self.logger.error(
                                f"Upload failed for {file_record['file_name']} after "
                                f"{attempts} attempts: {error}"
                            )
                            
                except Exception as e:
                    self.logger.error(f"Upload worker error (360): {str(e)}")
                    # Mark as failed with error
                    traceback.print_stack()
                    db.update_file(doc_id,
                        {
                            'status': self.STATUS_FAILED,
                            'upload_error': str(e),
                            'updated_at': datetime.now().isoformat()
                        }
                    )
                
                self.upload_queue.task_done()
                    
            except Exception as e:
                self.logger.error(f"Unexpected error in upload worker: {str(e)}",exc_info=True)
                time.sleep(5)  # Prevent CPU thrashing on repeated errors
            finally:
                db.close()
            
        
        self.logger.info(f"Upload worker {threading.current_thread().name} stopped")
    
    def _upload_file(self, file_record,db=None):
        """
        Upload a file to the FTP server using secure FTP_TLS.
        
        Args:
            file_record (dict): File record from database
            
        Returns:
            tuple: (success, remote_path, error_message)
        """
        file_path = file_record['file_path']
        file_name = file_record['file_name']
        file_size = file_record['file_size']
        doc_id = file_record['id']
        if db is None:
            db =  get_db_connection()
        notify_data = {
           "file": file_name,
           "reference":file_record['reference'],
           "device_id":self.device_id
        }
        
        # Determine remote path
        remote_dir = self.config['ftp_remote_dir']
        if not remote_dir.endswith('/'):
            remote_dir += '/'
            
        # Add batch ID and file type as subdirectories
        batch_sub_dir = f"{file_record['batch_id']}/"
        type_sub_dir = f"{file_record['file_type']}/"
        full_remote_dir = remote_dir + batch_sub_dir + type_sub_dir
        remote_path = full_remote_dir + file_name
        
        try:
            # Connect to FTP server with TLS if enabled
            if self.config.get('use_tls', True):
                # Create FTP_TLS connection
                ftp = ftplib.FTP_TLS(self.config['ftp_host'])
                
                # Configure SSL verification
                if not self.config.get('verify_ssl', True):
                    # Disable SSL certificate verification for self-signed certificates
                    context = ssl.SSLContext(ssl.PROTOCOL_TLS)
                    context.verify_mode = ssl.CERT_NONE
                    ftp.context = context
                
                # Login and enable data protection
                ftp.login(self.config['ftp_user'], self.config['ftp_pass'])
                ftp.prot_p()  # Set up secure data connection
            else:
                # Use regular FTP
                ftp = ftplib.FTP(self.config['ftp_host'])
                ftp.login(self.config['ftp_user'], self.config['ftp_pass'])
            
            try:
                # Create directories if they don't exist
                self._ensure_ftp_directory(ftp, remote_dir)
                self._ensure_ftp_directory(ftp, remote_dir + batch_sub_dir)
                self._ensure_ftp_directory(ftp, full_remote_dir)
                
                # Upload the file with progress tracking
                with open(file_path, 'rb') as file:
                    # Add a transfered counter to the FTP object
                    ftp.transfered = 0
                    
                    # Define callback for tracking transfer progress
                    def callback(data):
                        ftp.transfered += len(data)
                        if ftp.transfered % (1024 * 128) == 0:  # Update DB every 128KB
                            progress = min(100, int((ftp.transfered / file_size) * 100))
                            try:
                                db = get_db_connection()
                                db.update_file(doc_id,
                                    {'upload_progress': progress},
                                    
                                )
                                db.close()
                            except Exception as e:
                                pass
                            
                            
                            if callable(self.uploaded_callback):
                                notify_data["upload_progress"]=progress
                                notify_data["doc_id"]=doc_id
                                notify_data["notification_type"]="UPLOAD_PROGRESS"
                                self.uploaded_callback(notify_data)
                            else:
                                self.logger.error(f"uploaded_callback not called {file_name}")
                            
                        
                    
                    # Store the file
                    ftp.storbinary(f'STOR {remote_path}', file, 8192, callback)
                ftp.quit()
                notify_data["upload_progress"]=100
                notify_data["notification_type"]="UPLOAD_DONE"
                
                safe_run(publish_to_exchange("image.uploads", notify_data, "IMAGE.MAIN"))
                return True, remote_path, None
            except Exception as e:
                error_msg = f"Upload error: {str(e)}"
                self.logger.error(f"Upload error: {e}")
                traceback.print_stack()
            
            finally:
                self.logger.info(f"finally uploaded fn called {file_name}")
                # Ensure FTP connection is closed
                db.close()
                if ftp:
                    try:
                        ftp.quit()
                    except:
                        pass
            return False, None, error_msg
                
        except ftplib.all_errors as e:
            error_msg = f"FTP error: {str(e)}"
            self.logger.error(f"FTP upload failed for {file_name}: {error_msg}")
            return False, None, error_msg
            
        except Exception as e:
            error_msg = f"Upload error: {str(e)}"
            self.logger.error(f"Upload failed for {file_name}: {error_msg}")
            return False, None, error_msg
    def addDeviceId(self,device_id):
        self.device_id=device_id
    def _ensure_ftp_directory(self, ftp, directory):
        """
        Ensure that a directory exists on the FTP server, creating it if necessary.
        
        Args:
            ftp (ftplib.FTP): FTP connection
            directory (str): Directory path
        """
        try:
            ftp.cwd(directory)
            return  # Directory exists
        except ftplib.all_errors:
            try:
                # Try to create the directory
                ftp.mkd(directory)
                return
            except ftplib.all_errors as e:
                # Create each directory in the path
                parts = directory.strip('/').split('/')
                current = '/'
                for part in parts:
                    if not part:
                        continue
                    current = current + part + '/'
                    try:
                        ftp.cwd(current)
                    except ftplib.all_errors:
                        try:
                            ftp.mkd(current)
                            ftp.cwd(current)
                        except ftplib.all_errors as e:
                            self.logger.error(f"Failed to create directory {current}: {str(e)}")
                            raise
    
    def _cleanup_thread(self):
        """Cleanup thread for managing file retention."""
        self.logger.info("Cleanup thread started")
        db = get_db_connection()
        while self.running:
            try:
                # Sleep for the check interval
                for _ in range(int(self.config['check_interval'])):
                    if not self.running:
                        break
                    time.sleep(1)
                
                if not self.running:
                    break
                
                # Clean up old completed uploads
                self._cleanup_old_files(db)
                
            except Exception as e:
                self.logger.error(f"Error in cleanup thread: {str(e)}")
        
        self.logger.info("Cleanup thread stopped")
    
    def _cleanup_old_files(self, db=None):
        """Clean up files that have been completed and are older than retention period."""
        retention_days = int(self.config['retention_days'])
        db = get_db_connection()
        if retention_days <= 0:
            return  # Retention disabled
            
        self.logger.info(f"Cleaning up files older than {retention_days} days")
        
        # Calculate cutoff timestamp
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        cutoff_timestamp = cutoff_date.isoformat()
        
        # Find completed files older than cutoff
      
        old_files = db.search_files({"status":self.STATUS_COMPLETED,"created_before":cutoff_timestamp,"upload_complete":True})
        #     (File.status == self.STATUS_COMPLETED) & 
        #     (File.created_at < cutoff_timestamp) &
        #     (File.upload_complete == True)
        # )
        
        deleted_count = 0
        for file in old_files:
            try:
                # Check if file exists and delete
                if os.path.exists(file['file_path']):
                    os.remove(file['file_path'])
                    deleted_count += 1
                    self.logger.debug(f"Deleted old file: {file['file_path']}")
                
                # Update status in database
                db.update_file(file['id'],
                    {'file_deleted': True, 'updated_at': datetime.now().isoformat()}
                )
                
            except Exception as e:
                self.logger.error(f"Error deleting file {file['file_path']}: {str(e)}")
        
        if deleted_count > 0:
            self.logger.info(f"Cleaned up {deleted_count} old files")
    
    # Query methods
    def get_queue_status(self):
        """
        Get a summary of the current queue status.
        
        Returns:
            dict: Status summary
        """
        db = get_db_connection()
       
        queued_count = len(db.search_files({"status":self.STATUS_QUEUED}))
        uploading_count = len(db.search_files({"status":self.STATUS_UPLOADING}))
        completed_count = len(db.search_files({"status":self.STATUS_COMPLETED}))
        failed_count = len(db.search_files({"status":self.STATUS_FAILED}))
        
        return {
            'queued': queued_count,
            'uploading': uploading_count,
            'completed': completed_count,
            'failed': failed_count,
            'total': queued_count + uploading_count + completed_count + failed_count,
            'workers_active': len([w for w in self.workers if w.is_alive()]),
            'service_running': self.running,
            'timestamp': datetime.now().isoformat()
        }
    
    def query_files(self, status=None, batch_id=None, reference=None, file_type=None, limit=None):
        """
        Query files in the database with filtering.
        
        Args:
            status (str, optional): Filter by status
            batch_id (str, optional): Filter by batch ID
            reference (str, optional): Filter by reference
            file_type (str, optional): Filter by file type
            limit (int, optional): Limit the number of results
            
        Returns:
            list: Matching file records
        """
        db = get_db_connection()

        query_conditions = []
        
        if status:
            query_conditions.append({"status":status})
        
        if batch_id: 
            query_conditions.append({"batch_id":batch_id})
        
        if reference:
            query_conditions.append({"reference":reference})
        
        if file_type:
            query_conditions.append({"file_type":file_type})
            
         # Apply limit
        if limit and limit > 0:
            query_conditions.append({"limit":limit})
        
        # Combine conditions
        if not query_conditions:
            # No filters, get all files
            results = db.search_files()
        else:
            # Apply filters
            combined_query = query_conditions[0]
            for condition in query_conditions[1:]:
                combined_query = combined_query.update(condition)
                
            results = db.search_files(combined_query)
        
        #db.close()
            
        return results
    
    def get_batches(self):
        """
        Get a list of all unique batch IDs in the database.
        
        Returns:
            list: Unique batch IDs with summary information
        """
        db = get_db_connection()
        all_files = db.search_files()
        
        # Group by batch ID
        batches = {}
        for file in all_files:
            batch_id = file['batch_id']
            if batch_id not in batches:
                batches[batch_id] = {
                    'batch_id': batch_id,
                    'reference': file['reference'],
                    'created_at': file['created_at'],
                    'file_count': 0,
                    'status_summary': {
                        self.STATUS_QUEUED: 0,
                        self.STATUS_UPLOADING: 0,
                        self.STATUS_COMPLETED: 0,
                        self.STATUS_FAILED: 0
                    },
                    'file_types': set()
                }
            
            # Update counts
            batches[batch_id]['file_count'] += 1
            batches[batch_id]['status_summary'][file['status']] += 1
            batches[batch_id]['file_types'].add(file['file_type'])
        
        # Convert sets to lists for JSON serialization
        for batch in batches.values():
            batch['file_types'] = list(batch['file_types'])
        
        # Sort by creation date (newest first)
        sorted_batches = sorted(
            batches.values(),
            key=lambda x: x['created_at'],
            reverse=True
        )
        #db.close()
        return sorted_batches
    
    def retry_upload(self, file_id):
        """
        Retry a specific failed upload.
        
        Args:
            file_id (int): Document ID of the file to retry
            
        Returns:
            bool: Success status of the retry operation
        """
        self.logger.info(f"Attempting to retry upload for file ID: {file_id}")
        db = get_db_connection()
        # Get the file record
        file_record = db.get_file(file_id)
        if not file_record:
            self.logger.warning(f"File ID {file_id} not found in database")
            return False
        
        # Check if file exists
        if not os.path.exists(file_record['file_path']):
            self.logger.error(f"File not found: {file_record['file_path']}")
            return False
        
        # Reset status and attempts
        db.update_file(file_id,
            {
                'status': self.STATUS_QUEUED,
                'upload_attempts': 0,
                'file_error': None,
                'updated_at': datetime.now().isoformat()
            }
        )
        
        # Add to queue with original priority
        priority = file_record['priority']
        self.upload_queue.put((priority, file_id))
        #db.close()
        self.logger.info(f"Upload for file {file_record['file_name']} has been requeued")
        return True
    
    def retry_multiple_uploads(self, file_ids):
        """
        Retry multiple failed uploads.
        
        Args:
            file_ids (list): List of document IDs to retry
            
        Returns:
            dict: Results of retry operations
        """
        results = {
            'successful': [],
            'failed': []
        }
        
        self.logger.info(f"Attempting to retry {len(file_ids)} uploads")
        
        for file_id in file_ids:
            if self.retry_upload(file_id):
                results['successful'].append(file_id)
            else:
                results['failed'].append(file_id)
        
        self.logger.info(f"Retry operation completed. {len(results['successful'])} successful, {len(results['failed'])} failed")
        return results
    
    def retry_all_failed_uploads(self):
        """
        Retry all failed uploads.
        
        Returns:
            dict: Results of retry operations
        """
       
        db = get_db_connection()
        failed_files = db.search_files({"status":self.STATUS_FAILED})
        
        file_ids = [file['id'] for file in failed_files]
        
        if not file_ids:
            self.logger.info("No failed uploads to retry")
            return {'successful': [], 'failed': []}
        
        self.logger.info(f"Retrying all {len(file_ids)} failed uploads")
        #db.close()
        return self.retry_multiple_uploads(file_ids)
    
    def delete_completed_files(self, older_than_days=None, batch_id=None, reference=None):
        """
        Delete files that have been successfully uploaded.
        
        Args:
            older_than_days (int, optional): Only delete files older than this number of days
            batch_id (str, optional): Filter by batch ID
            reference (str, optional): Filter by reference
            
        Returns:
            int: Number of files deleted
        """
        
        db = get_db_connection()
        filters = {
            'status': self.STATUS_COMPLETED,
            'upload_complete':1
        }
        
        if older_than_days is not None and older_than_days > 0:
            filters = filters|{"older_than_days":older_than_days}
            
        if batch_id:
            filters = filters|{"batch_id":batch_id}
            
        if reference:
            filters = filters|{"reference":reference}
       
        completed_files = db.search_files(reference)
        
        deleted_count = 0
        for file in completed_files:
            try:
                if os.path.exists(file['file_path']):
                    os.remove(file['file_path'])
                    deleted_count += 1
                    self.logger.debug(f"Deleted file: {file['file_path']}")
                
                # Update status in database
                db.update_file(file['id'],
                    {'file_deleted': True, 'updated_at': datetime.now().isoformat()}
                    
                )
                
            except Exception as e:
                self.logger.error(f"Error deleting file {file['file_path']}: {str(e)}")
        
        self.logger.info(f"Manually deleted {deleted_count} completed files")
        return deleted_count
    
    def purge_old_records(self, older_than_days=30):
        """
        Purge old records from the database where files have been deleted.
        
        Args:
            older_than_days (int): Only purge records older than this many days
            
        Returns:
            int: Number of records purged
        """
        db = get_db_connection()
        if older_than_days <= 0:
            return 0
            
        cutoff_date = datetime.now() - timedelta(days=older_than_days)
        cutoff_timestamp = cutoff_date.isoformat()
        
      
        old_records = db.search_files({"file_deleted":1,"updated_at_before":cutoff_timestamp})

        
        record_ids = [record.doc_id for record in old_records]
        if record_ids:
            self.files_table.remove(doc_ids=record_ids)
            self.logger.info(f"Purged {len(record_ids)} old records from database")
          
        return len(record_ids)
    
    def __enter__(self):
        """Context manager entry."""
        # self.start_background_service()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        # self.stop_background_service()
        return False if exc_type else True


