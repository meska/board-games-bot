from django_rq import job


@job
def sync_polls():
    """
    Syncronize polls on channels
    :return:
    :rtype:
    """
    print('Updating polls...')
