import logging
from asyncio import sleep

from django.utils import translation
from django.utils.translation import gettext as _
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

from games.bgg import get_game, search_game
from games.models import group_games, my_games

logger = logging.getLogger(f'gamebot.{__name__}')


async def add_game(update: Update, context: CallbackContext.DEFAULT_TYPE) -> None:
    """ Add a game """
    translation.activate(update.effective_user.language_code)
    from games.models import add_game as add_game_db
    if not context.args:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_("Please write the name of the game or BGG ID after /add"),
        )
        return

    game = context.args[0]
    if game.isdigit():
        # lookup game by BGG by ID
        game_data = await get_game(game)
        if game_data:
            new = await add_game_db(update.effective_user.id, game_data, update.effective_chat.id)
            caption = _("Game added:") if new else _("Game updated:")
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                parse_mode='Markdown',
                photo=game_data.thumbnail,
                caption=caption + f" [{game_data.name}]({game_data.url})"
            )

        else:
            message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=_(f"Game {game} not found.")
            )
            await sleep(5)
            await message.delete()
    else:
        games = await search_game(game)
        if games:
            keyboard = []
            for game in games[0:10]:
                keyboard.append([
                    InlineKeyboardButton(f"[{game.id}] {game.name} ({game.year})",
                                         callback_data={'handler': 'games', 'data': 'add', 'game': game.id})
                ])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=_("Please choose a game"),
                reply_markup=reply_markup,
            )
        else:
            message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=_(f"No games found with query: {game}.")
            )
            await sleep(5)
            await message.delete()

    await sleep(5)
    await update.message.delete()


async def del_game(update: Update, context: CallbackContext.DEFAULT_TYPE) -> None:
    """ Remove a game from user library """
    translation.activate(update.effective_user.language_code)
    from games.models import remove_game as del_game_db
    if not context.args:
        message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_("Please write the BGG ID  of the game after /del"),
        )
    else:
        game = context.args[0]
        if game.isdigit():
            # lookup game by BGG by ID
            game_data = await get_game(game)
            if game_data:
                await del_game_db(update.effective_user.id, game_data)
                message = await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=_("Game removed:") + f" {game_data.name}"
                )
            else:
                message = await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=_(f"Game {game} not found.")
                )
    await sleep(5)
    await update.message.delete()
    await message.delete()


async def list_games(update: Update, context: CallbackContext.DEFAULT_TYPE) -> None:
    """ List all games """
    translation.activate(update.effective_user.language_code)

    if update.effective_chat.type.name.lower() == 'private':
        games = await my_games(update.effective_user.id)
        label = _("My games")
    else:
        games = await group_games(update.effective_chat.id)
        label = _("Games in this group")

    if games:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            disable_web_page_preview=True,
            parse_mode='Markdown',
            text=label + "\n" + "\n".join(
                [f"[{game.id}] {game.name} ({game.year}) [link]({game.url})" for game
                 in games])
        )
        await sleep(5)
        await update.message.delete()
    else:
        message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_(f"No games found.")
        )
        await sleep(5)
        await update.message.delete()
        await message.delete()


async def handle_games(update: Update, context: CallbackContext.DEFAULT_TYPE) -> None:
    """ Manage games """
    translation.activate(update.effective_user.language_code)

    if not update.callback_query:
        return

    data = update.callback_query.data
    if data['data'] == 'add':
        from games.models import add_game as add_game_db
        game_data = await get_game(data['game'])
        if game_data:
            new = await add_game_db(update.effective_user.id, game_data, update.effective_chat.id)
            caption = _("Game added:") if new else _("Game updated:")
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                parse_mode='Markdown',
                photo=game_data.thumbnail,
                caption=caption + f" [{game_data.name}]({game_data.url})"
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=_(f"Game {data['game']} not found.")
            )

    await update.callback_query.message.delete()
