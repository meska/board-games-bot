import logging

import pendulum
from asgiref.sync import async_to_sync
from django.conf import settings
from django.utils.translation import gettext as _
from django_rq import job
from telegram import Bot

logger = logging.getLogger(f'gamebot.{__name__}')


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
            bot = Bot(settings.TELEGRAM_TOKEN)
            async_to_sync(bot.stop_poll)(wp.chat_id, wp.message_id)
            bot = Bot(settings.TELEGRAM_TOKEN)
            async_to_sync(bot.unpin_chat_message)(wp.chat_id, wp.message_id)
            wp.message_id = None
            wp.poll_date = None
            updated = True

    if not wp.poll_date:
        # set next date
        wp.poll_date = pendulum.now().next(wp.weekday).date()
        updated = True

    if diff < 7 and not wp.message_id:
        # create the poll on telegram
        bot = Bot(settings.TELEGRAM_TOKEN)
        poll = async_to_sync(bot.send_poll)(
            wp.chat_id, f"{_('Game Night')} {wp.poll_date.strftime('%A %-d %b')}", [_('Yes'), _('No')],
            is_anonymous=False)
        bot = Bot(settings.TELEGRAM_TOKEN)
        async_to_sync(bot.pin_chat_message)(wp.chat_id, poll.message_id)
        wp.message_id = poll.message_id
        updated = True

    if updated:
        logger.debug(f'update_weekly_poll({poll_id})')
        WeeklyPoll.objects.filter(id=poll_id).update(
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
        update_weekly_poll.delay(wp.id)
