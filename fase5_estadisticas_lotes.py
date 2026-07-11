import pandas as pd
import numpy as np
import os
import json

# --- CONFIGURACIÓN DE RUTAS ---
PARQUET_MINERIA = "opensky_resultados_mineria.parquet"
PARQUET_ESTADISTICAS_LOTES = "opensky_estadisticas_lotes.parquet"
PARQUET_ESTADISTICAS_GLOBALES = "opensky_estadisticas_globales.parquet"

# Leer K óptimo del JSON de minería
def get_k_optimo():
    try:
        with open("mineria_resultados.json", "r") as f:
            data = json.load(f)
            return int(data.get("n_clusters", 3))  # Convertir a int
    except:
        return 3

K_CLUSTERS = get_k_optimo()

def calcular_estadisticas_lotes():
    """
    Calcula estadísticas agregadas por lote (fecha_captura_sistema)
    y guarda un Parquet con una fila por lote.
    """
    print("=" * 60)
    print("🎬 FASE 5: PRECÁLCULO DE ESTADÍSTICAS POR LOTE")
    print("=" * 60)
    
    # 1. Cargar dataset de minería
    if not os.path.exists(PARQUET_MINERIA):
        print(f"❌ Error: No se encontró '{PARQUET_MINERIA}'. Ejecuta la Fase 4 primero.")
        return
    
    print(f"⏳ Cargando '{PARQUET_MINERIA}'...")
    df = pd.read_parquet(PARQUET_MINERIA)
    print(f"📊 Registros totales: {len(df):,}")
    
    # 2. Obtener lista de fechas únicas
    fechas = df['fecha_captura_sistema'].unique()
    print(f"📅 Se detectaron {len(fechas)} lotes únicos.")
    
    # 3. Calcular estadísticas por lote
    registros = []
    for i, fecha in enumerate(fechas):
        if i % 10 == 0:
            print(f"   Procesando lote {i+1}/{len(fechas)}...")
        
        df_lote = df[df['fecha_captura_sistema'] == fecha]
        
        # Total de aeronaves únicas (por ICAO24)
        total_aviones = df_lote['icao24'].nunique()
        
        # Anomalías
        anomalias = df_lote['es_anomalia'].sum() if 'es_anomalia' in df_lote.columns else 0
        porcentaje_anomalias = (anomalias / total_aviones * 100) if total_aviones > 0 else 0
        
        # Estadísticas de velocidad (km/h)
        velocidad = df_lote['velocity_kmh'].dropna()
        vel_media = float(velocidad.mean()) if len(velocidad) > 0 else 0
        vel_std = float(velocidad.std()) if len(velocidad) > 0 else 0
        vel_min = float(velocidad.min()) if len(velocidad) > 0 else 0
        vel_max = float(velocidad.max()) if len(velocidad) > 0 else 0
        
        # Estadísticas de altitud (m)
        altitud = df_lote['baro_altitude'].dropna()
        alt_media = float(altitud.mean()) if len(altitud) > 0 else 0
        alt_std = float(altitud.std()) if len(altitud) > 0 else 0
        alt_min = float(altitud.min()) if len(altitud) > 0 else 0
        alt_max = float(altitud.max()) if len(altitud) > 0 else 0
        
        # Tasa vertical (m/s)
        tv = df_lote['vertical_rate'].dropna()
        tv_media = float(tv.mean()) if len(tv) > 0 else 0
        tv_std = float(tv.std()) if len(tv) > 0 else 0
        
        # Distribución de clústeres (como dict)
        cluster_counts = {}
        if 'cluster_vuelo' in df_lote.columns:
            counts = df_lote['cluster_vuelo'].value_counts()
            for k, v in counts.items():
                cluster_counts[int(k)] = int(v)
        # Asegurar que los clústeres estén presentes
        for c in range(K_CLUSTERS):
            if c not in cluster_counts:
                cluster_counts[c] = 0
        
        # Top países
        top_paises = {}
        if 'origin_country' in df_lote.columns:
            paises = df_lote['origin_country'].value_counts().head(3).to_dict()
            for pais, count in paises.items():
                top_paises[str(pais)] = int(count)
        
        # Aeronaves en tierra
        en_tierra = df_lote[df_lote['on_ground'] == True].shape[0] if 'on_ground' in df_lote.columns else 0
        
        # Guardar registro
        registros.append({
            'fecha_lote': str(fecha),
            'total_aviones': total_aviones,
            'anomalias': int(anomalias),
            'porcentaje_anomalias': round(porcentaje_anomalias, 2),
            'velocidad_media': round(vel_media, 2),
            'velocidad_std': round(vel_std, 2),
            'velocidad_min': round(vel_min, 2),
            'velocidad_max': round(vel_max, 2),
            'altitud_media': round(alt_media, 2),
            'altitud_std': round(alt_std, 2),
            'altitud_min': round(alt_min, 2),
            'altitud_max': round(alt_max, 2),
            'tv_media': round(tv_media, 2),
            'tv_std': round(tv_std, 2),
            'cluster_distribucion': json.dumps(cluster_counts),
            'top_paises': json.dumps(top_paises),
            'en_tierra': int(en_tierra)
        })
    
    # 4. Crear DataFrame y guardar
    df_estadisticas = pd.DataFrame(registros)
    print(f"\n💾 Guardando estadísticas por lote en '{PARQUET_ESTADISTICAS_LOTES}'...")
    df_estadisticas.to_parquet(PARQUET_ESTADISTICAS_LOTES, index=False)
    print(f"✅ {len(df_estadisticas)} lotes procesados.")
    
    # 5. Calcular estadísticas globales (todo el dataset)
    print("\n📊 Calculando estadísticas globales...")
    global_stats = {
        'total_registros': len(df),
        'total_lotes': len(fechas),
        'total_aviones_unicos': df['icao24'].nunique(),
        'total_anomalias': df['es_anomalia'].sum() if 'es_anomalia' in df.columns else 0,
        'velocidad_global_media': df['velocity_kmh'].mean(),
        'altitud_global_media': df['baro_altitude'].mean(),
        'tv_global_media': df['vertical_rate'].mean(),
        # Distribución global de clústeres
        'cluster_global': json.dumps(df['cluster_vuelo'].value_counts().to_dict()) if 'cluster_vuelo' in df.columns else '{}'
    }
    df_global = pd.DataFrame([global_stats])
    print(f"💾 Guardando estadísticas globales en '{PARQUET_ESTADISTICAS_GLOBALES}'...")
    df_global.to_parquet(PARQUET_ESTADISTICAS_GLOBALES, index=False)
    
    print("-" * 60)
    print("✔️ ¡FASE 5 COMPLETADA CON ÉXITO!")
    print(f"   Estadísticas por lote: {PARQUET_ESTADISTICAS_LOTES}")
    print(f"   Estadísticas globales: {PARQUET_ESTADISTICAS_GLOBALES}")
    print("-" * 60)

if __name__ == "__main__":
    calcular_estadisticas_lotes()