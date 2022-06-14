import logging
from asyncio import sleep

from django.utils import translation
from django.utils.translation import gettext as _
from telegram import ForceReply, InlineKeyboardButton, InlineKeyboardMarkup, Update
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
            text=f"{_('Please message the bot directly to use this feature, to avoid group spam.')}\nhttps://t.me/{context.bot.username}?start=games"
        )

        # add user to the users db for let him choose the channel when setting up games
        admins = await update.effective_chat.get_administrators()
        await new_chat_user(update.effective_chat, update.effective_user,
                            update.effective_user.id in [admin.user.id for admin in admins])
        await sleep(5)
        await warning_msg.delete()
        await update.message.delete()
        return

    if not update.callback_query:
        # choose group ?
        # from bot.models import my_groups
        # my_groups = await my_groups(update.effective_user.id)
        # if not my_groups:
        #     await context.bot.send_message(
        #         chat_id=update.effective_chat.id,
        #         text=_("You are not in any group. Please join a gaming group to use this feature.")
        #     )
        #     return

        keyboard = [[
            InlineKeyboardButton(_("Show Games"), callback_data={'handler': 'games', 'data': 'list'})
        ], [
            InlineKeyboardButton(_("Add Game"), callback_data={'handler': 'games', 'data': 'add'}),
        ], ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_("Manage your games:"),
            reply_markup=reply_markup
        )
    else:
        query = update.callback_query
        if query.data.get('data') == 'list':
            # show list of games
            from games.models import my_games
            my_games = await my_games(update.effective_user.id)
        if query.data.get('data') == 'add':
            # add a game
            await query.message.delete()
            await context.bot.send_message(
                update.effective_chat.id,
                _("Please enter the name of the game or BGG ID:"),
                reply_markup=ForceReply(selective=True)
            )
