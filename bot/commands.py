import logging
import os
from asyncio import sleep
from random import randint

import pendulum
from django.conf import settings
from django.utils import translation
from django.utils.translation import gettext as _
from munch import munchify
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import CallbackContext

from polls.models import delete_weekly_poll, get_weekly_poll, get_wp_partecipating_users, new_weekly_poll, \
    update_poll_answer

logger = logging.getLogger(f'gamebot.{__name__}')


async def start(update: Update, context: CallbackContext.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=_("Welcome to Game Night Bot!"))

    await context.bot.set_my_commands((
        ('start', 'Start'),
        ('weeklypoll', 'manage a weekly poll'),
        ('version', 'show version'),
        ('roll', 'pick a random user')
    ))


async def callBack(update: Update, context: CallbackContext.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    await query.answer()

    if context.bot_data.get('weeklypoll'):
        await weeklypoll(update, context)


async def weeklypoll(update: Update, context: CallbackContext.DEFAULT_TYPE) -> None:
    """Manages weekly polls"""

    # check if user is channel admin
    if update.effective_chat.id < 0:
        # checks only for grups
        admins = await update.effective_chat.get_administrators()
        if update.effective_user.id not in [admin.user.id for admin in admins]:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=_("You must be an administrator of this channel to use this feature.")
            )
            return

    translation.activate(update.effective_user.language_code)
    if update.callback_query:
        query = update.callback_query
        payload = munchify(context.bot_data)

        if payload.weeklypoll.field == 'weekday':
            payload.weeklypoll.weekday = query.data

            if query.data == '0':
                await query.edit_message_text(
                    text=_("Weekly poll not updated")
                )
                await sleep(5)
                await query.message.delete()
                return

            await delete_weekly_poll(update.effective_chat.id)

            if query.data == '-1':
                await query.edit_message_text(
                    text=_("Weekly poll deleted")
                )

                await sleep(5)
                await query.message.delete()
            else:
                # save weekly poll
                new = await new_weekly_poll(update.effective_chat.id, int(query.data))
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
                "weeklypoll": {
                    'field': 'weekday',
                    'chat_id': update.effective_chat.id
                }
            }
            context.bot_data.update(payload)
        else:
            keyboard = [[
                InlineKeyboardButton(_("Monday"), callback_data=pendulum.MONDAY),
                InlineKeyboardButton(_("Tuesday"), callback_data=pendulum.TUESDAY),
                InlineKeyboardButton(_("Wednesday"), callback_data=pendulum.WEDNESDAY),
            ], [
                InlineKeyboardButton(_("Thursday"), callback_data=pendulum.THURSDAY),
                InlineKeyboardButton(_("Friday"), callback_data=pendulum.FRIDAY),
                InlineKeyboardButton(_("Saturday"), callback_data=pendulum.SATURDAY),
            ], [
                InlineKeyboardButton(_("Sunday"), callback_data=pendulum.SUNDAY),
            ]]

            reply_markup = InlineKeyboardMarkup(keyboard)

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=_("Day of the week?"),
                reply_markup=reply_markup
            )
            payload = {
                "weeklypoll": {
                    'field': 'weekday',
                    'chat_id': update.effective_chat.id
                }
            }
            context.bot_data.update(payload)
    # await update.message.reply_text("Please choose:", reply_markup=reply_markup)


async def version(update: Update, context: CallbackContext.DEFAULT_TYPE) -> None:
    """Sends the version of the bot"""
    from toml import load
    toml_file = load(os.path.join(settings.BASE_DIR, 'pyproject.toml'))

    print(toml_file)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"{toml_file.get('tool').get('poetry').get('description')}\nVersion {toml_file.get('tool').get('poetry').get('version')}"
    )


async def handle_dice(update: Update, context: CallbackContext.DEFAULT_TYPE) -> None:
    """Handles dice rolls"""
    print(update.effective_chat.id)


async def roll(update: Update, context: CallbackContext.DEFAULT_TYPE) -> None:
    """Roll a dice for every user on the current poll"""

    wp = await get_weekly_poll(update.effective_chat.id)
    if not wp or not wp.message_id:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_("No weekly poll available")
        )
    users = await get_wp_partecipating_users(wp.id)  # get poll users

    userstable = "\n".join([user['user_name'] for user in users])
    msg = await context.bot.send_message(update.effective_chat.id, _(f"Choosing an user from:\n\n{userstable}"))
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    await sleep(2)
    winner = randint(0, len(users) - 1)
    await msg.edit_text(text=_(f"I choose {users[winner]['user_name']}!"))


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


async def poll_answer(update: Update, context: CallbackContext.DEFAULT_TYPE) -> None:
    """User answers a poll"""
    name = update.poll_answer.user.first_name if update.poll_answer.user.first_name else update.poll_answer.user.username if update.poll_answer.user.username else None
    await update_poll_answer(
        poll_id=update.poll_answer.poll_id,
        user_id=update.poll_answer.user.id,
        answer=update.poll_answer.option_ids,
        user_name=name
    )
    # print(update.poll_answer.to_json())


async def poll(update: Update, context: CallbackContext.DEFAULT_TYPE) -> None:
    """Sends a predefined poll"""
    answers = [_("Yes"), _("No")]
    question = _("Change Me")
    message = await context.bot.send_poll(
        update.effective_chat.id,
        question,
        answers,
        is_anonymous=False,
        allows_multiple_answers=False,
    )

    await message.pin()
    from polls.models import new_poll
    await new_poll(message.message_id, update.effective_chat.id, question, answers)

    payload = {
        message.poll.id: {
            "question": question,
            "message_id": message.message_id,
            "chat_id": update.effective_chat.id,
            "answers": 0,
        }
    }
    context.bot_data.update(payload)
