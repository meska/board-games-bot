import asyncio
import logging

from django.conf import settings
from django.core.management import BaseCommand
from telegram import Bot
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, \
    MessageHandler, PollAnswerHandler, \
    filters

from bot.commands import handle_dice, handle_members, handle_query_callback, roll, start, version
from games.commands import handle_games
from polls.commands import poll_answer, weeklypoll

logger = logging.getLogger(f'gamebot.{__name__}')


async def set_commands():
    bot = Bot(settings.TELEGRAM_TOKEN)
    await bot.set_my_commands([
        ('start', 'Start'),
        ('weeklypoll', 'manage a weekly poll'),
        ('version', 'show version'),
        ('roll', 'pick a random user'),
        # ('game', 'manage games'),
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
        app.add_handler(CommandHandler('games', handle_games))

        app.add_handler(PollAnswerHandler(poll_answer))
        app.add_handler(CallbackQueryHandler(handle_query_callback))
        app.add_handler(MessageHandler(filters.Dice.ALL, handle_dice))
        app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_members))
        app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, handle_members))
        # app.add_handler(MessageHandler(filters.ALL, handle_unwanted))

        # Start Bot
        logger.info('Starting Bot...')
        app.run_polling()
