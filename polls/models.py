from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

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
    chat_id = models.BigIntegerField(unique=True)
    message_id = models.BigIntegerField(null=True, blank=True)
    weekday = models.IntegerField(null=True, blank=True)
    poll_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.chat_id


@receiver(post_save, sender=WeeklyPoll, dispatch_uid='_save')
def weekly_poll_save(instance, **kwargs):
    from polls.tasks import update_weekly_poll
    update_weekly_poll.delay(instance.id)


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
    db_poll.save()
    return created


@database_sync_to_async
def get_weekly_poll(chat_id: int):
    return Poll.objects.filter(chat_id=chat_id).first()
