"""Management command to sync pending WAL records to the server.

Usage:
    python manage.py sync_pending          # continuous loop
    python manage.py sync_pending --once   # single pass
"""

from django.core.management.base import BaseCommand

from modules.persistence.sync_engine import SyncEngine


class Command(BaseCommand):
    help = "Sync pending WAL records to the server (run continuously or once)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="Run a single sync pass instead of a continuous loop.",
        )

    def handle(self, *args, **options):
        engine = SyncEngine()

        if options["once"]:
            stats = engine.run_once()
            self.stdout.write(
                f"Sync pass complete: "
                f"{stats['synced']} synced, "
                f"{stats['failed']} failed, "
                f"{stats['skipped']} skipped"
            )
        else:
            self.stdout.write("Starting continuous sync loop (Ctrl+C to stop)...")
            engine.run_loop()
            self.stdout.write("Sync loop stopped.")
