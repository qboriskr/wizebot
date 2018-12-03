from django.conf.urls import url

from .views import QuoteView, CommandReceiveView

app_name = 'wize_bot'
urlpatterns = [
    url('quote', QuoteView.as_view(), name='quote'),
    url(r'^bot/(?P<bot_token>.+)/$', CommandReceiveView.as_view(), name='command'),
]
