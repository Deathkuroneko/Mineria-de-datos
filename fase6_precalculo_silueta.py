import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from scipy.cluster.hierarchy import linkage, fcluster
from sklearn.metrics import silhouette_score, silhouette_samples
import os
import json

PARQUET_OPTIMIZADO = "opensky_datos_optimizados.parquet"
PARQUET_SILUETA = "opensky_siluetas_por_lote.parquet"

def get_k_optimo():
    """
    Recupera el número óptimo de clústeres calculado previamente.
    Retorna el número de clústeres como entero.
    """
    try:
        with open("mineria_resultados.json", "r") as f:
            data = json.load(f)
            return int(data.get("n_clusters", 3))  # Convertir a int
    except:
        return 3

K_CLUSTERS = get_k_optimo()

def precalcular_siluetas(k=K_CLUSTERS):
    """
    Calcula el coeficiente de silueta para evaluar la calidad del clustering en cada lote de datos.
    Guarda los resultados en un archivo Parquet.
    """
    print("📊 Precalculando coeficiente de silueta por lote...")
    df = pd.read_parquet(PARQUET_OPTIMIZADO)
    fechas = df['fecha_captura_sistema'].unique()
    resultados = []
    for fecha in fechas:
        print(f"  Procesando lote {fecha}...")
        df_lote = df[df['fecha_captura_sistema'] == fecha]
        X = df_lote[['latitude', 'longitude', 'velocity_kmh', 'vertical_rate']].dropna()
        if len(X) < 2:
            continue
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        Z = linkage(X_scaled, method='ward')
        clusters = fcluster(Z, t=k, criterion='maxclust')
        if len(set(clusters)) < 2:
            continue
        sil_score = silhouette_score(X_scaled, clusters)
        sil_samples = silhouette_samples(X_scaled, clusters)
        sil_per_cluster = {}
        for c in set(clusters):
            mask = clusters == c
            sil_per_cluster[int(c)] = float(sil_samples[mask].mean()) if np.any(mask) else 0.0
        resultados.append({
            'fecha_lote': fecha,
            'k': k,
            'silhouette_mean': sil_score,
            'silhouette_per_cluster': str(sil_per_cluster)
        })
    df_sil = pd.DataFrame(resultados)
    df_sil.to_parquet(PARQUET_SILUETA, index=False)
    print(f"✅ Siluetas guardadas en {PARQUET_SILUETA}")

if __name__ == "__main__":
    precalcular_siluetas()