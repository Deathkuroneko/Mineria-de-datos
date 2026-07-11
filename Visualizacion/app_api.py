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
import json
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
RUTA_SILUETA = os.path.join(PARENT_DIR, "opensky_siluetas_por_lote.parquet")
RUTA_GLOBAL_STATS = os.path.join(PARENT_DIR, "opensky_estadisticas_globales.parquet")  
RUTA_MINERIA_JSON = os.path.join(PARENT_DIR, "mineria_resultados.json")  
RUTA_METRICS_JSON = os.path.join(PARENT_DIR, "pipeline_metrics.json")

# Al inicio del archivo, define cuántos lotes quieres enviar
NUM_LOTES_A_DEVOLVER = 5  # Cambia este valor según necesites

@app.get("/api/vuelos")
def obtener_vuelos_minados():
    try:
        df = pd.read_parquet(RUTA_RESULTADOS)
        df = df.replace([np.inf, -np.inf], np.nan)
        
        # Obtener las fechas únicas ordenadas
        fechas = df['fecha_captura_sistema'].unique()
        fechas = np.sort(fechas)  # orden ascendente (la más antigua primero)
        
        # Tomar solo los primeros NUM_LOTES_A_DEVOLVER
        if len(fechas) > NUM_LOTES_A_DEVOLVER:
            fechas = fechas[:NUM_LOTES_A_DEVOLVER]
        
        # Filtrar el DataFrame para que solo incluya esos lotes
        df_filtrado = df[df['fecha_captura_sistema'].isin(fechas)]
        
        # Serializar a JSON
        json_limpio = df_filtrado.to_json(orient="records", default_handler=str)
        return Response(content=json_limpio, media_type="application/json")
        
    except Exception as e:
        return Response(content=f'{{"error": "No se pudieron leer los datos: {str(e)}"}}', media_type="application/json")
    
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
    
@app.get("/api/silhouette-precalc")
def obtener_silhouette_precalc(
    fecha_lote: str = Query(None, description="Fecha del lote. Si no se envía, usa el último.")
):
    try:
        # Verificar si existe el archivo
        if not os.path.exists(RUTA_SILUETA):
            return {"error": "Archivo de siluetas no encontrado. Ejecuta 'fase5_precalculo_silueta.py' primero."}
        
        df_sil = pd.read_parquet(RUTA_SILUETA)
        
        if fecha_lote is None:
            fila = df_sil.iloc[-1]  # último lote
        else:
            fila = df_sil[df_sil['fecha_lote'] == fecha_lote]
            if fila.empty:
                return {"error": f"No hay silueta para el lote {fecha_lote}"}
            fila = fila.iloc[0]
        
        # Convertir el string de sil_per_cluster a dict
        import ast
        sil_per_cluster = ast.literal_eval(fila['silhouette_per_cluster'])
        
        return {
            "fecha_lote": str(fila['fecha_lote']),
            "k": int(fila['k']),
            "silhouette_mean": float(fila['silhouette_mean']),
            "silhouette_per_cluster": sil_per_cluster
        }
    except Exception as e:
        return {"error": str(e)}
    
@app.get("/api/scatter-lote")
def obtener_scatter_por_lote(
    fecha_lote: str = Query(None, description="Fecha del lote. Si no se envía, usa el último lote.")
):
    """
    Devuelve los datos para el scatter plot: velocity_kmh vs baro_altitude, con cluster y anomalía.
    """
    try:
        df = pd.read_parquet(RUTA_RESULTADOS)  # Usamos el dataset con etiquetas
        
        if fecha_lote is None:
            ultima_fecha = df['fecha_captura_sistema'].max()
        else:
            ultima_fecha = fecha_lote
        
        df_lote = df[df['fecha_captura_sistema'] == ultima_fecha]
        if df_lote.empty:
            return {"error": f"No hay datos para el lote {ultima_fecha}"}
        
        # Seleccionar columnas necesarias
        scatter_data = df_lote[['velocity_kmh', 'baro_altitude', 'cluster_vuelo', 'es_anomalia']].dropna()
        if len(scatter_data) == 0:
            return {"error": "No hay datos válidos en este lote"}
        
        # Convertir a lista de diccionarios para JSON
        registros = scatter_data.to_dict(orient='records')
        
        return {
            "fecha_lote": str(ultima_fecha),
            "registros": registros,
            "total": len(registros)
        }
    except Exception as e:
        return {"error": str(e)}
    
@app.get("/api/estadisticas-lote")
def obtener_estadisticas_lote(
    fecha_lote: str = Query(None, description="Fecha del lote. Si no se envía, usa el último lote.")
):
    """
    Devuelve estadísticas resumidas del lote especificado.
    Lee directamente del Parquet pre-calculado (Fase 5).
    """
    try:
        # Ruta al Parquet de estadísticas por lote
        RUTA_ESTADISTICAS = os.path.join(PARENT_DIR, "opensky_estadisticas_lotes.parquet")
        
        if not os.path.exists(RUTA_ESTADISTICAS):
            return {"error": "El archivo de estadísticas no existe. Ejecuta la Fase 5 primero."}
        
        df_stats = pd.read_parquet(RUTA_ESTADISTICAS)
        
        # Si no se especifica fecha, usar el último lote
        if fecha_lote is None:
            # Tomar la fecha más reciente (ordenada)
            df_stats = df_stats.sort_values('fecha_lote')
            fila = df_stats.iloc[-1]
        else:
            fila = df_stats[df_stats['fecha_lote'] == fecha_lote]
            if fila.empty:
                return {"error": f"No hay estadísticas para el lote {fecha_lote}"}
            fila = fila.iloc[0]
        
        # Deserializar JSONs
        cluster_dist = json.loads(fila['cluster_distribucion'])
        top_paises = json.loads(fila['top_paises'])
        
        return {
            "fecha_lote": fila['fecha_lote'],
            "total_aviones": int(fila['total_aviones']),
            "anomalias": int(fila['anomalias']),
            "porcentaje_anomalias": float(fila['porcentaje_anomalias']),
            "velocidad": {
                "media": float(fila['velocidad_media']),
                "std": float(fila['velocidad_std']),
                "min": float(fila['velocidad_min']),
                "max": float(fila['velocidad_max'])
            },
            "altitud": {
                "media": float(fila['altitud_media']),
                "std": float(fila['altitud_std']),
                "min": float(fila['altitud_min']),
                "max": float(fila['altitud_max'])
            },
            "tasa_vertical": {
                "media": float(fila['tv_media']),
                "std": float(fila['tv_std'])
            },
            "cluster_distribucion": cluster_dist,
            "top_paises": top_paises,
            "en_tierra": int(fila['en_tierra'])
        }
    except Exception as e:
        return {"error": str(e)}
    
@app.get("/api/evolucion-temporal")
def obtener_evolucion_temporal():
    """
    Devuelve los datos agregados por lote (fecha, total_aviones, anomalias, velocidad_media)
    para todos los lotes disponibles.
    """
    try:
        df = pd.read_parquet(RUTA_RESULTADOS)
        # Agrupar por fecha_captura_sistema
        grouped = df.groupby('fecha_captura_sistema').agg(
            total_aviones=('icao24', 'count'),
            anomalias=('es_anomalia', lambda x: x.sum() if 'es_anomalia' in x else 0),
            velocidad_media=('velocity_kmh', 'mean'),
            altitud_media=('baro_altitude', 'mean')
        ).reset_index()
        
        # Ordenar por fecha
        grouped = grouped.sort_values('fecha_captura_sistema')
        
        # Convertir a listas para JSON
        fechas = grouped['fecha_captura_sistema'].astype(str).tolist()
        totales = grouped['total_aviones'].tolist()
        anomalias = grouped['anomalias'].fillna(0).astype(int).tolist()
        velocidades = grouped['velocidad_media'].fillna(0).tolist()
        altitudes = grouped['altitud_media'].fillna(0).tolist()
        
        return {
            "fechas": fechas,
            "totales": totales,
            "anomalias": anomalias,
            "velocidades": velocidades,
            "altitudes": altitudes
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/mapa-calor")
def obtener_mapa_calor():
    try:
        with open("mapa_calor_estatico.json", "r") as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        return {"error": "Mapa de calor estático no disponible. Ejecuta 'fase7_precalculo_mapa_calor.py' primero."}
    except Exception as e:
        return {"error": str(e)}
    
@app.get("/api/estadisticas-globales")
def obtener_estadisticas_globales():
    try:
        # Intentar leer el Parquet precalculado
        if os.path.exists(RUTA_GLOBAL_STATS):
            df_global = pd.read_parquet(RUTA_GLOBAL_STATS)
            stats = df_global.iloc[0].to_dict()
            # Convertir tipos
            for key, value in stats.items():
                if isinstance(value, (np.int64, np.int32)):
                    stats[key] = int(value)
                elif isinstance(value, (np.float64, np.float32)):
                    stats[key] = float(value)
            return stats
        else:
            # Fallback: calcular sobre la marcha
            df = pd.read_parquet(RUTA_RESULTADOS)
            # ... (código existente)
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/mineria-resultados")
def obtener_mineria_resultados():
    try:
        with open(RUTA_MINERIA_JSON, "r") as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        return {"error": "Archivo de resultados de minería no encontrado. Ejecuta la Fase 4 primero."}
    except Exception as e:
        return {"error": str(e)}
    
@app.get("/api/pipeline-metrics")
def obtener_metricas_pipeline():
    try:
        with open(RUTA_METRICS_JSON, "r") as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        return {"error": "Métricas del pipeline no disponibles. Ejecuta el pipeline primero."}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)