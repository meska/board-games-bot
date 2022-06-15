from django.contrib.postgres.fields import ArrayField
from django.db import models
# Create your models here.
from django.utils.text import slugify
from munch import Munch, munchify

from boardgamesbot.decorators import database_sync_to_async


class Game(models.Model):
    """
    Game model to keep a cache of bgg games
    """
    bgg_id = models.BigIntegerField(unique=True, db_index=True)  # Board Games Geek ID
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
        return f"https://boardgamegeek.com/{self.type}/{self.bgg_id}/{slugify(self.name)}"

    def __str__(self):
        return self.name


class GroupGame(models.Model):
    """
    ChatGame model to keep games owned by a group
    """
    chat_id = models.BigIntegerField(db_index=True)
    game = models.ForeignKey(Game, on_delete=models.CASCADE, db_index=True)
    owned_by = ArrayField(models.BigIntegerField(), default=list)  # Users who own the game
    in_place = models.BooleanField(
        default=False)  # True if the game stays always in the room, false if the owner keep it with him
    last_updated = models.DateTimeField(auto_now=True)


class Play(models.Model):
    """
    Play model to keep games played by a group
    """
    chat_id = models.BigIntegerField(db_index=True)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    played_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class PlayScore(models.Model):
    """
    PlayScore model to keep scores of a played game
    """
    play = models.ForeignKey(Play, on_delete=models.CASCADE)
    user_id = models.BigIntegerField()
    user_name = models.CharField(max_length=255)
    score = models.IntegerField()
    last_updated = models.DateTimeField(auto_now=True)


class UserGame(models.Model):
    """
    UserGame model to keep games owned by a user
    """
    user_id = models.BigIntegerField(db_index=True)
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
        'bgg_id': game.game.bgg_id,
        'year': game.game.year,
        'url': game.game.url,
    }) for game in games]


@database_sync_to_async
def group_games(chat_id: int) -> list:
    """
    Return a list of games owned by users in group
    """
    from bot.models import GroupMember
    members = list(GroupMember.objects.filter(chat__chat_id=chat_id).values_list('user_id', flat=True))
    games = UserGame.objects.filter(user_id__in=members).distinct()
    return [munchify({
        'name': game.game.name,
        'bgg_id': game.game.bgg_id,
        'year': game.game.year,
        'url': game.game.url,
    }) for game in games]


@database_sync_to_async
def add_game(user_id: int, game_data: Munch, chat_id: int = None) -> bool:
    """
    Add a game to the user's list of games
    """
    game = update_game(game_data)

    user_game, new = UserGame.objects.get_or_create(user_id=user_id, game=game)

    if chat_id:
        group_game, created = GroupGame.objects.get_or_create(chat_id=chat_id, game=game)
        if user_id not in group_game.owned_by:
            group_game.owned_by.append(user_id)
            group_game.save()

    return new


@database_sync_to_async
def remove_game(user_id: int, game_data: Munch, chat_id: int = None) -> bool:
    """
    Remove a game to the user's list of games
    """
    game = update_game(game_data)

    UserGame.objects.filter(user_id=user_id, game=game).delete()
    for groupgame in GroupGame.objects.filter(game=game, owned_by__contains=[user_id]):
        groupgame.owned_by.remove(user_id)
        groupgame.save()

    return True


def update_game(game_data):
    game, created = Game.objects.get_or_create(bgg_id=game_data.id)
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
