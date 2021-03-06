import asyncio
import logging
from asyncio import sleep

from django.conf import settings
from django.core.management import BaseCommand
from django.utils import translation
from django.utils.translation import gettext as _
from telegram import Bot
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, \
    MessageHandler, PollAnswerHandler, \
    filters

from bot.commands import handle_dice, handle_enroll, handle_forget, handle_members, handle_query_callback, \
    handle_replies, roll, start, version
from games.commands import add_game, del_game, handle_choose, handle_play, list_games
from polls.commands import poll_answer, weeklypoll

logger = logging.getLogger(f'gamebot.{__name__}')


async def set_commands():
    bot = Bot(settings.TELEGRAM_TOKEN)

    for lang in settings.LANGUAGES:
        logger.info(f'Setting commands for {lang}')
        translation.activate(lang[0])
        commands = [
            # ('start', 'Start'),
            ('weeklypoll', _('manage a weekly poll')),
            ('version', _('show version')),
            ('roll', _('pick a random user')),
            ('add', _('add game to your collection')),
            ('list', _('list your games or group games')),
            ('del', _('remove a game from your collection')),
            ('enroll', _('register yourself')),
            ('forget', _('forget yourself')),
            ('play', _('record play')),
            ('choose', _('choose a game to play')),
        ]
        await bot.set_my_commands(commands, language_code=lang[0])
        await sleep(1)


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

        app = ApplicationBuilder().token(settings.TELEGRAM_TOKEN).arbitrary_callback_data(True).build()

        # Add commands
        app.add_handler(CommandHandler('start', start))
        app.add_handler(CommandHandler('weeklypoll', weeklypoll))
        app.add_handler(CommandHandler('version', version))
        app.add_handler(CommandHandler('roll', roll))
        app.add_handler(CommandHandler('add', add_game, ))
        app.add_handler(CommandHandler('del', del_game, ))
        app.add_handler(CommandHandler('list', list_games))
        app.add_handler(CommandHandler('play', handle_play))
        app.add_handler(CommandHandler('enroll', handle_enroll))
        app.add_handler(CommandHandler('forget', handle_forget))
        app.add_handler(CommandHandler('choose', handle_choose))

        app.add_handler(PollAnswerHandler(poll_answer))
        app.add_handler(CallbackQueryHandler(handle_query_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_replies))
        app.add_handler(MessageHandler(filters.Dice.ALL, handle_dice))
        app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_members))
        app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, handle_members))

        # app.add_handler(MessageHandler(filters.ALL, handle_unwanted))

        # Start Bot
        logger.info('Starting Bot...')
        app.run_polling()
