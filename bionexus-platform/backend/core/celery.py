"""Celery application instance.

The app picks up its config from Django settings via the ``CELERY_``
prefix (``CELERY_BROKER_URL``, ``CELERY_TASK_ALWAYS_EAGER``, ...).

Tasks live in each module's ``tasks.py`` and are auto-discovered when
the worker starts via ``app.autodiscover_tasks()``.

Run a production worker ::

    celery -A core worker --loglevel=info

And the periodic-task scheduler (beat) ::

    celery -A core beat --loglevel=info

In dev and tests, ``CELERY_TASK_ALWAYS_EAGER=true`` (the default) makes
``Task.delay(...)`` run synchronously in the calling thread, which keeps
tests deterministic and removes the need for a Redis broker.
"""

from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

app = Celery("labionexus")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
