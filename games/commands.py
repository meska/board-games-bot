import logging
from asyncio import sleep

from django.utils import translation
from django.utils.translation import gettext as _
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

from bot.models import new_chat_user

logger = logging.getLogger(f'gamebot.{__name__}')


async def handle_games(update: Update, context: CallbackContext.DEFAULT_TYPE) -> None:
    """ Manage games """
    translation.activate(update.effective_user.language_code)
    # check if in a channel
    if update.effective_chat.id < 0:
        warning_msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_("Please message the bot directly to use this feature, to avoid group spam."),
        )

        # add user to the users db for let him choose the channel when setting up games
        admins = await update.effective_chat.get_administrators()
        await new_chat_user(update.effective_chat, update.effective_user,
                            update.effective_user.id in [admin.user.id for admin in admins])
        await sleep(3)
        await warning_msg.delete()
        await update.message.delete()
        return

    if not update.callback_query:
        # choose group
        print('ere')
        keyboard = [[
            InlineKeyboardButton(("👉 " if wp.weekday == pendulum.MONDAY else "") + _("Monday"),
                                 callback_data=pendulum.MONDAY),
            InlineKeyboardButton(("👉 " if wp.weekday == pendulum.TUESDAY else "") + _("Tuesday"),
                                 callback_data=pendulum.TUESDAY),
            InlineKeyboardButton(("👉 " if wp.weekday == pendulum.WEDNESDAY else "") + _("Wednesday"),
                                 callback_data=pendulum.WEDNESDAY),
        ], [
            InlineKeyboardButton(("👉 " if wp.weekday == pendulum.THURSDAY else "") + _("Thursday"),
                                 callback_data=pendulum.THURSDAY),
            InlineKeyboardButton(("👉 " if wp.weekday == pendulum.FRIDAY else "") + _("Friday"),
                                 callback_data=pendulum.FRIDAY),
            InlineKeyboardButton(("👉 " if wp.weekday == pendulum.SATURDAY else "") + _("Saturday"),
                                 callback_data=pendulum.SATURDAY),
        ], [
            InlineKeyboardButton(("👉 " if wp.weekday == pendulum.SUNDAY else "") + _("Sunday"),
                                 callback_data=pendulum.SUNDAY),
            InlineKeyboardButton("❌ " + _("Remove"), callback_data=-1),
            InlineKeyboardButton(_("Cancel"), callback_data=0),
        ]]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_("Existing weekly poll available. Please select a day to update it or choose remove to stop it."),
            reply_markup=reply_markup
        )
        payload = {
            "handle_games": {
                'field': 'weekday',
                'chat_id': update.effective_chat.id
            }
        }
        context.bot_data.update(payload)
