import asyncio
import logging

import pendulum
from django.conf import settings
from django.utils.translation import gettext as _
from django_rq import get_queue, job
from telegram import Bot

logger = logging.getLogger(f'gamebot.{__name__}')


async def new_poll(chat_id, title, answers):
    bot = Bot(settings.TELEGRAM_TOKEN)
    poll = await bot.send_poll(chat_id, title, answers, is_anonymous=False)
    await bot.pin_chat_message(chat_id, poll.message_id)
    return poll.poll.id, poll.message_id


async def stop_poll(chat_id, message_id):
    bot = Bot(settings.TELEGRAM_TOKEN)
    await bot.stop_poll(chat_id, message_id)
    await bot.unpin_chat_message(chat_id, message_id)
    return


@job
def update_weekly_poll(poll_id):
    from polls.models import WeeklyPoll
    logger.debug(f'start update_weekly_poll({poll_id})')
    wp = WeeklyPoll.objects.get(id=poll_id)

    diff = pendulum.now().date().diff(wp.poll_date, False).days

    updated = False

    if wp.message_id:
        # poll is online, check if it's time to update
        if diff < 0:
            # poll is overdue, stop and unpin
            loop = asyncio.get_event_loop()
            coroutine = stop_poll(wp.chat_id, wp.message_id)
            poll_id, message_id = loop.run_until_complete(coroutine)

            wp.message_id = None
            wp.poll_date = None
            updated = True

    if not wp.poll_date:
        # set next date
        wp.poll_date = pendulum.now().next(wp.weekday).date()
        updated = True

    if diff < 7 and not wp.message_id:
        # create the poll on telegram

        loop = asyncio.get_event_loop()
        coroutine = new_poll(wp.chat_id, f"{_('Game Night')} {wp.poll_date.strftime('%A %-d %b')}", [_('Yes'), _('No')])
        message_poll_id, message_id = loop.run_until_complete(coroutine)

        wp.poll_id = message_poll_id
        wp.message_id = message_id
        updated = True

    if updated:
        logger.debug(f'update_weekly_poll({poll_id})')
        WeeklyPoll.objects.filter(id=poll_id).update(
            poll_id=wp.poll_id,
            message_id=wp.message_id,
            poll_date=wp.poll_date
        )
    else:
        logger.debug(f'update_weekly_poll({poll_id}) - nothing to do')


@job
def sync_polls():
    """
    Syncronize polls on channels
    :return:
    :rtype:
    """
    logger.debug('sync_polls() started')
    from polls.models import WeeklyPoll
    for wp in WeeklyPoll.objects.all():
        job_id = f"update_weekly_poll_{wp.chat_id}"
        poll_job = get_queue().fetch_job(job_id)
        if not poll_job:
            update_weekly_poll.delay(wp.id, job_id=job_id)
        if poll_job and not poll_job.is_queued:
            poll_job.delete()
            update_weekly_poll.delay(wp.id, job_id=job_id)
