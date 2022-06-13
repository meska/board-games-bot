import logging

from django.conf import settings
from django.core.management import BaseCommand
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, \
    MessageHandler, PollAnswerHandler, \
    filters

from bot.commands import callBack, handle_dice, poll_answer, roll, start, version, weeklypoll

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
        app = ApplicationBuilder().token(settings.TELEGRAM_TOKEN).build()

        # Add commands
        app.add_handler(CommandHandler('start', start))
        app.add_handler(CommandHandler('weeklypoll', weeklypoll))
        app.add_handler(CommandHandler('version', version))
        app.add_handler(CommandHandler('roll', roll))
        app.add_handler(PollAnswerHandler(poll_answer))
        app.add_handler(CallbackQueryHandler(callBack))
        app.add_handler(MessageHandler(filters.Dice.ALL, handle_dice))

        # Start Bot
        logger.info('Starting Bot...')
        app.run_polling()
