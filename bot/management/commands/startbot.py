from django.conf import settings
from django.core.management import BaseCommand
from telegram.ext import ApplicationBuilder, CommandHandler

from bot.commands import start


class Command(BaseCommand):
    """
    Starts Bot
    """

    def handle(self, *args, **options):
        print("Starting Bot...")
        application = ApplicationBuilder().token(settings.TELEGRAM_TOKEN).build()

        start_handler = CommandHandler('start', start)
        application.add_handler(start_handler)

        application.run_polling()
