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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)

RUTA_OPTIMIZADO = os.path.join(PARENT_DIR, "opensky_datos_optimizados.parquet")
RUTA_RESULTADOS = os.path.join(PARENT_DIR, "opensky_resultados_mineria.parquet")
RUTA_SILUETA = os.path.join(PARENT_DIR, "opensky_siluetas_por_lote.parquet")
RUTA_GLOBAL_STATS = os.path.join(PARENT_DIR, "opensky_estadisticas_globales.parquet")  
RUTA_MINERIA_JSON = os.path.join(PARENT_DIR, "mineria_resultados.json")  
RUTA_METRICS_JSON = os.path.join(PARENT_DIR, "pipeline_metrics.json")

NUM_LOTES_A_DEVOLVER = 5

@app.get("/api/vuelos")
def obtener_vuelos_minados():
    """
    Retorna los datos de los vuelos procesados, limitados a un número de lotes determinado.
    """
    try:
        df = pd.read_parquet(RUTA_RESULTADOS)
        df = df.replace([np.inf, -np.inf], np.nan)
        
        fechas = df['fecha_captura_sistema'].unique()
        fechas = np.sort(fechas)
        
        if len(fechas) > NUM_LOTES_A_DEVOLVER:
            fechas = fechas[:NUM_LOTES_A_DEVOLVER]
        
        df_filtrado = df[df['fecha_captura_sistema'].isin(fechas)]
        
        json_limpio = df_filtrado.to_json(orient="records", default_handler=str)
        return Response(content=json_limpio, media_type="application/json")
        
    except Exception as e:
        return Response(content=f'{{"error": "No se pudieron leer los datos: {str(e)}"}}', media_type="application/json")
    
@app.get("/api/metodo-codo")
def obtener_metodo_codo():
    """
    Calcula el valor de la inercia (WCSS) para distintos números de clústeres a partir del último lote procesado.
    """
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
    Retorna la imagen codificada en base64 junto con metadatos del lote.
    """
    try:
        df = pd.read_parquet(RUTA_OPTIMIZADO)
        
        if fecha_lote is None:
            ultima_fecha = df['fecha_captura_sistema'].max()
        else:
            ultima_fecha = fecha_lote
        
        df_lote = df[df['fecha_captura_sistema'] == ultima_fecha]
        if df_lote.empty:
            return {"error": f"No hay datos para el lote {ultima_fecha}"}
        
        X = df_lote[['latitude', 'longitude', 'velocity_kmh', 'vertical_rate']].dropna()
        if len(X) == 0:
            return {"error": "No hay datos válidos en este lote"}
        
        sample_size = min(sample_size, len(X))
        X_sample = X.sample(n=sample_size, random_state=42)
        
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_sample)
        
        plt.figure(figsize=(10, 5))
        linkage = sch.linkage(X_scaled, method='ward')
        sch.dendrogram(linkage, no_labels=True, color_threshold=None)
        plt.title(f'Dendrograma Jerárquico - Lote {ultima_fecha} ({len(X_sample)} muestras)')
        plt.xlabel('Aeronaves (muestra aleatoria)')
        plt.ylabel('Distancia de fusión')
        plt.tight_layout()
        
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
    """
    Retorna los coeficientes de silueta calculados para evaluar el agrupamiento de los datos del lote.
    """
    try:
        if not os.path.exists(RUTA_SILUETA):
            return {"error": "Archivo de siluetas no encontrado. Ejecuta 'fase5_precalculo_silueta.py' primero."}
        
        df_sil = pd.read_parquet(RUTA_SILUETA)
        
        if fecha_lote is None:
            fila = df_sil.iloc[-1]
        else:
            fila = df_sil[df_sil['fecha_lote'] == fecha_lote]
            if fila.empty:
                return {"error": f"No hay silueta para el lote {fecha_lote}"}
            fila = fila.iloc[0]
        
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
    Retorna un subconjunto de variables con asignación de clústeres y detección de anomalías para generar gráficos de dispersión.
    """
    try:
        df = pd.read_parquet(RUTA_RESULTADOS)
        
        if fecha_lote is None:
            ultima_fecha = df['fecha_captura_sistema'].max()
        else:
            ultima_fecha = fecha_lote
        
        df_lote = df[df['fecha_captura_sistema'] == ultima_fecha]
        if df_lote.empty:
            return {"error": f"No hay datos para el lote {ultima_fecha}"}
        
        scatter_data = df_lote[['velocity_kmh', 'baro_altitude', 'cluster_vuelo', 'es_anomalia']].dropna()
        if len(scatter_data) == 0:
            return {"error": "No hay datos válidos en este lote"}
        
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
    Retorna las estadísticas descriptivas para el lote especificado basadas en los cálculos previos.
    """
    try:
        RUTA_ESTADISTICAS = os.path.join(PARENT_DIR, "opensky_estadisticas_lotes.parquet")
        
        if not os.path.exists(RUTA_ESTADISTICAS):
            return {"error": "El archivo de estadísticas no existe. Ejecuta la Fase 5 primero."}
        
        df_stats = pd.read_parquet(RUTA_ESTADISTICAS)
        
        if fecha_lote is None:
            df_stats = df_stats.sort_values('fecha_lote')
            fila = df_stats.iloc[-1]
        else:
            fila = df_stats[df_stats['fecha_lote'] == fecha_lote]
            if fila.empty:
                return {"error": f"No hay estadísticas para el lote {fecha_lote}"}
            fila = fila.iloc[0]
        
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
    Retorna la evolución temporal agregada (totales, anomalías, promedios) de los lotes procesados.
    """
    try:
        df = pd.read_parquet(RUTA_RESULTADOS)
        grouped = df.groupby('fecha_captura_sistema').agg(
            total_aviones=('icao24', 'count'),
            anomalias=('es_anomalia', lambda x: x.sum() if 'es_anomalia' in x else 0),
            velocidad_media=('velocity_kmh', 'mean'),
            altitud_media=('baro_altitude', 'mean')
        ).reset_index()
        
        grouped = grouped.sort_values('fecha_captura_sistema')
        
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
    """
    Retorna los datos y la imagen precalculada del mapa de calor de correlación.
    """
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
    """
    Retorna las estadísticas descriptivas calculadas a nivel global sobre todos los datos procesados.
    """
    try:
        if os.path.exists(RUTA_GLOBAL_STATS):
            df_global = pd.read_parquet(RUTA_GLOBAL_STATS)
            stats = df_global.iloc[0].to_dict()
            for key, value in stats.items():
                if isinstance(value, (np.int64, np.int32)):
                    stats[key] = int(value)
                elif isinstance(value, (np.float64, np.float32)):
                    stats[key] = float(value)
            return stats
        else:
            df = pd.read_parquet(RUTA_RESULTADOS)
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/mineria-resultados")
def obtener_mineria_resultados():
    """
    Retorna los resultados y métricas del proceso de minería de datos.
    """
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
    """
    Retorna las métricas de rendimiento generadas por la ejecución del pipeline de datos.
    """
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