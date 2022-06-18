import logging
import os
from asyncio import sleep
from random import randint

from django.conf import settings
from django.utils import translation
from django.utils.translation import gettext as _
from telegram import ForceReply, Update
from telegram.constants import ChatAction
from telegram.ext import CallbackContext, InvalidCallbackData

from bot.models import forget_user, get_user, left_chat_user, new_chat_user
from polls.models import get_weekly_poll, get_wp_partecipating_users

logger = logging.getLogger(f'gamebot.{__name__}')


async def start(update: Update, context: CallbackContext.DEFAULT_TYPE):
    translation.activate(update.effective_user.language_code)
    if context.args and context.args[0] == "games":
        from games.commands import handle_games
        await handle_games(update, context)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=_("Welcome to Game Night Bot!"))


async def handle_query_callback(update: Update, context: CallbackContext.DEFAULT_TYPE) -> None:
    """
        Query Callback router
    """
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    await query.answer()

    if isinstance(query.data, InvalidCallbackData):
        await query.message.delete()
        return
    if query.data.get('handler') == 'weeklypoll':
        from polls.commands import weeklypoll
        await weeklypoll(update, context)
    elif query.data.get('handler') == 'games':
        from games.commands import handle_games
        await handle_games(update, context)
    elif query.data.get('handler') == 'play':
        from games.commands import handle_play
        await handle_play(update, context)
    else:
        # context gone, delete the message
        await query.message.delete()


async def handle_replies(update: Update, context: CallbackContext.DEFAULT_TYPE) -> None:
    """
        Reply router
    """

    if context.user_data.get('play_score'):
        from games.commands import handle_score
        await handle_score(update, context)
        return

    if context.user_data.get('forgetting'):
        await handle_forget(update, context)
        return

    query = update.callback_query
    if not query or isinstance(query.data, InvalidCallbackData):
        return

    if query and query.message:
        await query.message.delete()

    if isinstance(query.data, dict) and query.data.get('handler') == 'games':
        from games.commands import handle_games
        await handle_games(update, context)
    else:
        # context gone, delete the message
        await query.message.delete()


async def version(update: Update, context: CallbackContext.DEFAULT_TYPE) -> None:
    """Sends the version of the bot"""
    from toml import load
    toml_file = load(os.path.join(settings.BASE_DIR, 'pyproject.toml'))

    print(toml_file)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"{toml_file.get('tool').get('poetry').get('description')}\nVersion {toml_file.get('tool').get('poetry').get('version')}"
    )


# noinspection PyUnusedLocal
async def handle_dice(update: Update, context: CallbackContext.DEFAULT_TYPE) -> None:
    """Handles dice rolls"""
    print(update.effective_chat.id)


# noinspection PyUnusedLocal
async def handle_enroll(update: Update, context: CallbackContext.DEFAULT_TYPE) -> None:
    """
        Register user in the bot, useful when the bot is addedd later to the group
    """
    translation.activate(update.effective_user.language_code)

    await new_chat_user(update.effective_chat, update.effective_user)
    db_user = await get_user(update.effective_user.id)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=_(
            f"You are now enrolled in GameBot {db_user.name}\nyour telegram id and name will be stored to enable all functions.\nYou can also use /forget to remove your registration and delete your data."
        )
    )


# noinspection PyUnusedLocal
async def handle_forget(update: Update, context: CallbackContext.DEFAULT_TYPE) -> None:
    """
        Forget user data
    """

    translation.activate(update.effective_user.language_code)

    if context.user_data.get('forgetting') and (
            update.message.text.lower().strip() == _("yes") or update.message.text.lower().strip() == 'yes'):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_("Ok, I will delete your data")
        )
        await forget_user(update.effective_user)
        await context.bot.send_animation(
            chat_id=update.effective_chat.id,
            animation="https://tenor.com/view/south-park-and-its-gone-sad-talking-its-finished-gif-17584433"
        )

        context.user_data.clear()
    elif context.user_data.get('forgetting'):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_("Ok, I will not delete your data")
        )
        context.user_data.clear()
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_(
                "Are you sure you want to delete all your data and statistics ?\nthis operation is not reversible.\nType YES to confirm."
            ),
            reply_markup=ForceReply(selective=True)
        )
        context.user_data['forgetting'] = True


# noinspection PyUnusedLocal
async def handle_unwanted(update: Update, context: CallbackContext.DEFAULT_TYPE) -> None:
    """Message filter ?"""
    print(update.effective_chat.id)


# noinspection PyUnusedLocal
async def handle_members(update: Update, context: CallbackContext.DEFAULT_TYPE) -> None:
    """Keep track of members"""

    user_left = update.message.left_chat_member
    if user_left:
        # remove user from the list of channel members
        logger.info(f"User {user_left.id} left the channel")
        await left_chat_user(update.message.chat, user_left)

    new_chat_members = update.message.new_chat_members
    for member in new_chat_members:
        # add user to the list of channel members
        logger.info(f"User {member.id} joined the channel")
        await new_chat_user(update.message.chat, member)


async def roll(update: Update, context: CallbackContext.DEFAULT_TYPE) -> None:
    """Roll a dice for every user on the current poll"""
    translation.activate(update.effective_user.language_code)
    wp = await get_weekly_poll(update.effective_chat.id)
    if not wp or not wp.message_id:
        msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_("No weekly poll available")
        )
        await sleep(3)
        await msg.delete()
        await update.message.delete()
        return
    users = await get_wp_partecipating_users(wp.id)  # get poll users
    if not users:
        msg = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_("No users participating in the weekly poll, try later")
        )
        await sleep(3)
        await msg.delete()
        await update.message.delete()
        return
    userstable = "\n".join([user['user_name'] for user in users])
    msg = await context.bot.send_message(update.effective_chat.id, _(f"Choosing an user from these:\n\n{userstable}"))
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    await sleep(2)
    winner = randint(0, len(users) - 1)
    await msg.edit_text(text=_(f"I choose {users[winner]['user_name']}!"))
    await sleep(30)
    await msg.delete()
    await update.message.delete()


async def roll_deprecated(update: Update, context: CallbackContext.DEFAULT_TYPE) -> None:
    """Roll a dice for every user on the current poll"""

    wp = await get_weekly_poll(update.effective_chat.id)
    if not wp or not wp.message_id:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_("No weekly poll available")
        )
    users = await get_wp_partecipating_users(wp.id)  # get poll users
    y = 0
    for user in users:
        user['msgname'] = await context.bot.send_message(update.effective_chat.id, f"{user['user_name']}:")
        user['dice'] = await context.bot.send_dice(update.effective_chat.id)
        y += 2
        await sleep(0.1)
    # wait for animations to finish
    await sleep(y)

    # show the winner
    winner_number = 0
    winner_user = None
    for user in users:
        if user['dice'].dice.value > winner_number:
            winner_number = user['dice'].dice.value
            winner_user = user

    await context.bot.send_message(update.effective_chat.id, f"{winner_user['user_name']} wins!")
