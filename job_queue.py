"""
Advanced Job Queue System for Production-Grade Video Processing
Handles concurrent processing, retry logic, priorities, and metrics
"""

import asyncio
import uuid
import time
import logging
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Callable, Optional, Dict, List, Any
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job lifecycle states"""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"


class JobPriority(Enum):
    """Job priority levels"""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    URGENT = 0


@dataclass
class Job:
    """Represents a video processing job"""
    job_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    user_id: int = 0
    status: JobStatus = JobStatus.PENDING
    priority: JobPriority = JobPriority.NORMAL
    
    # Job data
    session_data: Dict[str, Any] = field(default_factory=dict)
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Retry logic
    attempts: int = 0
    max_retries: int = 3
    last_error: Optional[str] = None
    
    # Progress
    progress: float = 0.0  # 0-100
    status_message: str = "Queued"
    
    # Results
    output_file: Optional[str] = None
    error_message: Optional[str] = None
    
    def duration_seconds(self) -> float:
        """Calculate job duration"""
        if not self.started_at:
            return 0
        end = self.completed_at or datetime.now()
        return (end - self.started_at).total_seconds()
    
    def should_retry(self) -> bool:
        """Check if job should be retried"""
        return (
            self.status == JobStatus.FAILED and
            self.attempts < self.max_retries
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'job_id': self.job_id,
            'user_id': self.user_id,
            'status': self.status.value,
            'priority': self.priority.name,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'attempts': self.attempts,
            'max_retries': self.max_retries,
            'duration_seconds': self.duration_seconds(),
            'progress': self.progress,
            'status_message': self.status_message,
            'error_message': self.error_message,
        }


class JobQueue:
    """Production-grade async job queue with priority, retries, and metrics"""
    
    def __init__(
        self,
        max_concurrent_jobs: int = 5,
        max_queue_size: int = 100,
        worker_timeout: int = 600
    ):
        self.max_concurrent_jobs = max_concurrent_jobs
        self.max_queue_size = max_queue_size
        self.worker_timeout = worker_timeout
        
        # Job storage
        self.jobs: Dict[str, Job] = {}
        self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        
        # Processing
        self.active_jobs: set = set()
        self.worker_task: Optional[asyncio.Task] = None
        
        # Metrics
        self.metrics = {
            'total_jobs': 0,
            'completed_jobs': 0,
            'failed_jobs': 0,
            'total_processing_time': 0,
            'avg_processing_time': 0,
            'success_rate': 0.0,
            'retry_count': 0,
        }
        
        # Handlers
        self.job_handlers: Dict[str, Callable] = {}
    
    async def start(self):
        """Start the queue worker"""
        if self.worker_task is None or self.worker_task.done():
            self.worker_task = asyncio.create_task(self._worker())
            logger.info("🚀 Job queue worker started")
    
    async def stop(self):
        """Stop the queue worker gracefully"""
        if self.worker_task and not self.worker_task.done():
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
        logger.info("⛔ Job queue worker stopped")
    
    async def submit_job(
        self,
        user_id: int,
        session_data: Dict[str, Any],
        priority: JobPriority = JobPriority.NORMAL,
        max_retries: int = 3
    ) -> Job:
        """Submit a new job to the queue"""
        
        # Check queue capacity
        if self.queue.qsize() >= self.max_queue_size:
            raise Exception(f"Queue full ({self.max_queue_size} jobs). Please try again later.")
        
        # Create job
        job = Job(
            user_id=user_id,
            session_data=session_data,
            priority=priority,
            max_retries=max_retries
        )
        
        # Store and queue
        self.jobs[job.job_id] = job
        job.status = JobStatus.QUEUED
        
        # Add to queue with priority (lower number = higher priority)
        await self.queue.put((priority.value, job.job_id))
        
        self.metrics['total_jobs'] += 1
        logger.info(f"📝 Job submitted: {job.job_id} (user: {user_id}, priority: {priority.name})")
        
        return job
    
    async def get_job_status(self, job_id: str) -> Optional[Job]:
        """Get job status and details"""
        return self.jobs.get(job_id)
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a job"""
        job = self.jobs.get(job_id)
        if job and job.status not in [JobStatus.COMPLETED, JobStatus.FAILED]:
            job.status = JobStatus.CANCELLED
            logger.info(f"❌ Job cancelled: {job_id}")
            return True
        return False
    
    def register_handler(self, handler_name: str, handler_func: Callable):
        """Register a job handler function"""
        self.job_handlers[handler_name] = handler_func
        logger.info(f"✓ Registered job handler: {handler_name}")
    
    async def _worker(self):
        """Worker that processes jobs from the queue"""
        logger.info("🔄 Job queue worker starting...")
        
        while True:
            try:
                # Check concurrent job limit
                while len(self.active_jobs) >= self.max_concurrent_jobs:
                    await asyncio.sleep(0.5)
                
                # Get next job from queue with timeout
                try:
                    _, job_id = await asyncio.wait_for(self.queue.get(), timeout=5)
                except asyncio.TimeoutError:
                    continue
                
                job = self.jobs.get(job_id)
                if not job or job.status == JobStatus.CANCELLED:
                    continue
                
                # Process job
                self.active_jobs.add(job_id)
                asyncio.create_task(self._process_job(job))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(1)
    
    async def _process_job(self, job: Job):
        """Process a single job with error handling and retries"""
        try:
            job.status = JobStatus.PROCESSING
            job.started_at = datetime.now()
            job.attempts += 1
            
            logger.info(f"⚙️ Processing job: {job.job_id} (attempt {job.attempts}/{job.max_retries + 1})")
            
            # Call registered handler
            handler = self.job_handlers.get('process_video')
            if not handler:
                raise Exception("No video processor handler registered")
            
            # Execute with timeout
            try:
                result = await asyncio.wait_for(
                    handler(job),
                    timeout=self.worker_timeout
                )
                
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.now()
                job.progress = 100.0
                job.status_message = "Completed successfully"
                job.output_file = result.get('output_file') if result else None
                
                # Update metrics
                duration = job.duration_seconds()
                self.metrics['completed_jobs'] += 1
                self.metrics['total_processing_time'] += duration
                self.metrics['avg_processing_time'] = (
                    self.metrics['total_processing_time'] /
                    self.metrics['completed_jobs']
                )
                self._update_success_rate()
                
                logger.info(
                    f"✅ Job completed: {job.job_id} in {duration:.2f}s"
                )
                
            except asyncio.TimeoutError:
                raise Exception(f"Job timeout after {self.worker_timeout}s")
            
        except Exception as e:
            job.last_error = str(e)
            job.error_message = str(e)
            
            logger.error(f"❌ Job failed: {job.job_id} - {e}")
            
            # Handle retry
            if job.should_retry():
                job.status = JobStatus.RETRY
                job.progress = 0
                job.status_message = f"Retrying (attempt {job.attempts + 1}/{job.max_retries + 1})"
                
                # Re-queue with exponential backoff
                backoff_delay = min(2 ** job.attempts, 60)  # Max 60 seconds
                await asyncio.sleep(backoff_delay)
                await self.queue.put((job.priority.value, job.job_id))
                
                logger.info(f"🔄 Job retrying: {job.job_id} (after {backoff_delay}s backoff)")
                self.metrics['retry_count'] += 1
            else:
                job.status = JobStatus.FAILED
                job.completed_at = datetime.now()
                self.metrics['failed_jobs'] += 1
                self._update_success_rate()
                
                logger.error(f"💥 Job permanently failed: {job.job_id}")
        
        finally:
            self.active_jobs.discard(job.job_id)
    
    def _update_success_rate(self):
        """Calculate current success rate"""
        total = self.metrics['completed_jobs'] + self.metrics['failed_jobs']
        if total > 0:
            self.metrics['success_rate'] = (
                self.metrics['completed_jobs'] / total * 100
            )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get queue metrics for monitoring"""
        return {
            **self.metrics,
            'queue_size': self.queue.qsize(),
            'active_jobs': len(self.active_jobs),
            'total_jobs_in_system': len(self.jobs),
        }
    
    def get_user_jobs(self, user_id: int) -> List[Job]:
        """Get all jobs for a user"""
        return [job for job in self.jobs.values() if job.user_id == user_id]
    
    def cleanup_old_jobs(self, hours: int = 24):
        """Remove completed jobs older than specified hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        removed = 0
        
        for job_id, job in list(self.jobs.items()):
            if (
                job.status in [JobStatus.COMPLETED, JobStatus.FAILED] and
                job.completed_at and
                job.completed_at < cutoff_time
            ):
                del self.jobs[job_id]
                removed += 1
        
        if removed > 0:
            logger.info(f"🧹 Cleaned up {removed} old jobs")
        
        return removed


# Global queue instance
job_queue: Optional[JobQueue] = None


async def init_job_queue(max_concurrent: int = 5) -> JobQueue:
    """Initialize the global job queue"""
    global job_queue
    job_queue = JobQueue(max_concurrent_jobs=max_concurrent)
    await job_queue.start()
    return job_queue


async def get_job_queue() -> JobQueue:
    """Get the global job queue"""
    global job_queue
    if job_queue is None:
        job_queue = await init_job_queue()
    return job_queue
