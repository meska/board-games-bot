import pendulum
from asgiref.sync import async_to_sync
from django.conf import settings
from django.utils.translation import gettext as _
from django_rq import job
from telegram import Bot


@job
def update_weekly_poll(poll_id):
    from polls.models import WeeklyPoll
    wp = WeeklyPoll.objects.get(id=poll_id)
    diff = pendulum.now().date().diff(wp.poll_date, False).days
    bot = Bot(settings.TELEGRAM_TOKEN)
    updated = False

    if wp.message_id:
        # poll is online, check if it's time to update
        if diff < 0:
            # poll is overdue, unpin it and forget it

            async_to_sync(bot.stop_poll)(wp.chat_id, wp.message_id)
            async_to_sync(bot.unpin_chat_message)(wp.chat_id, wp.message_id)
            wp.message_id = None
            wp.poll_date = None
            updated = True

    if not wp.poll_date:
        # set next date
        wp.poll_date = pendulum.now().next(wp.weekday).date()
        updated = True

    if pendulum.now().date().diff(wp.poll_date).days < 7 and not wp.message_id:
        # create the poll on telegram
        bot = Bot(settings.TELEGRAM_TOKEN)
        poll = async_to_sync(bot.send_poll)(
            wp.chat_id, f"{_('Game Night')} {wp.poll_date.strftime('%A %-d %b')}", [_('Yes'), _('No')],
            is_anonymous=False)
        async_to_sync(poll.pin)()
        wp.message_id = poll.message_id
        updated = True

    if updated:
        wp.save()


@job
def sync_polls():
    """
    Syncronize polls on channels
    :return:
    :rtype:
    """
    print('Updating weekly poll...')
    from polls.models import WeeklyPoll
    for wp in WeeklyPoll.objects.all():
        update_weekly_poll.delay(wp.id)
