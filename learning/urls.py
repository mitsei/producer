from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns
from grading import views

urlpatterns = patterns('',
    url(r'^$',
        views.GradingService.as_view()),
    url(r'^gradebooks/?$',
        views.GradebooksList.as_view()),
    url(r'^gradebooks/(?P<gradebook_id>[-.:@%\d\w]+)/?$',
        views.GradebookDetails.as_view()),
    url(r'^gradebooks/(?P<gradebook_id>[-.:@%\d\w]+)/gradesystems/?$',
        views.GradebookGradeSystemsList.as_view()),
    url(r'^gradebooks/(?P<gradebook_id>[-.:@%\d\w]+)/gradesystems/(?P<gradesystem_id>[-.:@%\d\w]+)/?$',
        views.GradebookGradeSystemDetails.as_view()),
    url(r'^gradebooks/(?P<gradebook_id>[-.:@%\d\w]+)/columns/?$',
        views.GradebookColumnsList.as_view()),
    url(r'^gradebooks/(?P<gradebook_id>[-.:@%\d\w]+)/columns/(?P<column_id>[-.:@%\d\w]+)/?$',
        views.GradebookColumnDetails.as_view()),
    url(r'^gradebooks/(?P<gradebook_id>[-.:@%\d\w]+)/columns/(?P<column_id>[-.:@%\d\w]+)/entries/?$',
        views.GradeEntriesList.as_view()),
    url(r'^gradebooks/(?P<gradebook_id>[-.:@%\d\w]+)/columns/(?P<column_id>[-.:@%\d\w]+)/summary/?$',
        views.GradebookColumnSummary.as_view()),
    url(r'^gradebooks/(?P<gradebook_id>[-.:@%\d\w]+)/entries/?$',
        views.GradeEntriesList.as_view()),
    url(r'^gradebooks/(?P<gradebook_id>[-.:@%\d\w]+)/entries/(?P<entry_id>[-.:@%\d\w]+)/?$',
        views.GradeEntryDetails.as_view()),
    url(r'^docs/?$',
        views.Documentation.as_view()),
)

urlpatterns = format_suffix_patterns(urlpatterns)