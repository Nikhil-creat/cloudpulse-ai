from celery import Celery

from app.core.config import get_settings

celery = Celery("cloudpulse", broker=get_settings().redis_url, backend=get_settings().redis_url,
                include=["app.workers.tasks"])
celery.conf.update(
    task_default_queue="default",
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={"app.workers.tasks.run_cnn": {"queue": "cnn"}, "app.workers.tasks.apply_plan": {"queue": "apply"}},
    beat_schedule={
        "collect-metrics": {"task": "app.workers.tasks.collect_all", "schedule": 60.0},
        "cnn-sweep": {"task": "app.workers.tasks.run_cnn", "schedule": 900.0},
    },
)
