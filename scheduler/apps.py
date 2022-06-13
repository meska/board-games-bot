import logging
import sys
from datetime import datetime
from django.apps import AppConfig
from django_rq import get_scheduler
from importlib import import_module

from scheduler.jobs import jobs

logger = logging.getLogger(f'gamebot.{__name__}')


class SchedulerConfig(AppConfig):
    name = 'scheduler'
    scheduler = None

    def schedule(self, taskname, interval, args=None, kwargs=None):
        """
        Schedule a task to be run every interval seconds.
        """
        # if settings.DEBUG:
        #     return
        mod_name, func_name = taskname.rsplit('.', 1)
        mod = import_module(mod_name)
        func = getattr(mod, func_name)
        res = self.scheduler.schedule(
            datetime.utcnow(), func, args=args, kwargs=kwargs, interval=interval,
            queue_name='high')

        logger.info(f"scheduled job: {res.description} interval: {interval}s")

    def cron(self, taskname, cron_string, args=None, kwargs=None):
        """
        Schedule a task to be run based on 'cron' config.
        """
        mod_name, func_name = taskname.rsplit('.', 1)
        mod = import_module(mod_name)
        func = getattr(mod, func_name)
        res = self.scheduler.cron(cron_string, func, args=args, kwargs=kwargs, queue_name='high')
        logger.info(f"scheduled cron: {res.description} interval: {cron_string}")

    def ready(self):
        """
        Setup scheduler jobs only if i call 'scheduler' management command
        """
        if 'scheduler' not in sys.argv:
            return

        self.scheduler = get_scheduler()

        # cleanup scheduled jobs from previous run
        for scheduled in self.scheduler.get_jobs():
            for j in jobs:
                if scheduled.description.startswith(j['job']):
                    # resync all'avvio
                    logger.info(f"Cleaning scheduled job {scheduled}")
                    scheduled.delete()

        # schedule jobs
        for j in jobs:
            if not j['scheduled']:
                if j.get('interval'):
                    self.schedule(j['job'], interval=j['interval'])
                if j.get('cron'):
                    self.cron(j['job'], j['cron'])
                j['scheduled'] = True
