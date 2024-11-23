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

load_dotenv()
df = pd.read_csv('static/otros/dataset.csv')

encoder_model = tf.keras.models.load_model('static/otros/encoder_model.h5')
latent_representations = np.load('static/otros/latent_representations.npy')
df_grouped = pd.read_pickle('static/otros/df_grouped.pkl')

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
    if request.method == 'POST' or 'nombre_cancion' in request.session:
        nombre_cancion = request.POST.get('nombre_cancion') or request.session.pop('nombre_cancion', '')
        artista_cancion = request.POST.get('artista_cancion') or request.session.pop('artista_cancion', '')
        album_cancion = request.POST.get('album_cancion') or request.session.pop('album_cancion', '')

        # Llamar a la función recomendar_canciones con los datos proporcionados
        recomendaciones_df = recomendar_canciones(nombre_cancion, artista_cancion, album_cancion, df_grouped, latent_representations)

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
                if not track_name or not artist_name:
                    rec['preview_url'] = None
                    continue
                # Buscar la canción en Spotify
                query = f"track:{track_name} artist:{artist_name}"
                try:
                    results = sp.search(q=query, type='track', limit=1)
                    if results['tracks']['items']:
                        track = results['tracks']['items'][0]
                        rec['preview_url'] = track.get('preview_url')
                    else:
                        rec['preview_url'] = None
                except Exception as e:
                    print(f"Error al buscar en Spotify: {e}")
                    rec['preview_url'] = None

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
