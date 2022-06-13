import logging

from django.conf import settings
from django.core.management import BaseCommand
# noinspection PyUnresolvedReferences
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler

from bot.commands import callBack, poll, roll, start, version, weeklypoll

logger = logging.getLogger(f'gamebot.{__name__}')


class Command(BaseCommand):
    """
    Starts Bot

    Command list:

    weeklypoll - manage a weekly poll
    version - show version
    roll - roll a dice

    """

    def handle(self, *args, **options):
        logger.info('Init Bot...')
        bot = ApplicationBuilder().token(settings.TELEGRAM_TOKEN).build()

        # Add commands
        bot.add_handler(CommandHandler('start', start))
        bot.add_handler(CommandHandler('poll', poll))
        bot.add_handler(CommandHandler('weeklypoll', weeklypoll))
        bot.add_handler(CommandHandler('version', version))
        bot.add_handler(CommandHandler('roll', roll))
        bot.add_handler(CallbackQueryHandler(callBack))

        # Start Bot
        logger.info('Starting Bot...')
        bot.run_polling()
