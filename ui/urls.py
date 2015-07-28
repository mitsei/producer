from django.conf.urls import patterns, url
from mecqbank_ui import views

urlpatterns = patterns('',
   url(r'^check/$',
        views.check_credentials,
        name="check"),
    url(r'^dashboard/$',
        views.dashboard,
        name="dashboard"),
    url(r'^privacy/$',
        views.privacy,
        name="privacy"),
    url(r'^tos/$',
        views.tos,
        name="tos"),
    url(r'',
        views.login_page,
        name="login"),
)
