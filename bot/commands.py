from telegram import Update
from telegram.ext import CallbackContext


async def start(update: Update, context: CallbackContext.DEFAULT_TYPE):
    print("start")
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")
