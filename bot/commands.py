from django.utils.translation import gettext as _
from telegram import Update
from telegram.ext import CallbackContext


async def start(update: Update, context: CallbackContext.DEFAULT_TYPE):
    print("start")
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")


async def poll(update: Update, context: CallbackContext.DEFAULT_TYPE) -> None:
    """Sends a predefined poll"""
    questions = [_("Yes"), _("No")]
    message = await context.bot.send_poll(
        update.effective_chat.id,
        "Serata Bla Bla",
        questions,
        is_anonymous=False,
        allows_multiple_answers=False,
    )
    await message.pin()
    payload = {
        message.poll.id: {
            "questions": questions,
            "message_id": message.message_id,
            "chat_id": update.effective_chat.id,
            "answers": 0,
        }
    }
    context.bot_data.update(payload)
