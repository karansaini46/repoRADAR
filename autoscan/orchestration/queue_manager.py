import os
import logging
from typing import Dict, Any

try:
    import redis
    from rq import Queue, Worker
except ImportError:
    # Ensure smooth failing if dependencies are missing during some test phases
    redis = None
    Queue = None
    Worker = None

logger = logging.getLogger(__name__)

# Standard queue names for the AutoScan pipelines
QUEUE_NAMES = [
    "discovery",
    "enrichment",
    "cloning",
    "scanning",
    "verification",
    "impact",
    "reporting",
    "contacts",
    "outreach",
    "followup"
]

class QueueManager:
    """
    Manages Redis Queue (rq) interactions for distributing background workloads.
    """
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        if redis and Queue:
            try:
                self.conn = redis.from_url(self.redis_url)
                self.queues = {name: Queue(name, connection=self.conn) for name in QUEUE_NAMES}
            except Exception as e:
                logger.error(f"Failed to connect to Redis for QueueManager: {e}")
                self.conn = None
                self.queues = {}
        else:
            logger.warning("redis or rq package not found. QueueManager disabled.")
            self.conn = None
            self.queues = {}

    def enqueue(self, queue_name: str, func, *args, **kwargs) -> str:
        """
        Enqueue a function to a specific queue.
        Returns the job ID.
        """
        if not self.conn or queue_name not in self.queues:
            logger.error(f"Queue {queue_name} not available or Redis disconnected.")
            return None
            
        try:
            # Set a high job_timeout (e.g. 1 hour = 3600s) so batch AI processing 
            # and large repo cloning jobs don't hit the default 180s RQ timeout.
            job = self.queues[queue_name].enqueue(func, *args, job_timeout=3600, **kwargs)
            logger.info(f"Enqueued job {job.id} to queue '{queue_name}'")
            return job.id
        except Exception as e:
            logger.error(f"Failed to enqueue job to {queue_name}: {e}")
            return None

    def get_queue_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Returns stats for all queues: pending, failed, active.
        """
        if not self.conn:
            return {"error": "Redis not connected"}
            
        stats = {}
        for name, q in self.queues.items():
            # In rq, you can get counts of queued and failed jobs
            stats[name] = {
                "pending": q.count,
                "failed": q.failed_job_registry.count if hasattr(q, 'failed_job_registry') else 0,
                "started": q.started_job_registry.count if hasattr(q, 'started_job_registry') else 0,
            }
        return stats

# Global instance
_queue_manager = None

def get_queue_manager() -> QueueManager:
    global _queue_manager
    if _queue_manager is None:
        _queue_manager = QueueManager()
    return _queue_manager
