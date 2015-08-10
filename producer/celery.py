"""
As described in
http://celery.readthedocs.org/en/latest/django/first-steps-with-django.html
"""
from __future__ import absolute_import

import os
import logging

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'producer.settings')

from django.conf import settings

log = logging.getLogger(__name__)

app = Celery('producer')  # pylint: disable=invalid-name

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)  # pragma: no cover

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))