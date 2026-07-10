import numpy as np
from fastapi import FastAPI, Response  # <--- Agregamos Response aquí
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

app = FastAPI(title="OpenSky Data Mining API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

RUTA_RESULTADOS = "../opensky_resultados_mineria.parquet"   

@app.get("/api/vuelos")
def obtener_vuelos_minados():
    """ Lee el archivo Parquet de la Fase 4 y expone los datos limpios en JSON """
    try:
        # 1. Leer el archivo Parquet
        df = pd.read_parquet(RUTA_RESULTADOS)
        
        # 2. Reemplazar infinitos por nulos de pandas
        df = df.replace([np.inf, -np.inf], np.nan)
        
        # 3. Forzar serialización directa a string JSON con soporte nativo de nulos (ISO-compliant)
        # 'orient="records"' genera la lista de diccionarios exacta que app.js espera.
        json_limpio = df.to_json(orient="records", default_handler=str)
        
        # 4. Retornar la respuesta HTTP cruda indicando que es un JSON aplicativo
        return Response(content=json_limpio, media_type="application/json")
        
    except Exception as e:
        # Si hay error, lo devolvemos como JSON manual estructurado
        return Response(content=f'{{"error": "No se pudieron leer los datos minados: {str(e)}"}}', media_type="application/json")
    
@app.get("/api/metodo-codo")
def obtener_metodo_codo():
    try:
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
        import pandas as pd
        import numpy as np
        
        # 1. Leer el dataset Parquet optimizado
        df = pd.read_parquet("opensky_datos_optimizados.parquet")
        
        # 2. IDENTIFICAR EL ÚLTIMO LOTE DEL SISTEMA (La foto más reciente del espacio aéreo)
        ultima_fecha = df['fecha_captura_sistema'].max()
        
        # 3. Filtrar el dataset para quedarnos solo con los datos de ese instante de captura
        df_ultimo_lote = df[df['fecha_captura_sistema'] == ultima_fecha]
        
        # 4. Extraer variables numéricas para la minería eliminando nulos si existen
        X = df_ultimo_lote[['latitude', 'longitude', 'velocity_kmh', 'vertical_rate']].dropna()
        
        # 5. Escalar datos de forma estándar
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        wcss = []
        for i in range(1, 9):
            kmeans = KMeans(n_clusters=i, init='k-means++', random_state=42, n_init=3)
            kmeans.fit(X_scaled)
            wcss.append(float(kmeans.inertia_))
            
        return {
            "k": list(range(1, 9)), # Cambiado a range(1, 9) -> [1, 2, 3, 4, 5, 6, 7, 8]
            "wcss": wcss,           # Ambos tienen 8 elementos.
            "info_lote": str(ultima_fecha),
            "registros_procesados": len(X)
        }
        
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)