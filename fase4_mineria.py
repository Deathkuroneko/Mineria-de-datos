import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
import os

# --- CONFIGURACIÓN DE RUTAS ---
PARQUET_LIMPIO = "opensky_datos_optimizados.parquet"
PARQUET_MINERIA = "opensky_resultados_mineria.parquet"

def ejecutar_modulo_mineria(n_clusters=3):
    print("=" * 60)
    print("🎬 MÓDULO 4: APLICACIÓN DE TÉCNICAS DE MINERÍA DE DATOS")
    print("=" * 60)
    
    # 1. CARGA DEL DATASET OPTIMIZADO
    if not os.path.exists(PARQUET_LIMPIO):
        print(f"❌ Error: No se encontró el archivo '{PARQUET_LIMPIO}'. Executa la Fase 3 primero.")
        return

    print(f"⏳ Cargando dataset optimizado Parquet...")
    df = pd.read_parquet(PARQUET_LIMPIO)
    print(f"📊 Registros listos para minería: {len(df):,}")

    # 2. SELECCIÓN DE CARACTERÍSTICAS (Feature Selection)
    # Seleccionamos las variables físicas/dinámicas determinantes para el vuelo
    features_monitoreo = ['baro_altitude', 'velocity_kmh', 'vertical_rate']
    
    print(f"⚙️ Seleccionando variables cinéticas para los modelos: {features_monitoreo}")
    X = df[features_monitoreo].copy()

    # 3. ESCALAMIENTO DE DATOS (Normalización Z-Score)
    # K-Means calcula distancias euclidianas. Si la altitud varía entre 0 y 12000, 
    # y la tasa vertical entre -10 y 10, la altitud dominaría el algoritmo. Reducimos todo a la misma escala.
    print("⚖️ Aplicando Standard Scaler (Normalización de magnitudes)...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # 4. ALGORITMO A: CLUSTERING CON K-MEANS
    print(f"🤖 Entrenando modelo K-Means (Búsqueda de {n_clusters} perfiles de vuelo)...")
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df['cluster_vuelo'] = kmeans.fit_transform(X_scaled).argmin(axis=1) # Asignación de clústeres

    # Mapeo interpretativo de los clústeres basado en los centroides obtenidos
    centroides = scaler.inverse_transform(kmeans.cluster_centers_)
    print("\n📊 Análisis de Centroides Encontrados (Perfiles Promedio):")
    for i, centroide in enumerate(centroides):
        print(f"   🔹 Perfil {i}: Altitud: {centroide[0]:.2f}m | Velocidad: {centroide[1]:.2f} km/h | Tasa Vertical: {centroide[2]:.2f} m/s")

    # 5. ALGORITMO B: DETECCIÓN DE ANOMALÍAS CON ISOLATION FOREST
    # contamination=0.01 significa que esperamos que de forma natural el 1% de los datos sean anomalías
    print("\n🌲 Entrenando modelo Isolation Forest para detección de vuelos atípicos...")
    iso_forest = IsolationForest(contamination=0.01, random_state=42, n_jobs=-1)
    
    # El modelo retorna 1 para datos normales y -1 para anomalías
    predicciones_anomalias = iso_forest.fit_predict(X_scaled)
    df['anomalia_score'] = predicciones_anomalias
    df['es_anomalia'] = np.where(df['anomalia_score'] == -1, True, False)

    num_anomalias = df['es_anomalia'].sum()
    print(f"⚠️ Detección completada: Se aislaron {num_anomalias:,} registros anómalos ({df['es_anomalia'].mean()*100:.2f}% del espacio aéreo).")

    # 6. EXPORTACIÓN DEL DATASET MINADO CON LAS NUEVAS ETIQUETAS
    print(f"\n💾 Guardando resultados enriquecidos en: '{PARQUET_MINERIA}'...")
    df.to_parquet(PARQUET_MINERIA, index=False)
    
    print("-" * 60)
    print("✔️ ¡FASE 4 COMPLETADA CON ÉXITO!")
    print("   El dataset ahora cuenta con etiquetas predictivas listas para la interfaz web.")
    print("-" * 60)
    
    return df

if __name__ == "__main__":
    ejecutar_modulo_mineria()