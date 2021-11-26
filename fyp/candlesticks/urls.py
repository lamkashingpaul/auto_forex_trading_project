from . import views
from django.urls import path
from django.conf.urls import url, include
from rest_framework import routers

router = routers.DefaultRouter()
router.register(r'candlesticks', views.CandlestickViewSet)

urlpatterns = [
    url('^api/', include(router.urls)),
    path('', views.index, name='index'),
    path('celery/', views.celery_test, name='celery'),
    path('backtest/', views.backtest, name='index'),
]
