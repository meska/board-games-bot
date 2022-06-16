from django_rq import job


@job
def new_chat_user_task(chat_id: int, user_id: int, user_name: str) -> bool:
    from bot.models import Chat, User
    chat, created = Chat.objects.get_or_create(id=chat_id)
    user, created = User.objects.get_or_create(id=user_id)
    chat.members.add(user)
    chat.save()
    return created
