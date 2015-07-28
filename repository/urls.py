from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns
from repository import views

urlpatterns = patterns('',
    url(r'^$',
        views.RepositoryService.as_view()),
    url(r'^repositories/?$',
        views.RepositoriesList.as_view()),
    url(r'^repositories/(?P<repository_id>[-.:@%\d\w]+)/?$',
        views.RepositoryDetails.as_view()),
    url(r'^repositories/(?P<repository_id>[-.:@%\d\w]+)/assets/?$',
        views.RepositoryAssetsList.as_view()),
    url(r'^repositories/(?P<repository_id>[-.:@%\d\w]+)/assets/(?P<asset_id>[-.:@%\d\w]+)/?$',
        views.RepositoryAssetDetails.as_view()),
    url(r'^repositories/(?P<repository_id>[-.:@%\d\w]+)/compositions/?$',
        views.RepositoryCompositionsList.as_view()),
    url(r'^repositories/(?P<repository_id>[-.:@%\d\w]+)/compositions/(?P<composition_id>[-.:@%\d\w]+)/?$',
        views.RepositoryCompositionDetails.as_view()),
    url(r'^repositories/(?P<repository_id>[-.:@%\d\w]+)/compositions/(?P<composition_id>[-.:@%\d\w]+)/assets/?$',
        views.RepositoryCompositionAssetsList.as_view()),
    url(r'^docs/?$',
        views.Documentation.as_view()),
)

urlpatterns = format_suffix_patterns(urlpatterns)