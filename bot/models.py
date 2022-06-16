import telegram
from django.db import models

from gamebot.decorators import database_sync_to_async


class Chat(models.Model):
    """
    Keep a list of groups
    """
    id = models.BigIntegerField(primary_key=True)
    title = models.CharField(max_length=255)
    members = models.ManyToManyField('bot.User', blank=True)
    last_updated = models.DateTimeField(auto_now=True)


class User(models.Model):
    id = models.BigIntegerField(primary_key=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)


def cru_chat(chat):
    c, chat_created = Chat.objects.get_or_create(id=chat.id)
    c.title = chat.title
    return c


def cru_user(user):
    u, user_created = User.objects.get_or_create(id=user.id)
    u.username = user.username
    u.name = user.first_name
    u.save()
    return u, user_created


@database_sync_to_async
def new_chat_user(chat: telegram.Chat, user: telegram.User, is_admin: bool = False) -> bool:
    u, user_created = cru_user(user)
    c, created = cru_chat(chat)

    c.members.add(u)
    c.save()

    return user_created


@database_sync_to_async
def left_chat_user(chat: telegram.Chat, user: telegram.User) -> bool:
    c, chat_created = cru_chat(chat)
    u, user_created = cru_user(user)

    c.members.remove(u)
    c.save()

    return True
