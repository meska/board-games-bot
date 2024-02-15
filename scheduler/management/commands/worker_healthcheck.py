from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    """
    Healtcheck Worker
    """

    help = __doc__
    args = "<queue>"
    se = None

    def add_arguments(self, parser):
        parser.add_argument(
            "--queue",
            dest="queue",
            default="cron",
            help="Name of the queue to check",
        )

    def handle(self, *args, **options):
        queue = options["queue"]
        from django.core.cache import cache
        hb = cache.get(f"healthcheck_{queue}")
        if hb:
            if timezone.now() - hb > timedelta(minutes=60):
                print(f"Healthcheck {queue} is too old: {hb}")
                # invio messaggio a sentry
                from sentry_sdk import capture_message
                from sentry_sdk import push_scope

                with push_scope() as scope:
                    scope.set_extra("queue", queue)
                    scope.set_extra("last_hearthbeat", hb)
                    scope.set_tag("queue", queue)
                    capture_message(
                        f"Healthcheck Failed {queue}", level="warning", scope=scope
                    )
                exit(1)
            else:
                print(f"Healthcheck {queue} is ok: {hb}")
                exit(0)
        else:
            print(f"Healthcheck {queue} not found")
            exit(1)
