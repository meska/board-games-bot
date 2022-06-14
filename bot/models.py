import telegram
from django.db import models

from boardgamesbot.decorators import database_sync_to_async


class Chat(models.Model):
    """
    Keep a list of groups
    """
    chat_id = models.BigIntegerField()
    chat_title = models.CharField(max_length=255)
    last_updated = models.DateTimeField(auto_now=True)


class GroupMember(models.Model):
    """
    Keep a list of users in group
    """
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    user_id = models.IntegerField()
    user_name = models.CharField(max_length=255)
    is_admin = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now=True)


@database_sync_to_async
def new_chat_user(chat: telegram.Chat, user: telegram.User, is_admin: bool = False) -> bool:
    c, created = Chat.objects.get_or_create(chat_id=chat.id, chat_title=chat.title)
    gm, created = GroupMember.objects.get_or_create(chat=c, user_id=user.id)
    gm.user_name = user.first_name
    gm.is_admin = is_admin
    gm.save()
    return created


@database_sync_to_async
def left_chat_user(chat: telegram.Chat, user: telegram.User) -> bool:
    c, created = Chat.objects.get_or_create(chat_id=chat.id, chat_title=chat.title)
    GroupMember.objects.filter(chat=c, user_id=user.id).delete()
    return True
