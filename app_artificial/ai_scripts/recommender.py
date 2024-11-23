# app_artificial/ai_scripts/recommender.py

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

def recomendar_canciones(nombre_cancion, artista_cancion, album_cancion, df_grouped, latent_representations, num_recomendaciones=5):
    try:
        # Normalizar las cadenas para evitar problemas de mayúsculas/minúsculas
        mask = (
            (df_grouped['track_name'].str.lower() == nombre_cancion.lower()) &
            (df_grouped['artists'].str.lower() == artista_cancion.lower()) &
            (df_grouped['album_name'].str.lower() == album_cancion.lower())
        )
        idx_cancion = df_grouped.index[mask].tolist()[0]
    except IndexError:
        # Si la canción no se encuentra, retorna None
        return None

    cancion_seleccionada = latent_representations[idx_cancion].reshape(1, -1)
    explicit_seleccionada = df_grouped.loc[idx_cancion, 'explicit']
    similitudes = cosine_similarity(cancion_seleccionada, latent_representations)
    indices_similares = np.argsort(similitudes[0])[::-1]
    # Filtrar canciones que no sean la seleccionada y que tengan el mismo valor de 'explicit'
    indices_similares = [i for i in indices_similares if i != idx_cancion and df_grouped.loc[i, 'explicit'] == explicit_seleccionada]
    canciones_recomendadas = df_grouped.iloc[indices_similares[:num_recomendaciones]]
    return canciones_recomendadas
