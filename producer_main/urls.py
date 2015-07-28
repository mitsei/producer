from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'MechRevTest.views.home', name='home'),
    # url(r'^MechRevTest/', include('MechRevTest.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/?', include(admin.site.urls)),

    url(r'^$', 'ui.views.login_page', name='login'),
    url(r'^api/v1/?', include('producer.urls', namespace='producer')),
    url(r'^touchstone/api/v1/?', include('producer.urls', namespace='producer.touchstone')),
)
