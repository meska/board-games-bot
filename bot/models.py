import logging
from typing import Optional

import telegram
from django.db import models
from munch import munchify

from gamebot.decorators import database_sync_to_async

logger = logging.getLogger(f'gamebot.{__name__}')


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


def cru_chat(chat: telegram.Chat) -> [Chat, bool]:
    logger.info('cru_chat: %s', chat.id)
    c, chat_created = Chat.objects.get_or_create(id=chat.id)
    if chat.title:
        c.title = chat.title
        c.save()
    if chat.type.name == 'PRIVATE' and not c.title:
        u = User.objects.get(id=chat.id)
        c.title = chat.type.title()
        c.members.add(u)
        c.save()
    return c, chat_created


def cru_user(user: telegram.User) -> [User, bool]:
    logger.info('cru_user: %s', user.id)
    u, user_created = User.objects.get_or_create(id=user.id)
    if user.username or user.first_name:
        u.username = user.username
        u.name = user.first_name
        u.save()
    return u, user_created


@database_sync_to_async
def new_chat_user(chat: telegram.Chat, user: telegram.User) -> bool:
    logger.info('new_chat_user: %s', chat.id)
    u, user_created = cru_user(user)
    c, created = cru_chat(chat)

    c.members.add(u)
    c.save()

    return user_created


@database_sync_to_async
def left_chat_user(chat: telegram.Chat, user: telegram.User) -> bool:
    logger.info('left_chat_user: %s', chat.id)
    c, chat_created = cru_chat(chat)
    u, user_created = cru_user(user)

    c.members.remove(u)
    c.save()

    return True


@database_sync_to_async
def forget_user(user: telegram.User) -> bool:
    logger.info('forget: %s', user.id)
    User.objects.filter(id=user.id).delete()  # delete users and their games too
    Chat.objects.filter(id=user.id).delete()  # delete private chats
    return True


@database_sync_to_async
def my_groups(chat: telegram.Chat, user: telegram.User) -> list:
    u, user_created = cru_user(user)
    cru_chat(chat)

    return list(Chat.objects.filter(members=u).values_list('id', 'title'))


@database_sync_to_async
def get_user(user_id: int) -> Optional[dict]:
    u, user_created = User.objects.get_or_create(id=user_id)
    return munchify({
        'id': u.id,
        'name': u.name if u.name else u.username if u.username else str(u.id),
    })
