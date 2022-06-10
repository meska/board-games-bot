from django.conf import settings
from django.core.management import BaseCommand
# noinspection PyUnresolvedReferences
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler

from bot.commands import callBack, poll, start, weeklypoll


class Command(BaseCommand):
    """
    Starts Bot
    """

    def handle(self, *args, **options):
        print("Init Bot...")
        bot = ApplicationBuilder().token(settings.TELEGRAM_TOKEN).build()

        # Add commands
        bot.add_handler(CommandHandler('start', start))
        bot.add_handler(CommandHandler('poll', poll))
        bot.add_handler(CommandHandler('weeklypoll', weeklypoll))
        bot.add_handler(CallbackQueryHandler(callBack))

        # Start Bot
        print("Start Bot")
        bot.run_polling()
