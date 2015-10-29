"""
Celery tasks for import module.
"""
from __future__ import unicode_literals

import os
import shutil

from celery import Task
from django.core.files.storage import default_storage
from django.conf import settings

from dlkit_django.proxy_example import TestRequest

from producer.receivers import RabbitMQReceiver
from producer_main.celery_app import app
from utilities.general import upload_class


class ErrorHandlingTask(Task):
    abstract = True

    def on_failure(self, exc, task_id, targs, tkwargs, einfo):
        """
        :param exc:
        :param task_id:
        :param args: path, domain_repo, user (args to import_file)
        :param kwargs:
        :param einfo: Traceback (str(einfo))
        :return:
        """
        if not settings.TEST:
            test_request = TestRequest(username=targs[2].username)
            rabbit = RabbitMQReceiver(request=test_request)
            msg = 'Import of {0} raised exception: {1!r}'.format(targs[0].split('/')[-1],
                                                                 str(exc))
            rabbit._pub_wrapper('new',
                                obj_type='repositories',
                                id_list=[msg],
                                status='error')
        default_storage.delete(targs[0])
        extracted_path = targs[0].replace('.zip', '').replace('.tar.gz', '')
        if os.path.isdir(extracted_path):
            shutil.rmtree(extracted_path)


    def on_success(self, retval, task_id, targs, tkwargs):
        """

        :param retval:
        :param task_id:
        :param targs:
        :param tkwargs:
        :return:
        """
        if not settings.TEST:
            test_request = TestRequest(username=targs[2].username)
            rabbit = RabbitMQReceiver(request=test_request)
            rabbit._pub_wrapper('new',
                                obj_type='repositories',
                                id_list=["Upload successful. You may now view your course."],
                                status='success')
        default_storage.delete(targs[0])
        extracted_path = targs[0].replace('.zip', '').replace('.tar.gz', '')
        if os.path.isdir(extracted_path):
            shutil.rmtree(extracted_path)


@app.task(base=ErrorHandlingTask)
def import_file(path, repo, user):
    """Asynchronously import a course."""
    upload_class(path, repo, user)


