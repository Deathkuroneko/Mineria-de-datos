import pandas as pd
import os

# --- CONFIGURACIÓN DE RUTAS ---
CSV_CRUDO = "opensky_datos_masivos.csv"
PARQUET_LIMPIO = "opensky_datos_optimizados.parquet"

def ejecutar_modulo_etl():
    print("=" * 60)
    print("🎬 MÓDULO 2: PREPARACIÓN DE DATOS (ETL) Y EXPORTACIÓN A PARQUET")
    print("=" * 60)
    
    # 1. VERIFICACIÓN Y LECTURA (E de Extract)
    if not os.path.exists(CSV_CRUDO):
        print(f"❌ Error: No se encontró el archivo '{CSV_CRUDO}'.")
        print("Asegúrate de ejecutar primero el Módulo 1 de recolección de datos.")
        return
        
    print(f"⏳ Leyendo datos crudos desde '{CSV_CRUDO}'...")
    df = pd.read_csv(CSV_CRUDO)
    print(f"📊 Registros iniciales detectados: {len(df):,}")

    # 2. LIMPIEZA Y TRANSFORMACIÓN (T de Transform)
    print("\n🧹 Aplicando reglas de negocio y limpieza...")
    
    # A. Eliminar duplicados de transpondedor en el mismo segundo
    df.drop_duplicates(subset=['icao24', 'time_position'], inplace=True)
    
    # B. Filtrar filas sin geolocalización o velocidad (esenciales para los algoritmos)
    df.dropna(subset=['longitude', 'latitude', 'velocity'], inplace=True)
    
    # C. Imputación/Relleno de valores nulos secundarios
    df['vertical_rate'] = df['vertical_rate'].fillna(0.0)
    df['baro_altitude'] = df['baro_altitude'].fillna(0.0)
    df['geo_altitude'] = df['geo_altitude'].fillna(df['baro_altitude']) # Fallback a altitud barométrica
    
    # D. Normalización de cadenas de texto
    df['callsign'] = df['callsign'].astype(str).str.strip().replace(['nan', ''], 'UNKNOWN')

    # E. Ingeniería de Características (Nuevas variables para la interfaz y minería)
    print("⚙️ Generando métricas derivadas (Feature Engineering)...")
    df['velocity_kmh'] = df['velocity'] * 3.6  # Conversión útil para visualización

    # 3. CARGA AUTOMATIZADA A PARQUET (L de Load)
    print(f"\n💾 Guardando dataset optimizado en binario columnar: '{PARQUET_LIMPIO}'...")
    
    # Guardamos en Parquet usando compresión Snappy (rápida y ligera)
    df.to_parquet(PARQUET_LIMPIO, index=False, compression='snappy')
    
    # --- MÉTRICAS DE VALIDACIÓN PARA TU INFORME ---
    tamano_csv = os.path.getsize(CSV_CRUDO) / (1024 * 1024)
    tamano_parquet = os.path.getsize(PARQUET_LIMPIO) / (1024 * 1024)
    
    print("-" * 60)
    print("✔️ ¡FASE 2 COMPLETADA CON ÉXITO!")
    print(f"📊 Filas finales listas para Minería/Dashboard: {len(df):,}")
    print(f"📉 Peso del CSV Crudo: {tamano_csv:.2f} MB")
    print(f"⚡ Peso del Parquet Limpio: {tamano_parquet:.2f} MB")
    print(f"📉 Reducción de almacenamiento: {((1 - tamano_parquet/tamano_csv) * 100):.1f}% menos espacio en disco.")
    print("-" * 60)

if __name__ == "__main__":
    ejecutar_modulo_etl()