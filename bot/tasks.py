from django_rq import job


@job
def new_chat_user_task(chat_id: int, user_id: int, user_name: str) -> bool:
    from bot.models import Chat
    from bot.models import GroupMember
    chat, created = Chat.objects.get_or_create(chat_id=chat_id)
    gm, created = GroupMember.objects.get_or_create(chat=chat, user_id=user_id)
    gm.user_name = user_name
    gm.save()
    return created
