# -*- coding: utf8 -*-

from django.conf.urls import url, include
from django.contrib import admin

admin.autodiscover()

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^planet/', include('wize_bot.urls', namespace='wize_bot'))
]