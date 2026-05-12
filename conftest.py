"""Pytest configuration when running tests from the repo root.

Adds the Django backend to ``sys.path`` so ``core.settings`` is importable
and points ``DJANGO_SETTINGS_MODULE`` at it. pytest-django takes care of
``django.setup()`` and test-database creation — do NOT call ``migrate``
here, it fights pytest-django's database blocker and breaks collection.
"""

import os
import sys

import django

BASE_DIR = os.path.dirname(__file__)
BACKEND_DIR = os.path.join(BASE_DIR, "bionexus-platform", "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

# When pytest is invoked from the repo root, pytest-django does not pick
# up the backend's pytest.ini, so we initialize Django ourselves. The
# test database is still created by pytest-django at test time — do NOT
# call ``migrate`` here, it races the django_db blocker.
django.setup()
