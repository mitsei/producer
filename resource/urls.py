from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns
from resource import views

urlpatterns = patterns('',
    url(r'^$',
        views.ResourceService.as_view()),
    url(r'^bins/?$',
        views.BinsList.as_view()),
    url(r'^bins/(?P<bin_id>[-.:@%\d\w]+)/?$',
        views.BinDetails.as_view()),
    url(r'^bins/(?P<bin_id>[-.:@%\d\w]+)/resources/?$',
        views.BinResourcesList.as_view()),
    url(r'^bins/(?P<bin_id>[-.:@%\d\w]+)/resources/(?P<resource_id>[-.:@%\d\w]+)/?$',
        views.BinResourceDetails.as_view()),
    url(r'^docs/?$',
        views.Documentation.as_view()),
)

urlpatterns = format_suffix_patterns(urlpatterns)