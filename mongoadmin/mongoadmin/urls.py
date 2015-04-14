from django.conf.urls import patterns, include, url
from django.conf import settings
from django.conf.urls.static import static

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^mongoadmin/', include('mongonaut.urls')),
    url(r'^$', 'mongoadmin.views.login', name="home", kwargs={'type_id': 1}),
    url(r'^login/$', 'mongoadmin.views.login', name="login", kwargs={'type_id': 0}),
    url(r'^logout/$', 'mongoadmin.views.logout'),
)

# add media access.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
