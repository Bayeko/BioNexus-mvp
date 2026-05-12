"""Pytest configuration for the backend Django project.

pytest-django (via pytest.ini's DJANGO_SETTINGS_MODULE) handles
``django.setup()`` and test-database creation automatically. Calling
``migrate`` at conftest import time triggered pytest-django's database
blocker (which is installed *before* conftests load) and made the whole
suite fail to collect.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
