from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns
from assessments import views

urlpatterns = patterns('',
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/items/?$',
        views.ItemsList.as_view()),
    url(r'^banks/(?P<bank_id>[-.:@%\d\w]+)/?$',
        views.AssessmentBanksDetail.as_view()),
    url(r'^banks/?$',
        views.AssessmentBanksList.as_view()),
    url(r'^items/(?P<item_id>[-.:@%\d\w]+)/?$',
        views.ItemDetails.as_view()),
    url(r'^items/?$',
        views.ItemsList.as_view()),
)

urlpatterns = format_suffix_patterns(urlpatterns)