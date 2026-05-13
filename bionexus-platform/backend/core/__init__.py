# Expose the Celery app under the project namespace so ``celery -A core``
# can find it. ``shared_task`` decorators in each module's ``tasks.py``
# bind to this app via Celery's default-app lookup.
from .celery import app as celery_app

__all__ = ["celery_app"]
