import logging
import sys
from django.apps import AppConfig

from django_rq import get_queue

logger = logging.getLogger(f"gamebot.{__name__}")


class SchedulerConfig(AppConfig):
    name = "scheduler"
    scheduler = None

    def ready(self):
        """
        Setup scheduler jobs only if i call 'scheduler' management command

        """
        if "--with-scheduler" not in sys.argv:
            return

        queue = get_queue("high")

        job = queue.fetch_job("sync_polls")
        if job:
            job.delete()
            queue.remove(job.id)
        queue.enqueue("polls.tasks.sync_polls", job_id="sync_polls")

        job = queue.fetch_job("healthcheck")
        if job:
            job.delete()
            queue.remove(job.id)
        queue.enqueue("scheduler.tasks.healthcheck", job_id="healthcheck")
