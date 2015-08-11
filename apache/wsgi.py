ALLDIRS = ['/usr/local/pythonenv/producer/lib/python2.6/site-packages']

import os
import sys
import site

# from https://code.google.com/p/modwsgi/wiki/VirtualEnvironments

sys.path.insert(0, '/var/www/producer/producer_main/')
sys.path.insert(1, '/var/www/producer/')

prev_sys_path = list(sys.path)
for directory in ALLDIRS:
    site.addsitedir(directory)

new_sys_path = []
for item in list(sys.path):
    if item not in prev_sys_path:
        new_sys_path.append(item)
        sys.path.remove(item)

sys.path[:0] = new_sys_path

os.environ['DJANGO_SETTINGS_MODULE'] = 'producer_main.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
