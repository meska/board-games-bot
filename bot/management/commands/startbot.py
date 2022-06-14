import asyncio
import logging

from django.conf import settings
from django.core.management import BaseCommand
from telegram import Bot
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, \
    MessageHandler, PollAnswerHandler, \
    filters

from bot.commands import handle_dice, handle_query_callback, poll_answer, roll, start, version, \
    weeklypoll

logger = logging.getLogger(f'gamebot.{__name__}')


async def set_commands():
    bot = Bot(settings.TELEGRAM_TOKEN)
    await bot.set_my_commands([
        ('start', 'Start'),
        ('weeklypoll', 'manage a weekly poll'),
        ('version', 'show version'),
        ('roll', 'pick a random user')
    ])


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

        loop = asyncio.get_event_loop()
        loop.run_until_complete(set_commands())

        app = ApplicationBuilder().token(settings.TELEGRAM_TOKEN).build()

        # Add commands
        app.add_handler(CommandHandler('start', start))
        app.add_handler(CommandHandler('weeklypoll', weeklypoll))
        app.add_handler(CommandHandler('version', version))
        app.add_handler(CommandHandler('roll', roll))
        app.add_handler(PollAnswerHandler(poll_answer))
        app.add_handler(CallbackQueryHandler(handle_query_callback))
        app.add_handler(MessageHandler(filters.Dice.ALL, handle_dice))
        # app.add_handler(MessageHandler(filters.ALL, handle_unwanted))

        # Start Bot
        logger.info('Starting Bot...')
        app.run_polling()
