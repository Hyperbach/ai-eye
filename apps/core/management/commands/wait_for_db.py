import time

from django.core.management.base import BaseCommand
from django.db import connection
from django.db.utils import OperationalError
from django.utils.translation import ngettext


class Command(BaseCommand):
    help = "Checks database connection"

    def add_arguments(self, parser):
        parser.add_argument(
            "--seconds",
            nargs="?",
            type=int,
            help="Number of seconds to wait before retrying",
            default=1,
        )

    def handle(self, *args, **options):
        self.stdout.write("Waiting for database...")

        wait = options["seconds"]
        while True:
            try:
                connection.ensure_connection()
                break
            except OperationalError:
                plural_time = ngettext("second", "seconds", wait)
                self.stdout.write(
                    self.style.WARNING(
                        f"Database unavailable, retrying after {wait} {plural_time}!"
                    )
                )
                time.sleep(wait)

        self.stdout.write(self.style.SUCCESS("Database available!"))
