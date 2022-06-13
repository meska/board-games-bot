import pendulum
from asgiref.sync import async_to_sync
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django_rq import get_queue
from telegram import Bot

from boardgamesbot.decorators import database_sync_to_async


class Poll(models.Model):
    message_id = models.BigIntegerField()
    chat_id = models.BigIntegerField()
    pinned = models.BooleanField(default=False)
    question = models.CharField(max_length=200)
    answers = models.JSONField(default=dict)
    pub_date = models.DateTimeField('date published', auto_now_add=True)

    class Meta:
        unique_together = ('message_id', 'chat_id')

    def __str__(self):
        return self.question


class WeeklyPoll(models.Model):
    poll_id = models.BigIntegerField(null=True, blank=True)
    chat_id = models.BigIntegerField(unique=True)
    message_id = models.BigIntegerField(null=True, blank=True)
    weekday = models.IntegerField(null=True, blank=True)
    poll_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.chat_id} - {self.weekday}"


@receiver(post_save, sender=WeeklyPoll, dispatch_uid='_save')
def weekly_poll_save(instance, **kwargs):
    from polls.tasks import update_weekly_poll
    job_id = f"update_weekly_poll_{instance.chat_id}"
    if not get_queue().fetch_job(job_id):
        update_weekly_poll.delay(instance.id, job_id=job_id)


@database_sync_to_async
def new_poll(message_id, chat_id, question, answers):
    db_poll = Poll(
        message_id=message_id, chat_id=chat_id, question=question, answers=answers,
        pinned=True)
    return db_poll.save()


@database_sync_to_async
def new_weekly_poll(chat_id: int, weekday: int):
    db_poll, created = WeeklyPoll.objects.get_or_create(chat_id=chat_id)
    db_poll.weekday = weekday
    db_poll.poll_date = pendulum.now().next(weekday).date()
    db_poll.save()
    return created


@database_sync_to_async
def get_weekly_poll(chat_id: int):
    try:
        return WeeklyPoll.objects.get(chat_id=chat_id)
    except ObjectDoesNotExist:
        return None


@database_sync_to_async
def delete_weekly_poll(chat_id: int):
    try:
        wp = WeeklyPoll.objects.get(chat_id=chat_id)

        if wp.message_id:
            async_to_sync(Bot(settings.TELEGRAM_TOKEN).stop_poll)(wp.chat_id, wp.message_id)
            async_to_sync(Bot(settings.TELEGRAM_TOKEN).unpin_chat_message)(wp.chat_id, wp.message_id)

            # if pool is in the future delete it
            if wp.poll_date > pendulum.now().date():
                async_to_sync(Bot(settings.TELEGRAM_TOKEN).delete_message)(wp.chat_id, wp.message_id)

        wp.delete()
    except ObjectDoesNotExist:
        return None
