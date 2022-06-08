from django.conf import settings
from django.core.management import BaseCommand
from telegram.ext import ApplicationBuilder, CommandHandler

from bot.commands import poll, start


class Command(BaseCommand):
    """
    Starts Bot
    """

    def handle(self, *args, **options):
        print("Starting Bot...")
        bot = ApplicationBuilder().token(settings.TELEGRAM_TOKEN).build()

        start_handler = CommandHandler('start', start)

        bot.add_handler(start_handler)
        bot.add_handler(CommandHandler('poll', poll))

        bot.run_polling()
