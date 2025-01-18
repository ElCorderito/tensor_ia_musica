import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd

# Cargar features_df normalizado sin aplicar pesos
features_df = pd.read_pickle('static/otros/features_df_normalized.pkl')

def recomendar_canciones(nombre_cancion, artista_cancion, album_cancion, df_grouped, user_weights, num_recomendaciones=5):
    try:
        # Buscar la canción usando los tres criterios
        mask = (
            (df_grouped['track_name'].str.lower() == nombre_cancion.lower()) &
            (df_grouped['artists'].str.lower() == artista_cancion.lower()) &
            (df_grouped['album_name'].str.lower() == album_cancion.lower())
        )
        idx_cancion = df_grouped.index[mask].tolist()[0]
    except IndexError:
        # Si la canción no se encuentra, retorna None
        return None

    # Aplicar pesos a las características
    weighted_features = features_df.copy()
    for feature, weight in user_weights.items():
        if feature in weighted_features.columns:
            weighted_features[feature] *= weight

    # Seleccionar las características de la canción seleccionada
    cancion_seleccionada = weighted_features.iloc[idx_cancion].values.reshape(1, -1)

    # Calcular similitudes
    similitudes = cosine_similarity(cancion_seleccionada, weighted_features.values)

    # Crear un DataFrame con los índices y similitudes
    similitudes_df = pd.DataFrame({
        'index': df_grouped.index,
        'track_name': df_grouped['track_name'],
        'artists': df_grouped['artists'],
        'similarity': similitudes[0]
    })

    # Eliminar la canción original
    similitudes_df = similitudes_df[similitudes_df['index'] != idx_cancion]

    # Eliminar duplicados basados en 'track_name' y 'artists'
    similitudes_df = similitudes_df.drop_duplicates(subset=['track_name', 'artists'])

    # Ordenar por similitud descendente
    similitudes_df = similitudes_df.sort_values(by='similarity', ascending=False)

    # Obtener los índices de las canciones más similares
    indices_similares = similitudes_df['index'].head(num_recomendaciones).tolist()

    # Obtener las canciones recomendadas
    canciones_recomendadas = df_grouped.loc[indices_similares]

    return canciones_recomendadas