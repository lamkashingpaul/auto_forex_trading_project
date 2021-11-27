from . import views
from django.urls import path
from django.conf.urls import url, include
from django.contrib.auth import views as auth_views
from rest_framework import routers

router = routers.DefaultRouter()
router.register(r'candlesticks', views.CandlestickViewSet)

urlpatterns = [
    url('^api/', include(router.urls)),
    url('^celery-progress/', include('celery_progress.urls')),
    path('', views.index, name='index'),
    path('backtest/', views.backtest, name='index'),
]
