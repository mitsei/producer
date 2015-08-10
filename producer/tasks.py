"""
Celery tasks for import module.
"""
from __future__ import unicode_literals

from producer.celery import app
from utilities.general import upload_class


@app.task
def import_file(path, repo, user):
    """Asynchronously import a course."""
    import_course_from_file(path, repo, user)

