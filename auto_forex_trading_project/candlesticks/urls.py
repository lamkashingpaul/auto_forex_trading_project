from . import views
from django.urls import path
from django.urls import include, re_path
from django.contrib.auth import views as auth_views
from rest_framework import routers

router = routers.DefaultRouter()
router.register(r'candlesticks', views.CandlestickViewSet)

urlpatterns = [
    re_path('^api/', include(router.urls)),
    re_path('^celery-progress/', include('celery_progress.urls')),
    path('', views.index, name='index'),
    path('backtest/', views.backtest, name='index'),
    path('backtest/result/', views.backtest_result, name='index'),
    path('optimization/', views.optimization, name='index'),
    path('optimization/result/', views.optimization_result, name='index'),
]
