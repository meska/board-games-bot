from django.db import models

from boardgamesbot.decorators import database_sync_to_async


class Poll(models.Model):
    message_id = models.BigIntegerField()
    chat_id = models.BigIntegerField()
    pinned = models.BooleanField(default=False)
    question = models.CharField(max_length=200)
    answers = models.JSONField(default=dict)
    pub_date = models.DateTimeField('date published', auto_now_add=True)

    class Meta:
        unique_together = ('message_id', 'chat_id')

    def __str__(self):
        return self.question


@database_sync_to_async
def new_poll(message_id, chat_id, question, answers):
    db_poll = Poll(
        message_id=message_id, chat_id=chat_id, question=question, answers=answers,
        pinned=True)
    return db_poll.save()
