from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns
from learning import views

urlpatterns = patterns('',
    url(r'^objectivebanks/?$',
        views.ObjectiveBanksList.as_view()),
    url(r'^objectivebanks/(?P<objectivebank_id>[-.:@%\d\w]+)/?$',
        views.ObjectiveBankDetails.as_view()),
    url(r'^objectivebanks/(?P<objectivebank_id>[-.:@%\d\w]+)/objectives/?$',
        views.ObjectivesList.as_view()),
    url(r'^objectivebanks/(?P<objectivebank_id>[-.:@%\d\w]+)/activities/?$',
        views.ActivitiesList.as_view()),
    url(r'^objectivebanks/(?P<objectivebank_id>[-.:@%\d\w]+)/assets/?$',
        views.AssetsList.as_view()),
    url(r'^objectives/?$',
        views.ObjectivesList.as_view()),
    url(r'^objectives/(?P<objective_id>[-.:@%\d\w]+)/?$',
        views.ObjectiveDetails.as_view()),
    url(r'^activities/?$',
        views.ActivitiesList.as_view()),
    url(r'^activities/(?P<activity_id>[-.:@%\d\w]+)/?$',
        views.ActivityDetails.as_view()),
    url(r'^assets/?$',
        views.AssetsList.as_view()),
    url(r'^assets/(?P<asset_id>[-.:@%\d\w]+)/?$',
        views.AssetDetails.as_view()),
)

urlpatterns = format_suffix_patterns(urlpatterns)