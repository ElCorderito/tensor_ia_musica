import os
from django.shortcuts import render, redirect
from .ai_scripts.simple_recommender import recommend_songs, get_track_info_from_spotify
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import time
from dotenv import load_dotenv
import pandas as pd
import numpy as np
import tensorflow as tf
from sklearn.metrics.pairwise import cosine_similarity
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .ai_scripts.recommender import recomendar_canciones
from django.urls import reverse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import RecomendacionSerializer
import json
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from .models import HistorialBusqueda, Recomendacion


load_dotenv()

# Cargar el dataset
df = pd.read_csv('static/otros/dataset.csv')
df['track_genre'] = df['track_genre'].astype(str)

# Agrupar y procesar el DataFrame
df_grouped = df.groupby('track_id').agg({
    'artists': 'first',
    'album_name': 'first',
    'track_name': 'first',
    'popularity': 'first',
    'duration_ms': 'first',
    'explicit': 'first',
    'danceability': 'first',
    'energy': 'first',
    'key': 'first',
    'loudness': 'first',
    'mode': 'first',
    'speechiness': 'first',
    'acousticness': 'first',
    'instrumentalness': 'first',
    'liveness': 'first',
    'valence': 'first',
    'tempo': 'first',
    'time_signature': 'first',
    'track_genre': lambda x: ', '.join(set(x))  # Combinar géneros únicos
}).reset_index()

# Agregar la columna 'track_name_lower' al DataFrame agrupado
df_grouped['track_name_lower'] = df_grouped['track_name'].str.lower()

# Si necesitas cargar df_grouped desde un archivo pickle, asegúrate de agregar la columna
# df_grouped = pd.read_pickle('static/otros/df_grouped.pkl')
# df_grouped['track_name_lower'] = df_grouped['track_name'].str.lower()

# Cargar el modelo y las representaciones latentes
encoder_model = tf.keras.models.load_model('static/otros/encoder_model.h5')
latent_representations = np.load('static/otros/latent_representations.npy')

# Resto de tu código...

#df_grouped = pd.read_pickle('static/otros/df_grouped.pkl')

# Usar las variables de entorno
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
SPOTIPY_REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')

def index(request):
    return render(request, 'index.html')


# Función para configurar la autenticación con Spotify
def spotify_auth():
    return SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope="user-library-read"
    )

# Vista para redirigir al usuario a la página de autenticación de Spotify
def spotify_login(request):
    sp_oauth = spotify_auth()
    auth_url = sp_oauth.get_authorize_url()
    # Guardar 'next' en la sesión si existe
    next_url = request.GET.get('next')
    if next_url:
        request.session['next_url'] = next_url
    return redirect(auth_url)


# Vista para obtener recomendaciones de Spotify
def recommend_view_spotify(request):
    token_info = request.session.get('token_info', None)  # Obtiene el token de la sesión
    recommendations = []
    if not token_info:
        return redirect('spotify_login')
    if request.method == 'POST':
        track_id = request.POST.get('track_id')
        recommendations = recommend_from_spotify(track_id, token_info['access_token'])
    return render(request, 'spotify_recommend_form.html', {'recommendations': recommendations})

# Vista para manejar el callback de redirección desde Spotify
def spotify_callback(request):
    sp_oauth = spotify_auth()
    code = request.GET.get('code')
    token_info = sp_oauth.get_access_token(code)
    request.session['token_info'] = token_info
    # Recuperar 'next_url' de la sesión
    next_url = request.session.pop('next_url', None)
    if next_url:
        return redirect(next_url)
    else:
        return redirect('tensoria')  # O redirige a una página predeterminada


def recommend_from_spotify(track_id, token):
    sp = Spotify(auth=token)
    recommendations = sp.recommendations(seed_tracks=[track_id], limit=5)
    return recommendations['tracks']

# Vista para la IA con integración de Spotify
def recommend_view_with_ia(request):
    token_info = refresh_token_if_needed(request)
    if token_info is None:
        return redirect('spotify_login')
    recommendations = []
    track_info = None
    if request.method == 'POST':
        track_id = request.POST.get('track_id')
        track_info = get_track_info_from_spotify(track_id, token_info['access_token'])
        recommendations = recommend_songs(track_id, token_info['access_token'])
    return render(request, 'ia.html', {'recommendations': recommendations, 'track_info': track_info})

def is_token_expired(token_info):
    now = int(time.time())
    return token_info['expires_at'] - now < 60

def refresh_token_if_needed(request):
    token_info = request.session.get('token_info', None)
    if token_info is None:
        return None
    sp_oauth = spotify_auth()
    if is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        request.session['token_info'] = token_info
    return token_info


def tensoria_view(request):
    recomendaciones = None
    mensaje_error = None
    if request.method == 'POST':
        nombre_cancion = request.POST.get('nombre_cancion', '').strip()
        artista_cancion = request.POST.get('artista_cancion', '').strip()
        album_cancion = request.POST.get('album_cancion', '').strip()

        if not artista_cancion or not album_cancion:
            # Buscar en el DataFrame agrupado
            match = df_grouped[df_grouped['track_name_lower'] == nombre_cancion.lower()]
            if not match.empty:
                artista_cancion = match.iloc[0]['artists']
                album_cancion = match.iloc[0]['album_name']
            else:
                mensaje_error = "No se encontró la canción en la base de datos."
                return render(request, 'tensoria.html', {
                    'recomendaciones': recomendaciones,
                    'nombre_cancion': nombre_cancion,
                    'artista_cancion': artista_cancion,
                    'album_cancion': album_cancion,
                    'mensaje_error': mensaje_error
                })

        # Llamar a la función recomendar_canciones con los datos proporcionados
        recomendaciones_df = recomendar_canciones(
            nombre_cancion, artista_cancion, album_cancion, df_grouped, latent_representations
        )

        # Verificar si se obtuvieron recomendaciones
        if recomendaciones_df is not None and not recomendaciones_df.empty:
            recomendaciones = recomendaciones_df.to_dict(orient='records')

            # Para cada recomendación, obtener el preview_url usando la API de Spotify
            token_info = refresh_token_if_needed(request)
            if token_info is None:
                # Almacenar datos del formulario en la sesión
                request.session['nombre_cancion'] = nombre_cancion
                request.session['artista_cancion'] = artista_cancion
                request.session['album_cancion'] = album_cancion
                login_url = f"{reverse('spotify_login')}?next={request.path}"
                return redirect(login_url)

            sp = Spotify(auth=token_info['access_token'])
            for rec in recomendaciones:
                # Verificar que las claves existen
                track_name = rec.get('track_name') or rec.get('track_name_column_name')
                artist_name = rec.get('artists') or rec.get('artist_name_column_name')

                # Asegurarse de que los campos track_name y artist_name estén definidos
                if not track_name or not artist_name:
                    rec['preview_url'] = None
                    rec['album_cover_url'] = None
                    continue

                # Construir la consulta para Spotify
                query = f"track:{track_name} artist:{artist_name}"
                try:
                    results = sp.search(q=query, type='track', limit=1)

                    # Verificar si se encontraron resultados
                    if results['tracks']['items']:
                        track = results['tracks']['items'][0]

                        # Manejar el preview_url
                        rec['preview_url'] = track.get('preview_url')

                        # Manejar la URL de la imagen del álbum
                        rec['album_cover_url'] = (
                            track['album']['images'][0]['url'] if track['album']['images'] else None
                        )
                    else:
                        # Si no se encuentran resultados
                        rec['preview_url'] = None
                        rec['album_cover_url'] = None

                except Exception as e:
                    # Manejo de errores al buscar en Spotify
                    print(f"Error al buscar en Spotify: {e}")
                    rec['preview_url'] = None
                    rec['album_cover_url'] = None

            # Guardar en el historial si el usuario está autenticado
            if request.user.is_authenticated:
                historial_entry = HistorialBusqueda.objects.create(
                    usuario=request.user,
                    nombre_cancion=nombre_cancion,
                    artista_cancion=artista_cancion,
                    album_cancion=album_cancion
                )

                # Guardar cada recomendación en el modelo Recomendacion
                recomendacion_objects = []
                for rec in recomendaciones:
                    # Obtener datos de la recomendación
                    track_name = rec.get('track_name') or rec.get('track_name_column_name')
                    artist_name = rec.get('artists') or rec.get('artist_name_column_name')
                    album_name = rec.get('album_name')
                    track_genre = rec.get('track_genre')
                    preview_url = rec.get('preview_url')
                    album_cover_url = rec.get('album_cover_url')

                    # Crear instancia de Recomendacion
                    recomendacion = Recomendacion(
                        historial=historial_entry,
                        track_name=track_name,
                        artists=artist_name,
                        album_name=album_name,
                        track_genre=track_genre,
                        preview_url=preview_url,
                        album_cover_url=album_cover_url
                    )
                    recomendacion_objects.append(recomendacion)

                # Guardar todas las recomendaciones de una vez
                Recomendacion.objects.bulk_create(recomendacion_objects)

        else:
            mensaje_error = "No se encontraron recomendaciones para la canción proporcionada."
    else:
        nombre_cancion = ''
        artista_cancion = ''
        album_cancion = ''

    return render(request, 'tensoria.html', {
        'recomendaciones': recomendaciones,
        'nombre_cancion': nombre_cancion,
        'artista_cancion': artista_cancion,
        'album_cancion': album_cancion,
        'mensaje_error': mensaje_error
    })

@require_GET
def autocomplete_songs(request):
    query = request.GET.get('term', '')
    if query:
        matches = df_grouped[df_grouped['track_name_lower'].str.contains(query.lower(), na=False)].head(20)
        # Convertir a lista de diccionarios
        suggestions = matches[['track_name', 'artists', 'album_name', 'track_genre']].to_dict(orient='records')
    else:
        suggestions = []
    return JsonResponse(suggestions, safe=False)


"""
class RecomendacionAPIView(APIView):
    def post(self, request):
        nombre_cancion = request.data.get('nombre_cancion')
        artista_cancion = request.data.get('artista_cancion')
        album_cancion = request.data.get('album_cancion')

        recomendaciones_df = recomendar_canciones(
            nombre_cancion, artista_cancion, album_cancion, df_grouped, latent_representations
        )

        if recomendaciones_df is not None and not recomendaciones_df.empty:
            recomendaciones = recomendaciones_df.to_dict(orient='records')

            # Obtener preview_url de Spotify para cada recomendación
            token_info = refresh_token_if_needed(request)
            if token_info is None:
                return Response({'error': 'No autenticado en Spotify'}, status=status.HTTP_401_UNAUTHORIZED)
            sp = Spotify(auth=token_info['access_token'])
            for rec in recomendaciones:
                query = f"track:{rec['track_name']} artist:{rec['artists']}"
                results = sp.search(q=query, type='track', limit=1)
                if results['tracks']['items']:
                    track = results['tracks']['items'][0]
                    rec['preview_url'] = track.get('preview_url')
                else:
                    rec['preview_url'] = None

            serializer = RecomendacionSerializer(recomendaciones, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'No se encontraron recomendaciones.'}, status=status.HTTP_404_NOT_FOUND)
"""

@login_required
def historial_view(request):
    historial = HistorialBusqueda.objects.filter(usuario=request.user).order_by('-fecha_busqueda')
    return render(request, 'historial.html', {'historial': historial})

def sobre_nosotros_view(request):
    return render(request, 'sobre_nosotros.html')
