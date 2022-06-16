import telegram
from django.db import models
# Create your models here.
from django.utils.text import slugify
from munch import Munch, munchify

from bot.models import Chat, cru_chat, cru_user
from gamebot.decorators import database_sync_to_async


class Game(models.Model):
    """
    Game model to keep a cache of bgg games
    """
    id = models.BigIntegerField(primary_key=True)  # Board Games Geek ID
    name = models.CharField(max_length=255)
    thumbnail = models.CharField(max_length=255)
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

    def __str__(self):
        return self.name


class Play(models.Model):
    """
    Play model to keep games played by a group
    """
    chat = models.ForeignKey('bot.Chat', on_delete=models.SET_NULL, null=True, blank=True)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    played_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class PlayScore(models.Model):
    """
    PlayScore model to keep scores of a played game
    """
    play = models.ForeignKey(Play, on_delete=models.CASCADE)
    user = models.ForeignKey('bot.User', on_delete=models.CASCADE)
    score = models.IntegerField()
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
def group_games(chat_id: int) -> list:
    """
    Return a list of games owned by users in group
    """
    games = UserGame.objects.filter(user__in=Chat.objects.get(id=chat_id).members.all()).distinct()
    return [munchify({
        'name': game.game.name,
        'id': game.game.id,
        'year': game.game.year,
        'url': game.game.url,
    }) for game in games]


@database_sync_to_async
def add_game(user: telegram.User, game_data: Munch, chat: telegram.Chat = None) -> bool:
    """
    Add a game to the user's list of games
    """
    game = update_game(game_data)

    user, user_created = cru_user(user)
    user_game, new = UserGame.objects.get_or_create(user=user, game=game)

    if chat:
        c, created = cru_chat(chat)
        c.members.add(user)
        c.save()

    return new


@database_sync_to_async
def remove_game(user: telegram.User, game_data: Munch) -> bool:
    """
    Remove a game to the user's list of games
    """
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
