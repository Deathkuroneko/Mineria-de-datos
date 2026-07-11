import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
import os
import json

# --- CONFIGURACIÓN DE RUTAS ---
PARQUET_LIMPIO = "opensky_datos_optimizados.parquet"
PARQUET_MINERIA = "opensky_resultados_mineria.parquet"

def calcular_k_optimo_muestreado(df, features, sample_per_lote, max_k=8):
    """
    Calcula K óptimo usando muestreo estratificado por lote.
    """
    fechas = df['fecha_captura_sistema'].unique()
    muestras = []
    for fecha in fechas:
        df_lote = df[df['fecha_captura_sistema'] == fecha]
        if len(df_lote) > sample_per_lote:
            df_lote = df_lote.sample(n=sample_per_lote, random_state=42)
        muestras.append(df_lote)
    df_muestra = pd.concat(muestras, ignore_index=True)
    
    X = df_muestra[features].copy()
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Calcular wcss y codo (igual que antes)
    wcss = []
    for i in range(1, max_k + 1):
        kmeans = KMeans(n_clusters=i, init='k-means++', random_state=42, n_init=3)
        kmeans.fit(X_scaled)
        wcss.append(kmeans.inertia_)
    
    # Método de máxima distancia
    x1, y1 = 1, wcss[0]
    x2, y2 = max_k, wcss[-1]
    distancias = []
    for i in range(1, max_k - 1):
        x0 = i + 1
        y0 = wcss[i]
        numer = abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1)
        denom = np.sqrt((y2 - y1)**2 + (x2 - x1)**2)
        dist = numer / denom if denom != 0 else 0
        distancias.append(dist)
    
    k_optimo = np.argmax(distancias) + 2
    print(f"   ✅ K óptimo (muestreo estratificado, {len(df_muestra):,} muestras): {k_optimo}")
    return k_optimo

def ejecutar_modulo_mineria(n_clusters=None):
    """
    Si n_clusters es None, se calcula automáticamente con el método del codo.
    Si se especifica, se usa ese valor.
    """
    print("=" * 60)
    print("🎬 MÓDULO 4: APLICACIÓN DE TÉCNICAS DE MINERÍA DE DATOS")
    print("=" * 60)
    
    # 1. CARGA DEL DATASET OPTIMIZADO
    if not os.path.exists(PARQUET_LIMPIO):
        print(f"❌ Error: No se encontró el archivo '{PARQUET_LIMPIO}'. Ejecuta la Fase 3 primero.")
        return

    print(f"⏳ Cargando dataset optimizado Parquet...")
    df = pd.read_parquet(PARQUET_LIMPIO)
    print(f"📊 Registros listos para minería: {len(df):,}")

    # 2. SELECCIÓN DE CARACTERÍSTICAS
    features_monitoreo = ['baro_altitude', 'velocity_kmh', 'vertical_rate']
    print(f"⚙️ Seleccionando variables cinéticas: {features_monitoreo}")
    X = df[features_monitoreo].copy()

    # 3. ESCALAMIENTO
    print("⚖️ Aplicando Standard Scaler...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # 4. DETERMINAR K ÓPTIMO
    if n_clusters is None:
        print("🔍 Calculando K óptimo con el método del codo...")
        n_clusters = calcular_k_optimo_muestreado(df, features_monitoreo, sample_per_lote=2000)
    else:
        print(f"ℹ️ Usando K fijo: {n_clusters} (especificado por el usuario)")

    # 5. CLUSTERING CON K-MEANS
    print(f"🤖 Entrenando modelo K-Means con {n_clusters} clústeres...")
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df['cluster_vuelo'] = kmeans.fit_predict(X_scaled)  # Asignación directa

    # Mapeo de centroides
    centroides = scaler.inverse_transform(kmeans.cluster_centers_)
    print("\n📊 Análisis de Centroides Encontrados (Perfiles Promedio):")
    for i, centroide in enumerate(centroides):
        print(f"   🔹 Perfil {i}: Altitud: {centroide[0]:.2f}m | Velocidad: {centroide[1]:.2f} km/h | Tasa Vertical: {centroide[2]:.2f} m/s")

    # 6. DETECCIÓN DE ANOMALÍAS
    print("\n🌲 Entrenando Isolation Forest...")
    iso_forest = IsolationForest(contamination=0.01, random_state=42, n_jobs=-1)
    predicciones_anomalias = iso_forest.fit_predict(X_scaled)
    df['anomalia_score'] = predicciones_anomalias
    df['es_anomalia'] = np.where(df['anomalia_score'] == -1, True, False)

    num_anomalias = df['es_anomalia'].sum()
    print(f"⚠️ Detección completada: {num_anomalias:,} registros anómalos ({df['es_anomalia'].mean()*100:.2f}%)")

    # 7. GUARDAR RESULTADOS EN PARQUET
    print(f"\n💾 Guardando resultados en: '{PARQUET_MINERIA}'...")
    df.to_parquet(PARQUET_MINERIA, index=False)

    # 8. GUARDAR MÉTRICAS EN JSON
    metricas = {
        "total_registros_procesados": len(df),
        "n_clusters": n_clusters,
        "k_optimo_calculado": n_clusters,  # Para el frontend
        "centroides": [
            {
                "perfil": i,
                "altitud": float(centroides[i][0]),
                "velocidad": float(centroides[i][1]),
                "tasa_vertical": float(centroides[i][2])
            }
            for i in range(len(centroides))
        ],
        "anomalias_detectadas": int(num_anomalias),
        "porcentaje_anomalias": float(df['es_anomalia'].mean() * 100),
        "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    with open("mineria_resultados.json", "w") as f:
        json.dump(metricas, f, indent=2, default=str)

    print(f"\n📊 Métricas de minería guardadas en 'mineria_resultados.json'")
    print("-" * 60)
    print("✔️ ¡FASE 4 COMPLETADA CON ÉXITO!")
    print("   El dataset ahora cuenta con etiquetas predictivas listas para la interfaz web.")
    print("-" * 60)

    return df

if __name__ == "__main__":
    ejecutar_modulo_mineria()