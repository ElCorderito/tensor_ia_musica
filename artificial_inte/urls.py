from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from app_artificial import views
from django.conf.urls.static import static
from app_artificial.views import *

urlpatterns = [
    path('', views.index, name='index'),  # Página de inicio
    path('spotify_recommend/', views.recommend_view_spotify, name='spotify_recommend'),  # Recomendaciones de Spotify
    path('spotify_recommend_with_ia/', views.recommend_view_with_ia, name='spotify_recommend_with_ia'),  # IA con Spotify
    path('spotify_login/', views.spotify_login, name='spotify_login'),  # Inicio de sesión de Spotify
    path('callback/', views.spotify_callback, name='spotify_callback'),  # Callback de Spotify
    path('tensoria/', views.tensoria_view, name='tensoria'),  # Recomendaciones del Tensorflow
    path('api/recomendaciones/', RecomendacionAPIView.as_view(), name='api_recomendaciones'),  # API de recomendaciones
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
