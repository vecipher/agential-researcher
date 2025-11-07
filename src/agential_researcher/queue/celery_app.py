from celery import Celery
from .config import settings

# Create Celery instance
celery_app = Celery(
    "agential_researcher",
    broker=settings.broker_url,
    backend=settings.backend_url,
    include=[
        "src.agential_researcher.queue.tasks"
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task routing for different queues with exchange and routing keys
    task_routes={
        "src.agential_researcher.queue.tasks.enqueue_job_task": {"queue": "hot", "routing_key": "hot.tasks"},
        "src.agential_researcher.queue.tasks.summarize_task": {"queue": "hot", "routing_key": "hot.tasks"},
        "src.agential_researcher.queue.tasks.embed_task": {"queue": "hot", "routing_key": "hot.tasks"},
        "src.agential_researcher.queue.tasks.ocr_task": {"queue": "vlm_ocr", "routing_key": "vlm_ocr.tasks"},
        "src.agential_researcher.queue.tasks.vlm_task": {"queue": "vlm_ocr", "routing_key": "vlm_ocr.tasks"},
        "src.agential_researcher.queue.tasks.backfill_task": {"queue": "backfill", "routing_key": "backfill.tasks"},
        "src.agential_researcher.queue.tasks.maintenance_task": {"queue": "maintenance", "routing_key": "maintenance.tasks"},
    },
    # Retry and dead-letter queue configuration
    task_reject_on_worker_lost=True,
    # Retry policy: exponential backoff with max retries
    task_retry_policy={
        'max_retries': 3,
        'interval_start': 0,
        'interval_step': 0.2,
        'interval_max': 0.2,
    },
    # Queue configuration with priority support
    task_queue_max_priority=10,
    task_default_priority=5,
    # Worker configuration
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_memory_per_child=200000,  # 200MB
)

if __name__ == "__main__":
    celery_app.start()