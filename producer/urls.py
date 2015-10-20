from django.conf.urls import patterns, url, include
from rest_framework.urlpatterns import format_suffix_patterns

urlpatterns = patterns('',
    url(r'^assessment/?', include('assessments.urls', namespace='assessments')),
    url(r'^grading/?', include('grading.urls', namespace='grading')),
    url(r'^learning/?', include('learning.urls', namespace='learning')),
    url(r'^repository/?', include('repository.urls', namespace='repository')),
)
