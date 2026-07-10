import numpy as np
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os
import io
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import scipy.cluster.hierarchy as sch
from sklearn.preprocessing import StandardScaler
from fastapi import Query
from sklearn.metrics import silhouette_score, silhouette_samples
from scipy.cluster.hierarchy import fcluster

app = FastAPI(title="OpenSky Data Mining API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rutas relativas: los Parquets están en el directorio padre de Visualizacion/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # directorio donde está app_api.py
PARENT_DIR = os.path.dirname(BASE_DIR)                 # subimos un nivel

RUTA_OPTIMIZADO = os.path.join(PARENT_DIR, "opensky_datos_optimizados.parquet")
RUTA_RESULTADOS = os.path.join(PARENT_DIR, "opensky_resultados_mineria.parquet")

@app.get("/api/vuelos")
def obtener_vuelos_minados():                                                   
    try:
        df = pd.read_parquet(RUTA_RESULTADOS)
        df = df.replace([np.inf, -np.inf], np.nan)
        json_limpio = df.to_json(orient="records", default_handler=str)
        return Response(content=json_limpio, media_type="application/json")
    except Exception as e:
        return Response(content=f'{{"error": "No se pudieron leer los datos minados: {str(e)}"}}', media_type="application/json")
    
@app.get("/api/metodo-codo")
def obtener_metodo_codo():
    try:
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
        
        df = pd.read_parquet(RUTA_OPTIMIZADO)
        ultima_fecha = df['fecha_captura_sistema'].max()
        df_ultimo_lote = df[df['fecha_captura_sistema'] == ultima_fecha]
        X = df_ultimo_lote[['latitude', 'longitude', 'velocity_kmh', 'vertical_rate']].dropna()
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        wcss = []
        for i in range(1, 9):
            kmeans = KMeans(n_clusters=i, init='k-means++', random_state=42, n_init=3)
            kmeans.fit(X_scaled)
            wcss.append(float(kmeans.inertia_))
            
        return {
            "k": list(range(1, 9)),
            "wcss": wcss,
            "info_lote": str(ultima_fecha),
            "registros_procesados": len(X)
        }
    except Exception as e:
        return {"error": str(e)}
    
@app.get("/api/dendrograma-lote")
def obtener_dendrograma_por_lote(
    fecha_lote: str = Query(None, description="Fecha del lote (formato 'YYYY-MM-DD HH:MM:SS'). Si no se envía, usa el último lote."),
    sample_size: int = Query(400, ge=50, le=1500)
):
    """
    Genera un dendrograma jerárquico a partir de una muestra del lote especificado.
    Devuelve la imagen en base64 para incrustar en el frontend.
    """
    try:
        df = pd.read_parquet(RUTA_OPTIMIZADO)
        
        if fecha_lote is None:
            # Si no se especifica, usamos el último lote
            ultima_fecha = df['fecha_captura_sistema'].max()
        else:
            ultima_fecha = fecha_lote
        
        # Filtrar por la fecha indicada
        df_lote = df[df['fecha_captura_sistema'] == ultima_fecha]
        if df_lote.empty:
            return {"error": f"No hay datos para el lote {ultima_fecha}"}
        
        # Seleccionar características para el clustering
        X = df_lote[['latitude', 'longitude', 'velocity_kmh', 'vertical_rate']].dropna()
        if len(X) == 0:
            return {"error": "No hay datos válidos en este lote"}
        
        # Muestreo aleatorio (para no sobrecargar la visualización)
        sample_size = min(sample_size, len(X))
        X_sample = X.sample(n=sample_size, random_state=42)
        
        # Escalar datos
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_sample)
        
        # Generar dendrograma
        plt.figure(figsize=(10, 5))
        linkage = sch.linkage(X_scaled, method='ward')
        sch.dendrogram(linkage, no_labels=True, color_threshold=None)
        plt.title(f'Dendrograma Jerárquico - Lote {ultima_fecha} ({len(X_sample)} muestras)')
        plt.xlabel('Aeronaves (muestra aleatoria)')
        plt.ylabel('Distancia de fusión')
        plt.tight_layout()
        
        # Guardar en buffer y codificar en base64
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close()
        encoded = base64.b64encode(buf.read()).decode('utf-8')
        
        return {
            "imagen": encoded,
            "fecha_lote": str(ultima_fecha),
            "muestras": len(X_sample)
        }
    except Exception as e:
        return {"error": str(e)}
    
@app.get("/api/silhouette")
def obtener_silhouette(
    fecha_lote: str = Query(None, description="Fecha del lote. Si no se envía, usa el último."),
    k: int = Query(3, ge=2, le=10, description="Número de clústeres (K) para evaluar.")
):
    try:
        # 1. Cargar datos optimizados
        df = pd.read_parquet(RUTA_OPTIMIZADO)
        
        # 2. Determinar lote
        if fecha_lote is None:
            ultima_fecha = df['fecha_captura_sistema'].max()
        else:
            ultima_fecha = fecha_lote
        
        df_lote = df[df['fecha_captura_sistema'] == ultima_fecha]
        if df_lote.empty:
            return {"error": f"No hay datos para el lote {ultima_fecha}"}
        
        # 3. Seleccionar características y limpiar nulos
        X = df_lote[['latitude', 'longitude', 'velocity_kmh', 'vertical_rate']].dropna()
        if len(X) == 0:
            return {"error": "No hay datos válidos en este lote"}
        
        # 4. Escalar
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # 5. Clustering jerárquico con K especificado
        linkage = sch.linkage(X_scaled, method='ward')
        # Asignar clústeres (fcluster con criterio 'maxclust')
        clusters = fcluster(linkage, t=k, criterion='maxclust')
        
        # 6. Calcular silueta
        # silhouette_score necesita que el número de clústeres sea > 1 y < n_samples
        if len(set(clusters)) < 2:
            return {"error": "Número insuficiente de clústeres para calcular silueta"}
        
        sil_score = silhouette_score(X_scaled, clusters)
        sil_samples = silhouette_samples(X_scaled, clusters)
        
        # 7. Calcular silueta por clúster (media por clúster)
        sil_per_cluster = {}
        for c in set(clusters):
            mask = clusters == c
            sil_per_cluster[int(c)] = float(sil_samples[mask].mean()) if np.any(mask) else 0.0
        
        return {
            "fecha_lote": str(ultima_fecha),
            "k": k,
            "silhouette_mean": float(sil_score),
            "silhouette_per_cluster": sil_per_cluster,
            "n_samples": len(X)
        }
        
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)