import zipfile
import cStringIO

from django.conf import settings
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import Http404, HttpResponse
from rest_framework.renderers import JSONRenderer, BrowsableAPIRenderer
from rest_framework.permissions import AllowAny

from dlkit_django.errors import *

from bs4 import BeautifulSoup

from utilities import assessment as autils
from utilities import general as gutils

# https://stackoverflow.com/questions/20424521/override-jsonserializer-on-django-rest-framework/20426493#20426493
class DLJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        data = gutils.clean_up_dl_objects(data)
        return super(DLJSONRenderer, self).render(data,
                                                  accepted_media_type,
                                                  renderer_context)


class ProducerAPIViews(gutils.DLKitSessionsManager):
    """Set up the managers"""
    def initial(self, request, *args, **kwargs):
        """set up the managers"""
        super(ProducerAPIViews, self).initial(request, *args, **kwargs)
        gutils.activate_managers(request)
        self._managers = ['am', 'cm', 'gm', 'lm', 'rm']
        for manager in self._managers:
            setattr(self, manager, gutils.get_session_data(request, manager))

    def finalize_response(self, request, response, *args, **kwargs):
        """save the updated managers"""
        try:
            for manager in self._managers:
                gutils.set_session_data(request, manager, getattr(self, manager))
        except AttributeError:
            pass  # with an exception, the RM may not be set
        return super(ProducerAPIViews, self).finalize_response(request,
                                                               response,
                                                               *args,
                                                               **kwargs)

