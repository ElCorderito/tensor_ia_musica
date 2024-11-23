# ai_scripts/simple_recommender.py
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
load_dotenv()

# Usar las variables de entorno
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
SPOTIPY_REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')

# Diccionario simple de canciones por género (IA básica)
song_database = {
    'rock': ['Bohemian Rhapsody - Queen', 'Stairway to Heaven - Led Zeppelin', 'Hotel California - Eagles'],
    'pop': ['Bad Guy - Billie Eilish', 'Blinding Lights - The Weeknd', 'Shape of You - Ed Sheeran'],
    'hiphop': ['Sicko Mode - Travis Scott', 'God\'s Plan - Drake', 'Rockstar - Post Malone'],
    'canadian pop': ['Blinding Lights - The Weeknd']  # Si el género devuelto es "canadian pop"
}

# Función para configurar la autenticación con Spotify
def spotify_auth():
    return SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope="user-library-read"
    )

# Función para obtener toda la información de una canción usando Spotify
def get_track_info_from_spotify(track_id, token):
    sp = Spotify(auth=token)
    track_info = sp.track(track_id)
    
    # Extraemos toda la información relevante
    song_details = {
        "name": track_info['name'],
        "album": track_info['album']['name'],
        "artists": [artist['name'] for artist in track_info['artists']],  # Lista de todos los artistas
        "release_date": track_info['album']['release_date'],
        "genres": sp.artist(track_info['artists'][0]['id'])['genres'],  # Géneros del artista
        "duration_ms": track_info['duration_ms'],  # Duración en milisegundos
        "popularity": track_info['popularity'],  # Popularidad del track
        "external_urls": track_info['external_urls']['spotify'],  # Enlace de la canción en Spotify
    }

    return song_details

# Recomendador basado en géneros con integración a Spotify
def recommend_songs(track_id, token):
    sp = Spotify(auth=token)  # Aquí definimos la variable 'sp'
    
    track_info = get_track_info_from_spotify(track_id, token)  # Obtiene la información completa de la canción

    # Imprime la información de la canción
    print(f"Información de la canción:")
    for key, value in track_info.items():
        print(f"{key}: {value}")

    # Obtén los géneros del artista
    artist_id = sp.track(track_id)['artists'][0]['id']
    artist_info = sp.artist(artist_id)

    genres = artist_info['genres'] if artist_info['genres'] else ["Género no disponible"]

    print(f"Géneros obtenidos de Spotify: {genres}")  # Imprime los géneros en la consola para depurar

    # Buscar si alguno de los géneros del artista tiene una palabra clave que coincida en el diccionario 'song_database'
    for genre in genres:
        for key in song_database:
            if key in genre:  # Verificamos si el género del artista contiene una palabra clave de los géneros de la base de datos
                print(f"Se encontró coincidencia: {genre} coincide con {key}")
                return song_database[key]  # Devolvemos las recomendaciones para esa coincidencia

    # Si ninguno de los géneros coincide, no hay recomendaciones
    return ['No recommendations available for this genre']
