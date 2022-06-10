"""
    Scheduled jobs definition
"""

jobs = [{

    'job': 'polls.tasks.sync_polls',
    'interval': 60 * 10,
    'scheduled': False
}]
