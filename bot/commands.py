import pendulum
from django.utils.translation import gettext as _
from munch import munchify
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

from polls.models import new_weekly_poll


async def start(update: Update, context: CallbackContext.DEFAULT_TYPE):
    print("start")
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")


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

    if update.callback_query:
        query = update.callback_query
        payload = munchify(context.bot_data)

        if payload.weeklypoll.field == 'weekday':
            payload.weeklypoll.weekday = query.data

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
    else:
        # TODO: check existing poll
        # days of the week (1 = Monday, 7 = Sunday) as for date.isoweekday()

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


# answers = [_("Yes"), _("No")]
# question = _("Change Me")
# message = await context.bot.send_poll(
#     update.effective_chat.id,
#     question,
#     answers,
#     is_anonymous=False,
#     allows_multiple_answers=False,
# )

# await message.pin()
# from polls.models import new_poll
# await new_poll(message.message_id, update.effective_chat.id, question, answers)

# payload = {
#     message.poll.id: {
#         "question": question,
#         "message_id": message.message_id,
#         "chat_id": update.effective_chat.id,
#         "answers": 0,
#     }
# }
# context.bot_data.update(payload)


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
