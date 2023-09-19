import logging
from typing import Optional

import pendulum
import telegram
from asgiref.sync import async_to_sync
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext as _
from django_rq import get_queue
from telegram import Bot
from telegram.error import BadRequest

from bot.models import Chat, cru_user
from gamebot.decorators import database_sync_to_async

logger = logging.getLogger(f"gamebot.{__name__}")


class WeeklyPoll(models.Model):
    poll_id = models.BigIntegerField(null=True, blank=True)
    chat = models.ForeignKey("bot.Chat", on_delete=models.CASCADE, null=True)
    message_id = models.BigIntegerField(null=True, blank=True)
    weekday = models.IntegerField(null=True, blank=True)
    lang = models.CharField(max_length=5, default="en")
    question_prefix = models.CharField(max_length=200, default="")
    answers = ArrayField(models.CharField(max_length=50), default=list)
    poll_date = models.DateField(null=True, blank=True)
    errors = models.IntegerField(default=0)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.chat_id} - {self.weekday}"


class WeeklyPollAnswer(models.Model):
    wp = models.ForeignKey(WeeklyPoll, on_delete=models.CASCADE)
    user = models.ForeignKey("bot.User", on_delete=models.CASCADE)
    answer = models.IntegerField(
        null=True, blank=True, choices=((0, _("Yes")), (1, _("No")))
    )
    answer_date = models.DateTimeField("date answered", auto_now=True)

    def __str__(self):
        return f"{self.wp} - {self.user_id}"


@receiver(post_save, sender=WeeklyPoll, dispatch_uid="_save")
def weekly_poll_save(instance, **kwargs):
    from polls.tasks import update_weekly_poll

    job_id = f"update_weekly_poll_{instance.chat_id}"
    if not get_queue().fetch_job(job_id) or settings.DEBUG:
        update_weekly_poll.delay(instance.id, job_id=job_id)


@database_sync_to_async
def cru_update_weekly_poll(
    chat_id: int,
    weekday: int,
    lang: str = "en",
    question_prefix: str = "",
    answers: dict = [],
) -> bool:
    chat, created = Chat.objects.get_or_create(id=chat_id)
    db_poll, created = WeeklyPoll.objects.get_or_create(chat=chat)
    db_poll.lang = lang
    db_poll.weekday = weekday
    db_poll.poll_date = pendulum.now().next(weekday).date()
    db_poll.question_prefix = question_prefix
    db_poll.answers = answers
    db_poll.save()
    return created


@database_sync_to_async
def get_weekly_poll(chat_id: int = None, poll_id: int = None) -> Optional[WeeklyPoll]:
    try:
        if chat_id:
            return WeeklyPoll.objects.get(chat_id=chat_id)
        if poll_id:
            return WeeklyPoll.objects.get(poll_id=poll_id)
    except ObjectDoesNotExist:
        return None


@database_sync_to_async
def update_poll_answer(poll_id: int, user: telegram.User, answer: []) -> bool:
    u, created = cru_user(user)
    try:
        wp = WeeklyPoll.objects.get(poll_id=poll_id)
        wa, created = WeeklyPollAnswer.objects.get_or_create(wp_id=wp.id, user=u)
        wa.answer = answer[0] if answer else None
        wa.user = u
        wa.save()
        logger.info(f"{wa.user.name} answered {wa.get_answer_display()} - {wp.weekday}")

        from bot.tasks import new_chat_user_task

        new_chat_user_task.delay(wp.chat_id, u.id)

    except ObjectDoesNotExist:
        logger.warning(f"poll {poll_id} does not exist")
        return False

    return created


@database_sync_to_async
def get_wp_partecipating_users(wp_id: int) -> []:
    wp = WeeklyPoll.objects.get(id=wp_id)
    return list(
        wp.weeklypollanswer_set.filter(answer=0).values("user__id", "user__username")
    )


@database_sync_to_async
def delete_weekly_poll(chat_id: int) -> bool:
    try:
        wp = WeeklyPoll.objects.get(chat_id=chat_id)

        if wp.message_id:
            try:
                async_to_sync(Bot(settings.TELEGRAM_TOKEN).stop_poll)(
                    wp.chat_id, wp.message_id
                )
                async_to_sync(Bot(settings.TELEGRAM_TOKEN).unpin_chat_message)(
                    wp.chat_id, wp.message_id
                )
            except BadRequest:
                # already unpinned or poll already closed
                pass

            # if pool is in the future delete it
            if wp.poll_date > pendulum.now().date():
                async_to_sync(Bot(settings.TELEGRAM_TOKEN).delete_message)(
                    wp.chat_id, wp.message_id
                )

        wp.delete()
        return True
    except ObjectDoesNotExist:
        return False
