import logging
import re
from asyncio import sleep

import pendulum
from django.utils import translation
from django.utils.translation import gettext as _
from telegram import ForceReply, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

from bot.commands import cleanup
from bot.models import get_user, my_groups
from games.bgg import get_game, search_game
from games.models import choose_game, create_play, cru_play, group_games, group_players, my_games

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

    # check for game address
    match = re.match(r'^(https?://)?(www\.)?(bgg|boardgamegeek).com/boardgame/(?P<id>\d+)/?([\w-]+)?$', game)
    if match:
        game = match.groupdict().get('id')

    if game.isdigit():
        # lookup game by BGG by ID
        game_data = await get_game(game)
        if game_data:
            new = await add_game_db(update.effective_user, game_data, update.effective_chat)
            caption = _("Game added:") if new else _("Game updated:")
            if game_data.thumbnail:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    parse_mode='Markdown',
                    photo=game_data.thumbnail,
                    caption=caption + f" [{game_data.name}]({game_data.url})"
                )
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    parse_mode='Markdown',
                    text=caption + f" [{game_data.name}]({game_data.url})",
                    disable_web_page_preview=True
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
            if len(games) > 25:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=_(
                        f"Too many results ({len(games)}). Please be more specific.\nTry using BGG ID or paste bgg game addess\n Example: /add https://boardgamegeek.com/boardgame/169786/scythe"),
                    disable_web_page_preview=True,
                )
            else:
                keyboard = []
                for game in games[0:25]:
                    keyboard.append([
                        InlineKeyboardButton(f"{game.name} ({game.year}) - {game.id}",
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
        games = await group_games(update.effective_chat)
        label = _("Games in this group")

    if games:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            disable_web_page_preview=True,
            parse_mode='Markdown',
            text=label + "\n" + "\n".join(
                [f"{game.name} ({game.year}) - [{game.id}]({game.url})" for game
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
            new = await add_game_db(update.effective_user, game_data, update.effective_chat)
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


async def handle_score(update: Update, context: CallbackContext.DEFAULT_TYPE) -> None:
    """ Record game score """
    translation.activate(update.effective_user.language_code)

    user_data = context.user_data.get('play_score')
    score = update.message.text
    if score.isdigit():
        await cru_play(user_data.get('play'), user_data.get('player'), int(score))
        # other users
        players = await group_players(user_data.get('group'), user_data.get('play'))
        keyboard = []
        for player in players:
            score = f" - ({player.score})" if player.score else ""
            keyboard.append([
                InlineKeyboardButton(f"{player.name}{score}",
                                     callback_data={'handler': 'play', 'data': 'player', 'player': player.id,
                                                    'play': user_data.get('play'), 'group': user_data.get('group')})
            ])
        keyboard.append([
            InlineKeyboardButton(_("Done"),
                                 callback_data={'handler': 'play', 'data': 'player', 'player': -1,
                                                'play': user_data.get('play')})
        ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_("Chose another a player or click Done to finish"),
            reply_markup=reply_markup,
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_(f"Invalid score: {score}"),
            reply_markup=ForceReply(selective=True)
        )

    # record score


async def handle_play(update: Update, context: CallbackContext.DEFAULT_TYPE) -> None:
    """ Record game play """
    translation.activate(update.effective_user.language_code)

    if update.callback_query and isinstance(update.callback_query.data, dict):
        data = update.callback_query.data
        if data.get('data') == 'group':
            games = await group_games(data.get('group'))
            if games:
                keyboard = []
                for game in games:
                    keyboard.append([
                        InlineKeyboardButton(f"[{game.id}] {game.name} ({game.year})",
                                             callback_data={'handler': 'play', 'data': 'game', 'game': game.id,
                                                            'group': data.get('group')})
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
                    text=_(f"No games found in this group.\nadd a game first with /add.")
                )
                await sleep(5)
                await message.delete()
        elif data.get('data') == 'game':
            game = data.get('game')
            group = data.get('group')
            players = await group_players(group)
            if players:
                # create play on db
                play_id = await create_play(update.effective_chat, game, update.effective_user)

                keyboard = []
                for player in players:
                    keyboard.append([
                        InlineKeyboardButton(f"{player.name}",
                                             callback_data={'handler': 'play', 'data': 'player', 'player': player.id,
                                                            'play': play_id, 'group': group})
                    ])
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=_("Please choose a player\nmissing players must user /enroll to be added"),
                    reply_markup=reply_markup,
                )
            else:
                message = await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=_(f"No players found in this group.\nPlease use /enroll to add players")
                )
                await sleep(5)
                await message.delete()
        elif data.get('data') == 'player':
            player = data.get('player')
            play = data.get('play')
            group = data.get('group')
            # ask for score

            if player == -1:
                # done
                msg = await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=_("Game recorded"),
                )
                context.user_data.clear()
                await cleanup(10, [msg, update.callback_query.message])
            else:
                player = await get_user(player)
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=_(f"Please write the score of {player.name}"),
                    reply_markup=ForceReply(selective=True)
                )
                context.user_data['play_score'] = {'player': player.id, 'play': play, 'group': group}
            return
        else:
            return

    else:
        # choose group
        groups = await my_groups(update.effective_chat, update.effective_user)
        if not groups:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=_("You are not in any group. Please join one first.\nOr use /enroll from inside a group.")
            )
            return
        else:
            keyboard = []
            for group in groups:
                keyboard.append([
                    InlineKeyboardButton(f"{group[1]}",
                                         callback_data={'handler': 'play', 'data': 'group', 'group': group[0]})
                ])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=_("Please choose a group\nIf you dont't see your group, use /enroll from inside that group."),
                reply_markup=reply_markup,
            )


async def handle_choose(update: Update, context: CallbackContext.DEFAULT_TYPE) -> None:
    """
        Choose a game to play

        Propose a game to the user searching from the list of games added to the group
        then fiter for number of players
        then order for last played

    """
    translation.activate(update.effective_user.language_code)

    if not context.args:

        # TODO: choose n. of players from active poll if exists ?

        message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=_("Please specify number of players after /choose"),
        )
    else:
        try:
            number_of_players = int(context.args[0])

            games = await choose_game(update.effective_chat, update.effective_user, number_of_players)
            if not games:
                message = await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=_("No games found to play, buy more"),
                )
            else:
                gamelist = [
                    _("{} - last play: {} - {}".format(
                        x.name,
                        x.last_played.format('DD/MM/YY') if x.last_played > pendulum.datetime(1980, 1, 1) else _(
                            "Never"),
                        " ".join(x.last_users)
                    )) for x in games]

                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=_("Games for {} players:\n\n{}".format(number_of_players, "\n".join(gamelist))),

                )

        except ValueError:
            message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=_("Invalid number of players"),
            )
            return
