from __future__ import annotations

import logging
import pendulum
import telegram
from django.db import models
# Create your models here.
from django.db.models import QuerySet
from django.utils.text import slugify
from munch import Munch, munchify
from pendulum import DateTime
from typing import Optional

from bot.models import Chat, User, cru_chat, cru_user
from gamebot.decorators import database_sync_to_async

logger = logging.getLogger(f'gamebot.{__name__}')


class Game(models.Model):
    """
    Game model to keep a cache of bgg games
    """
    id = models.BigIntegerField(primary_key=True)  # Board Games Geek ID
    name = models.CharField(max_length=255)
    thumbnail = models.CharField(max_length=255, null=True, blank=True)
    type = models.CharField(max_length=255)
    playingtime = models.IntegerField(default=0)
    suggested_players = models.CharField(max_length=5, default='')
    min_players = models.IntegerField(default=1)
    max_players = models.IntegerField(default=1)
    year = models.IntegerField(null=True, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    @property
    def url(self):
        return f"https://boardgamegeek.com/{self.type}/{self.id}/{slugify(self.name)}"

    def last_played_from_users(self, users: QuerySet) -> [DateTime, list]:
        """
        Return the last played date from a group of users
        """
        last_played = PlayScore.objects.filter(play__game=self, user__in=users).order_by('-play__played_date').first()
        if last_played:
            return pendulum.instance(last_played.play.played_date), last_played.play.users
        return pendulum.datetime(1970, 1, 1), []

    def __str__(self):
        return self.name


class Play(models.Model):
    """
    Play model to keep games played by a group
    """
    chat = models.ForeignKey('bot.Chat', on_delete=models.SET_NULL, null=True, blank=True)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    recorded_by = models.ForeignKey('bot.User', on_delete=models.SET_NULL, null=True, blank=True)
    played_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    @property
    def users(self):
        return [x.user for x in self.playscore_set.all()]


class PlayScore(models.Model):
    """
    PlayScore model to keep scores of a played game
    """
    play = models.ForeignKey(Play, on_delete=models.CASCADE)
    user = models.ForeignKey('bot.User', on_delete=models.CASCADE)
    score = models.IntegerField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)


class UserGame(models.Model):
    """
    UserGame model to keep games owned by a user
    """
    user = models.ForeignKey('bot.User', on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    last_updated = models.DateTimeField(auto_now=True)


@database_sync_to_async
def my_games(user_id: int) -> list:
    """
    Return a list of games owned by a user
    """
    games = UserGame.objects.filter(user_id=user_id)
    return [munchify({
        'name': game.game.name,
        'id': game.game.id,
        'year': game.game.year,
        'url': game.game.url,
    }) for game in games]


@database_sync_to_async
def group_games(chat: telegram.Chat | int) -> list:
    """
    Return a list of games owned by users in group
    """
    if isinstance(chat, int):
        c = Chat.objects.get(id=chat)
    else:
        c, created = cru_chat(chat)

    if isinstance(c, Chat):
        games = UserGame.objects.filter(user__in=c.members.all()).distinct()
        return [munchify({
            'name': game.game.name,
            'id': game.game.id,
            'year': game.game.year,
            'url': game.game.url,
        }) for game in games]
    return []


@database_sync_to_async
def group_players(chat: telegram.Chat | int, play_id: int = None) -> list:
    """
    Return a list of games owned by users in group
    """
    if isinstance(chat, int):
        c = Chat.objects.get(id=chat)
    else:
        c, created = cru_chat(chat)

    players = c.members.all()

    if play_id:
        # exclude players who have been recorded in this play
        play = Play.objects.get(id=play_id)

    return [munchify({
        'name': player.name if player.name else player.username if player.username else player.id,
        'id': player.id,
        'score': play.playscore_set.filter(user=player).first().score if play.playscore_set.filter(user=player).first() and play_id else None,
    }) for player in players]


@database_sync_to_async
def add_game(user: telegram.User, game_data: Munch, chat: telegram.Chat = None) -> bool:
    """
    Add a game to the user's list of games
    """
    logger.info(f'Adding game {game_data.name} to user {user.id}')
    game = update_game(game_data)

    u, user_created = cru_user(user)
    user_game, new = UserGame.objects.get_or_create(user=u, game=game)

    if chat:
        c, created = cru_chat(chat)
        c.members.add(u)
        c.save()

    return new


@database_sync_to_async
def remove_game(user: telegram.User, game_data: Munch) -> bool:
    """
    Remove a game to the user's list of games
    """
    logger.info(f'Removing game {game_data.name} from user {user.id}')
    game = update_game(game_data)
    user, user_created = cru_user(user)

    UserGame.objects.filter(user=user, game=game).delete()

    return True


def update_game(game_data):
    game, created = Game.objects.get_or_create(id=game_data.id)
    game.name = game_data.name
    game.thumbnail = game_data.thumbnail
    game.playingtime = game_data.playingtime
    game.rating = game_data.rating
    game.type = game_data.type
    game.suggested_players = game_data.suggested_players
    game.min_players = game_data.minplayers
    game.max_players = game_data.maxplayers
    game.year = game_data.year
    game.save()
    return game


@database_sync_to_async
def cru_play(play_id: int, user_id: int, score: int) -> bool:
    """
    Create or update a play
    """
    logger.info(f'Updating score for  play {play_id} user {user_id} score {score}')
    user = User.objects.get(id=user_id)
    play = Play.objects.get(id=play_id)
    play_score, new = PlayScore.objects.get_or_create(play=play, user=user)
    play_score.score = score
    play_score.save()

    return True


@database_sync_to_async
def create_play(chat: telegram.Chat, game_id: int, user: telegram.User) -> int:
    """
        Create  a play
    """
    logger.info(f'Creating a play for  {chat.id} game {game_id}')
    chat, created = cru_chat(chat)
    user, created = cru_user(user)
    game = Game.objects.get(id=game_id)
    play = Play(chat=chat, game=game, recorded_by=user)
    play.save()
    return play.id


@database_sync_to_async
def choose_game(chat: telegram.Chat, player: telegram.User, players: int) -> Optional[list]:
    """
    Propose a game to the user searching from the list of games added to the group
    then fiter for number of players
    then order for last played
    """
    logger.info(f'Choosing game for chat {chat.id} player {player.id} players {players}')
    users = Chat.objects.get(id=chat.id).members.all()
    games = [x.game for x in UserGame.objects.filter(user__in=users)]
    games = [game for game in games if game.min_players <= players <= game.max_players]
    games = sorted(games, key=lambda x: x.last_played_from_users(users)[0], reverse=True)
    if games:
        return [munchify({
            'name': game.name,
            'id': game.id,
            'year': game.year,
            'url': game.url,
            'last_played': game.last_played_from_users(users)[0],
            'last_users': [f"@{x.username}" for x in game.last_played_from_users(users)[1]],
        }) for game in games]
    return None
