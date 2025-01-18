# models.py
from django.db import models
from django.contrib.auth.models import User

class HistorialBusqueda(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    nombre_cancion = models.CharField(max_length=255)
    artista_cancion = models.CharField(max_length=255)
    album_cancion = models.CharField(max_length=255)
    fecha_busqueda = models.DateTimeField(auto_now_add=True)
    # Añadir campos para los filtros
    filter_danceability = models.BooleanField(default=False)
    filter_energy = models.BooleanField(default=False)
    filter_valence = models.BooleanField(default=False)
    filter_tempo = models.BooleanField(default=False)
    filter_track_genre = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.nombre_cancion} - {self.artista_cancion} ({self.fecha_busqueda.strftime('%d/%m/%Y %H:%M')})"

class Recomendacion(models.Model):
    historial = models.ForeignKey(HistorialBusqueda, on_delete=models.CASCADE, related_name='recomendaciones')
    track_name = models.CharField(max_length=255)
    artists = models.CharField(max_length=255)
    album_name = models.CharField(max_length=255)
    track_genre = models.CharField(max_length=255, blank=True, null=True)
    preview_url = models.URLField(blank=True, null=True)
    album_cover_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"{self.track_name} - {self.artists}"
