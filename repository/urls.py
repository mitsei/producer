from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns
from repository import views

urlpatterns = patterns('',
    url(r'^repositories/(?P<repository_id>[-.:@%\d\w]+)/assets/?$',
        views.AssetsList.as_view()),
    url(r'^repositories/(?P<repository_id>[-.:@%\d\w]+)/children/?$',
        views.RepositoryChildrenList.as_view()),
    url(r'^repositories/(?P<repository_id>[-.:@%\d\w]+)/compositions/?$',
        views.CompositionsList.as_view()),
    url(r'^repositories/(?P<repository_id>[-.:@%\d\w]+)/compositions/(?P<composition_id>[-.:@%\d\w]+)/children/?$',
        views.CompositionChildrenList.as_view()),
    url(r'^repositories/(?P<repository_id>[-.:@%\d\w]+)/compositions/(?P<composition_id>[-.:@%\d\w]+)/unlock/?$',
        views.UnlockComposition.as_view()),
    url(r'^repositories/(?P<repository_id>[-.:@%\d\w]+)/download/?$',
        views.RepositoryDownload.as_view()),
    url(r'^repositories/(?P<repository_id>[-.:@%\d\w]+)/queryplans/?$',
        views.RepositoryQueryPlansAvailable.as_view()),
    url(r'^repositories/(?P<repository_id>[-.:@%\d\w]+)/search/?$',
        views.RepositorySearch.as_view()),
    url(r'^repositories/(?P<repository_id>[-.:@%\d\w]+)/upload/?$',
        views.UploadNewClassFile.as_view()),
    url(r'^repositories/(?P<repository_id>[-.:@%\d\w]+)/?$',
        views.RepositoryDetails.as_view()),
    url(r'^repositories/?$',
        views.RepositoriesList.as_view()),
    url(r'^assets/?$',
        views.AssetsList.as_view()),
    url(r'^assets/(?P<asset_id>[-.:@%\d\w]+)/?$',
        views.AssetDetails.as_view()),
    url(r'^assets/(?P<asset_id>[-.:@%\d\w]+)/download/?$',
        views.AssetDownload.as_view()),
    url(r'^compositions/?$',
        views.CompositionsList.as_view()),
    url(r'^compositions/(?P<composition_id>[-.:@%\d\w]+)/?$',
        views.CompositionDetails.as_view()),
    url(r'^compositions/(?P<composition_id>[-.:@%\d\w]+)/assets/?$',
        views.CompositionAssetsList.as_view()),
    url(r'^compositions/(?P<composition_id>[-.:@%\d\w]+)/children/?$',
        views.CompositionChildrenList.as_view()),
    url(r'^compositions/(?P<composition_id>[-.:@%\d\w]+)/download/?$',
        views.CompositionDownload.as_view()),
    url(r'^compositions/(?P<composition_id>[-.:@%\d\w]+)/offerings/?$',
        views.CompositionOfferingsList.as_view()),
    url(r'^compositions/(?P<composition_id>[-.:@%\d\w]+)/unlock/?$',
        views.UnlockComposition.as_view()),
)

urlpatterns = format_suffix_patterns(urlpatterns)