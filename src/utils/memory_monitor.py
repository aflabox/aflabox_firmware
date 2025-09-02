#!/usr/bin/env python3
import asyncio
import gc
import logging
import time
import os
import sys
from datetime import datetime
from .logger import get_logger

logger = get_logger("memory_monitor")

class MemoryMonitor:
    """
    A class to monitor memory usage in Python applications
    
    Features:
    - Periodic memory usage tracking
    - Memory leak detection
    - Memory usage logging and alerting
    - Process-wide memory statistics
    - Optional tracemalloc integration for detailed tracking
    
    Example usage:
    
    # Synchronous:
    monitor = MemoryMonitor(interval=60)
    monitor.start_sync()
    # ...later...
    monitor.stop()
    
    # Asynchronous:
    monitor = MemoryMonitor(interval=60)
    task = await monitor.start_monitoring()
    # ...later...
    monitor.stop()
    """
    
    def __init__(self, interval=60, logger=None, alert_threshold_mb=500, 
                 enable_tracemalloc=False, max_snapshots=5, log_dir=None):
        """
        Initialize the memory monitor
        
        Args:
            interval (int): Polling interval in seconds
            logger: Logger instance to use (creates one if None)
            alert_threshold_mb (int): Memory threshold in MB to trigger alerts
            enable_tracemalloc (bool): Whether to use tracemalloc for detailed tracking
            max_snapshots (int): Maximum number of memory snapshots to keep
            log_dir (str): Directory to save memory logs (None for no file logging)
        """
        self.interval = interval
        self.logger = logger or logging.getLogger("memory_monitor")
        self.alert_threshold_mb = alert_threshold_mb
        self.enable_tracemalloc = enable_tracemalloc
        self.max_snapshots = max_snapshots
        self.log_dir = log_dir
        
        self.running = False
        self._task = None
        self._snapshots = []
        self._peak_memory = 0
        self._tracemalloc_enabled = False
        self._start_time = None
        
        # Initialize tracemalloc if requested
        if self.enable_tracemalloc:
            self._setup_tracemalloc()
    
    def _setup_tracemalloc(self):
        """Setup tracemalloc for detailed memory tracking"""
        try:
            import tracemalloc
            if not tracemalloc.is_tracing():
                tracemalloc.start(25)  # Capture 25 frames
                self._tracemalloc_enabled = True
                self.logger.info("Tracemalloc enabled for detailed memory tracking")
            else:
                self._tracemalloc_enabled = True
                self.logger.info("Using existing tracemalloc instance")
        except ImportError:
            self.logger.warning("Tracemalloc not available, detailed tracking disabled")
            self._tracemalloc_enabled = False
    
    def _get_process_memory(self):
        """Get current memory usage of the process"""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            return {
                'rss': memory_info.rss / (1024 * 1024),  # RSS in MB
                'vms': memory_info.vms / (1024 * 1024),  # VMS in MB
                'shared': getattr(memory_info, 'shared', 0) / (1024 * 1024),  # Shared in MB
                'percent': process.memory_percent(),
                'system_total': psutil.virtual_memory().total / (1024 * 1024),  # Total system memory in MB
                'system_available': psutil.virtual_memory().available / (1024 * 1024)  # Available system memory in MB
            }
        except ImportError:
            # Fallback to simpler memory reporting if psutil is not available
            import resource
            rusage = resource.getrusage(resource.RUSAGE_SELF)
            if sys.platform == 'darwin':  # macOS
                # On macOS, ru_maxrss is in bytes
                rss = rusage.ru_maxrss / (1024 * 1024)
            else:  # Linux, etc.
                # On Linux, ru_maxrss is in KB
                rss = rusage.ru_maxrss / 1024
            return {
                'rss': rss,
                'vms': 0,  # Not available without psutil
                'shared': 0,  # Not available without psutil
                'percent': 0,  # Not available without psutil
                'system_total': 0,  # Not available without psutil
                'system_available': 0  # Not available without psutil
            }
    
    def _get_tracemalloc_stats(self):
        """Get detailed memory allocation statistics from tracemalloc"""
        if not self._tracemalloc_enabled:
            return None
            
        try:
            import tracemalloc
            snapshot = tracemalloc.take_snapshot()
            
            # Store snapshot for leak detection
            self._snapshots.append((time.time(), snapshot))
            if len(self._snapshots) > self.max_snapshots:
                self._snapshots.pop(0)
            
            # Get top statistics
            top_stats = snapshot.statistics('lineno')
            
            # Calculate total traced memory
            traced_memory = sum(stat.size for stat in top_stats)
            
            # Return useful information
            return {
                'traced_memory_mb': traced_memory / (1024 * 1024),
                'top_allocations': [
                    {
                        'file': stat.traceback[0].filename,
                        'line': stat.traceback[0].lineno,
                        'size_mb': stat.size / (1024 * 1024)
                    }
                    for stat in top_stats[:10]  # Return top 10 allocations
                ]
            }
        except Exception as e:
            self.logger.error(f"Error getting tracemalloc stats: {e}")
            return None
    
    def _detect_memory_leaks(self):
        """Analyze snapshots to detect potential memory leaks"""
        if len(self._snapshots) < 2:
            return None
            
        try:
            import tracemalloc
            
            # Get oldest and newest snapshots
            oldest_time, oldest = self._snapshots[0]
            newest_time, newest = self._snapshots[-1]
            
            # Skip if time difference is too small
            if newest_time - oldest_time < self.interval * 2:
                return None
            
            # Compare snapshots
            comparison = newest.compare_to(oldest, 'lineno')
            
            # Filter significant increases
            significant_increases = [
                {
                    'file': stat.traceback[0].filename,
                    'line': stat.traceback[0].lineno,
                    'size_diff_mb': stat.size_diff / (1024 * 1024),
                    'count_diff': stat.count_diff
                }
                for stat in comparison 
                if stat.size_diff > 100 * 1024  # Only report increases over 100KB
            ]
            
            return {
                'time_diff': newest_time - oldest_time,
                'significant_increases': significant_increases[:10]  # Return top 10 increases
            }
        except Exception as e:
            self.logger.error(f"Error detecting memory leaks: {e}")
            return None
    
    def _log_to_file(self, memory_info, tracemalloc_stats, leak_detection):
        """Log memory information to a file"""
        if not self.log_dir:
            return
            
        try:
            os.makedirs(self.log_dir, exist_ok=True)
            log_file = os.path.join(self.log_dir, f"memory_{datetime.now().strftime('%Y%m%d')}.log")
            
            with open(log_file, 'a') as f:
                f.write(f"=== Memory Report: {datetime.now().isoformat()} ===\n")
                f.write(f"RSS: {memory_info['rss']:.2f} MB\n")
                f.write(f"VMS: {memory_info['vms']:.2f} MB\n")
                f.write(f"Memory usage: {memory_info['percent']:.2f}%\n")
                f.write(f"System memory: {memory_info['system_available']:.2f} MB available of {memory_info['system_total']:.2f} MB\n")
                
                if tracemalloc_stats:
                    f.write(f"Traced memory: {tracemalloc_stats['traced_memory_mb']:.2f} MB\n")
                    f.write("Top allocations:\n")
                    for alloc in tracemalloc_stats['top_allocations']:
                        f.write(f"  {alloc['file']}:{alloc['line']} - {alloc['size_mb']:.2f} MB\n")
                
                if leak_detection and leak_detection['significant_increases']:
                    f.write(f"Potential memory leaks (over {leak_detection['time_diff']:.1f} seconds):\n")
                    for leak in leak_detection['significant_increases']:
                        f.write(f"  {leak['file']}:{leak['line']} - increased by {leak['size_diff_mb']:.2f} MB ({leak['count_diff']} objects)\n")
                
                f.write("\n")
        except Exception as e:
            self.logger.error(f"Error writing memory log to file: {e}")
    
    async def _monitor(self):
        """Core monitoring loop"""
        self._start_time = time.time()
        
        while self.running:
            try:
                # Trigger garbage collection
                gc.collect()
                
                # Get memory information
                memory_info = self._get_process_memory()
                tracemalloc_stats = self._get_tracemalloc_stats() if self._tracemalloc_enabled else None
                leak_detection = self._detect_memory_leaks() if self._tracemalloc_enabled and len(self._snapshots) > 1 else None
                
                # Update peak memory
                if memory_info['rss'] > self._peak_memory:
                    self._peak_memory = memory_info['rss']
                
                # Log memory information
                uptime = time.time() - self._start_time
                self.logger.info(f"Memory usage: {memory_info['rss']:.2f} MB RSS, peak: {self._peak_memory:.2f} MB, uptime: {uptime/3600:.1f}h")
                
                # Check for high memory usage
                if memory_info['rss'] > self.alert_threshold_mb:
                    self.logger.warning(f"High memory usage detected: {memory_info['rss']:.2f} MB (threshold: {self.alert_threshold_mb} MB)")
                    
                    # Log more detailed information on high memory
                    if tracemalloc_stats:
                        for alloc in tracemalloc_stats['top_allocations']:
                            self.logger.warning(f"Top memory allocation: {alloc['file']}:{alloc['line']} - {alloc['size_mb']:.2f} MB")
                
                # Log potential memory leaks
                if leak_detection and leak_detection['significant_increases']:
                    self.logger.warning(f"Potential memory leaks detected:")
                    for leak in leak_detection['significant_increases']:
                        self.logger.warning(f"Memory increase: {leak['file']}:{leak['line']} - {leak['size_diff_mb']:.2f} MB ({leak['count_diff']} objects)")
                
                # Log to file if enabled
                self._log_to_file(memory_info, tracemalloc_stats, leak_detection)
                
                # Wait for next interval
                await asyncio.sleep(self.interval)
                
            except asyncio.CancelledError:
                self.logger.debug("Memory monitoring task cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in memory monitoring: {e}")
                await asyncio.sleep(self.interval)  # Continue monitoring despite errors
    
    async def start_monitoring(self):
        """Start monitoring memory usage (async version)"""
        if self.running:
            return self._task
            
        self.running = True
        self._task = asyncio.create_task(self._monitor())
        
        # Set a descriptive name for the task if supported
        if hasattr(self._task, 'set_name'):
            self._task.set_name("memory_monitor")
            
        return self._task
    
    def start_sync(self):
        """Start monitoring in a separate thread (sync version)"""
        if self.running:
            return
            
        self.running = True
        
        import threading
        
        def run_monitoring():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._monitor())
            finally:
                loop.close()
        
        thread = threading.Thread(target=run_monitoring, daemon=True)
        thread.start()
        return thread
    
    def stop(self):
        """Stop memory monitoring"""
        self.running = False
        if self._task and not self._task.done():
            self._task.cancel()
    
    def get_summary(self):
        """Get a summary of memory statistics"""
        memory_info = self._get_process_memory()
        uptime = time.time() - (self._start_time or time.time())
        
        return {
            'current_rss_mb': memory_info['rss'],
            'peak_rss_mb': self._peak_memory,
            'uptime_seconds': uptime,
            'system_available_mb': memory_info['system_available'],
            'system_total_mb': memory_info['system_total']
        }
    
    def log_snapshot(self, label=None):
        """Manually trigger a memory snapshot with optional label"""
        memory_info = self._get_process_memory()
        tracemalloc_stats = self._get_tracemalloc_stats() if self._tracemalloc_enabled else None
        
        snapshot_label = label or f"manual_snapshot_{datetime.now().isoformat()}"
        
        self.logger.info(f"Memory snapshot '{snapshot_label}': {memory_info['rss']:.2f} MB RSS")
        
        # Store additional information about this snapshot
        snapshot_info = {
            'label': snapshot_label,
            'timestamp': datetime.now().isoformat(),
            'memory_info': memory_info,
            'tracemalloc_stats': tracemalloc_stats
        }
        
        # Optionally log to file
        if self.log_dir:
            try:
                os.makedirs(self.log_dir, exist_ok=True)
                snapshot_file = os.path.join(self.log_dir, f"memory_snapshot_{snapshot_label}.log")
                
                with open(snapshot_file, 'w') as f:
                    import json
                    json.dump(snapshot_info, f, indent=2, default=str)
            except Exception as e:
                self.logger.error(f"Error writing snapshot to file: {e}")
        
        return snapshot_info

