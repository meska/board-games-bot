from django_rq import job


@job
def update_weekly_poll(poll_id):
    from polls.models import WeeklyPoll
    wp = WeeklyPoll.objects.get(id=poll_id)
    print(wp)


@job
def sync_polls():
    """
    Syncronize polls on channels
    :return:
    :rtype:
    """
    print('Updating weekly poll...')
    from polls.models import WeeklyPoll
    for wp in WeeklyPoll.objects.all():
        update_weekly_poll.delay(wp.id)
