from django.contrib.postgres.fields import ArrayField
from django.db import models

# Create your models here.
from boardgamesbot.decorators import database_sync_to_async


class Game(models.Model):
    """
    Game model to keep a cache of bgg games
    """
    bgg_id = models.IntegerField(unique=True)  # Board Games Geek ID
    name = models.CharField(max_length=255)
    thumbnail = models.CharField(max_length=255)
    min_players = models.IntegerField(default=1)
    max_players = models.IntegerField(default=1)
    year = models.IntegerField(null=True, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class GroupGame(models.Model):
    """
    ChatGame model to keep games owned by a group
    """
    chat_id = models.BigIntegerField()
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    owned_by = ArrayField(models.IntegerField(), default=list)  # Users who own the game
    in_place = models.BooleanField(
        default=False)  # True if the game stays always in the room, false if the owner keep it with him
    last_updated = models.DateTimeField(auto_now=True)


class Play(models.Model):
    """
    Play model to keep games played by a group
    """
    chat_id = models.BigIntegerField()
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    played_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)


class PlayScore(models.Model):
    """
    PlayScore model to keep scores of a played game
    """
    play = models.ForeignKey(Play, on_delete=models.CASCADE)
    user_id = models.IntegerField()
    user_name = models.CharField(max_length=255)
    score = models.IntegerField()
    last_updated = models.DateTimeField(auto_now=True)


class UserGame(models.Model):
    """
    UserGame model to keep games owned by a user
    """
    user_id = models.BigIntegerField()
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    last_updated = models.DateTimeField(auto_now=True)


@database_sync_to_async
def my_games(user_id: int) -> list:
    """
    Return a list of groups the user is in
    """
    return list(UserGame.objects.filter(user_id=user_id).values_list('game_id', 'game__name'))
