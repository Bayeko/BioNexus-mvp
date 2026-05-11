import os
import django
from django.core.management import call_command

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

django.setup()
call_command("migrate", run_syncdb=True, verbosity=0)
