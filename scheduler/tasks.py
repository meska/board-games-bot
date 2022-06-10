import pytz
from django.conf import settings
from django.utils import timezone
from django_rq import job, queues
from pipenv.vendor.dateutil.relativedelta import relativedelta
from rq.exceptions import NoSuchJobError
from sentry_sdk import capture_exception


def clean_or_recover_errors(queue, jobs_id):
    tz = pytz.timezone('UTC')
    for job_id in jobs_id:
        # considero solo i più vecchi di 1 ora
        job_to_recover = queue.fetch_job(job_id)
        if job_to_recover:
            if job_to_recover.func_name == 'scheduler.tasks.recover_jobs':
                job_to_recover.delete()

            if job_to_recover.ended_at and tz.localize(job_to_recover.ended_at) < (
                    timezone.now() + relativedelta(hours=-1)):
                print(f"Recovering Job {job_to_recover}")
                job_to_recover.requeue()

            if job_to_recover.enqueued_at and tz.localize(job_to_recover.enqueued_at) < (
                    timezone.now() + relativedelta(hours=-2)):
                print(f"Recovering Job {job_to_recover}")
                job_to_recover.requeue()
        else:
            print(f"Recover - Job not found {job_id}")
            queue.remove(job_id)


def clean_deferreds(queue, jobs_id):
    tz = pytz.timezone('UTC')
    for job_id in jobs_id:
        # considero solo i più vecchi di 3 ore
        scheduled_job = queue.fetch_job(job_id)
        if scheduled_job:
            if tz.localize(scheduled_job.created_at) < (timezone.now() + relativedelta(hours=-3)):
                try:
                    father = scheduled_job.dependency
                    print(father)
                except NoSuchJobError:
                    print(f"Recovering deferred job: {scheduled_job}")
                    try:
                        scheduled_job.perform()
                        scheduled_job.delete()
                        father = None
                    except Exception as e:
                        capture_exception(e)
                        continue

                while father is not None:
                    try:
                        father = father.dependency
                        print(father)
                        if tz.localize(scheduled_job.created_at) < (timezone.now() + relativedelta(hours=-6)):
                            # se è più vecchio di 6 ore lo eseguo comunque
                            print(f"Recovering deferred ( 6 ore ) job: {father}")
                            try:
                                father.perform()
                                father.delete()
                                father = None
                            except AttributeError:
                                pass
                            except Exception as e:
                                capture_exception(e)

                    except NoSuchJobError:
                        print(f"Recovering deferred job: {father}")
                        try:
                            father.perform()
                            father.delete()
                            father = None
                        except Exception as e:
                            capture_exception(e)

        else:
            print(f"Deferred - Job not found {job_id}")
            queue.deferred_job_registry.remove(job_id)


@job
def recover_jobs():
    """
    Pulizia dei jobs in coda su startup
    @return:
    """
    rq_queues = [x for x in settings.RQ_QUEUES]
    for q_name in rq_queues:
        q = queues.get_queue(q_name)
        clean_or_recover_errors(q, q.failed_job_registry.get_job_ids())
        clean_deferreds(q, q.deferred_job_registry.get_job_ids())
