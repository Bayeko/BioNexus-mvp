import os
import sys
import django
from django.core.management import call_command

BASE_DIR = os.path.dirname(__file__)
BACKEND_DIR = os.path.join(BASE_DIR, 'bionexus-platform', 'backend')
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

django.setup()
call_command('migrate', run_syncdb=True, verbosity=0)
