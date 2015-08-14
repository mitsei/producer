"""
Celery tasks for import module.
"""
from __future__ import unicode_literals

from producer_main.celery import app
from utilities.general import upload_class


@app.task
def import_file(path, repo, user):
    """Asynchronously import a course."""
    try:
        upload_class(path, repo, user)
    except Exception as ex:
        import traceback, logging
        logging.info(traceback.format_exc())

