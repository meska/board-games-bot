import logging
from asyncio import sleep

import pendulum
from django.utils import translation
from django.utils.translation import gettext as _
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

from polls.models import cru_update_weekly_poll, delete_weekly_poll, get_weekly_poll, update_poll_answer

logger = logging.getLogger(f'gamebot.{__name__}')


async def weeklypoll(update: Update, context: CallbackContext.DEFAULT_TYPE) -> None:
    """Manages weekly polls"""
    translation.activate(update.effective_user.language_code)
    # check if user is channel admin
    if update.effective_chat.id < 0:
        # checks only for grups
        admins = await update.effective_chat.get_administrators()
        if update.effective_user.id not in [admin.user.id for admin in admins]:
            warning_msg = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=_("You must be an administrator of this channel to use this feature.")
            )
            await sleep(3)
            await warning_msg.delete()
            await update.message.delete()
            return

    if update.callback_query:
        query = update.callback_query
        weekday = query.data.get('data')

        if weekday == 0:
            await query.edit_message_text(
                text=_("Weekly poll not updated")
            )
            await sleep(5)
            await query.message.delete()
            return

        await delete_weekly_poll(update.effective_chat.id)

        if weekday == -1:
            await query.edit_message_text(
                text=_("Weekly poll deleted")
            )

            await sleep(5)
            await query.message.delete()
        else:
            # save weekly poll
            new = await cru_update_weekly_poll(
                chat_id=update.effective_chat.id,
                weekday=weekday,
                lang=update.effective_user.language_code,
                question_prefix=_('Game Night'),
                answers=[_('Yes'), _('No')]
            )
            if new:
                await query.edit_message_text(
                    text=_("Weekly poll saved")
                )
            else:
                await query.edit_message_text(
                    text=_("Weekly poll updated")
                )

            await sleep(5)
            await query.message.delete()
    else:
        # check existing poll

        wp = await get_weekly_poll(update.effective_chat.id)

        if wp:
            # weekly poll exists

            keyboard = [[
                InlineKeyboardButton(("👉 " if wp.weekday == pendulum.MONDAY else "") + _("Monday"),
                                     callback_data={'handler': 'weeklypoll', 'data': pendulum.MONDAY}),
                InlineKeyboardButton(("👉 " if wp.weekday == pendulum.TUESDAY else "") + _("Tuesday"),
                                     callback_data={'handler': 'weeklypoll', 'data': pendulum.TUESDAY}),
                InlineKeyboardButton(("👉 " if wp.weekday == pendulum.WEDNESDAY else "") + _("Wednesday"),
                                     callback_data={'handler': 'weeklypoll', 'data': pendulum.WEDNESDAY}),
            ], [
                InlineKeyboardButton(("👉 " if wp.weekday == pendulum.THURSDAY else "") + _("Thursday"),
                                     callback_data={'handler': 'weeklypoll', 'data': pendulum.THURSDAY}),
                InlineKeyboardButton(("👉 " if wp.weekday == pendulum.FRIDAY else "") + _("Friday"),
                                     callback_data={'handler': 'weeklypoll', 'data': pendulum.FRIDAY}),
                InlineKeyboardButton(("👉 " if wp.weekday == pendulum.SATURDAY else "") + _("Saturday"),
                                     callback_data={'handler': 'weeklypoll', 'data': pendulum.SATURDAY}),
            ], [
                InlineKeyboardButton(("👉 " if wp.weekday == pendulum.SUNDAY else "") + _("Sunday"),
                                     callback_data={'handler': 'weeklypoll', 'data': pendulum.SUNDAY}),
                InlineKeyboardButton("❌ " + _("Remove"), callback_data={'handler': 'weeklypoll', 'data': -1}),
                InlineKeyboardButton(_("Cancel"), callback_data={'handler': 'weeklypoll', 'data': 0}),
            ]]

            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=_("Existing weekly poll available. Please select a day to update it or choose remove to stop it."),
                reply_markup=reply_markup
            )
        else:
            keyboard = [[
                InlineKeyboardButton(_("Monday"), callback_data={'handler': 'weeklypoll', 'data': pendulum.MONDAY}),
                InlineKeyboardButton(_("Tuesday"), callback_data={'handler': 'weeklypoll', 'data': pendulum.TUESDAY}),
                InlineKeyboardButton(_("Wednesday"),
                                     callback_data={'handler': 'weeklypoll', 'data': pendulum.WEDNESDAY}),
            ], [
                InlineKeyboardButton(_("Thursday"), callback_data={'handler': 'weeklypoll', 'data': pendulum.THURSDAY}),
                InlineKeyboardButton(_("Friday"), callback_data={'handler': 'weeklypoll', 'data': pendulum.FRIDAY}),
                InlineKeyboardButton(_("Saturday"), callback_data={'handler': 'weeklypoll', 'data': pendulum.SATURDAY}),
            ], [
                InlineKeyboardButton(_("Sunday"), callback_data={'handler': 'weeklypoll', 'data': pendulum.SUNDAY}),
            ]]

            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=_("Day of the week?"),
                reply_markup=reply_markup
            )
        await update.message.delete()


# noinspection PyUnusedLocal
async def poll_answer(update: Update, context: CallbackContext.DEFAULT_TYPE) -> None:
    """User answers a poll"""

    await update_poll_answer(
        poll_id=update.poll_answer.poll_id,
        user=update.poll_answer.user,
        answer=update.poll_answer.option_ids
    )
