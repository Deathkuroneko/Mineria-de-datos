import pandas as pd
import numpy as np
import os
import seaborn as sns
import matplotlib.pyplot as plt
import io
import base64
import json

PARQUET_RESULTADOS = "opensky_resultados_mineria.parquet"
OUTPUT_JSON = "Visualizacion\mapa_calor_estatico.json"

def generar_mapa_calor_estatico(sample_per_lote=2000):
    """
    Genera un mapa de calor estático de correlación de variables utilizando una muestra estratificada.
    Retorna un diccionario con la imagen codificada en base64 y metadatos, almacenándolo en un archivo JSON.
    """
    print("📊 Generando mapa de calor estático con muestreo estratificado...")
    
    df = pd.read_parquet(PARQUET_RESULTADOS)
    print(f"   Registros totales: {len(df):,}")
    
    fechas = df['fecha_captura_sistema'].unique()
    muestras = []
    for fecha in fechas:
        df_lote = df[df['fecha_captura_sistema'] == fecha]
        if len(df_lote) > sample_per_lote:
            df_lote = df_lote.sample(n=sample_per_lote, random_state=42)
        muestras.append(df_lote)
    df_muestra = pd.concat(muestras, ignore_index=True)
    print(f"   Muestra total: {len(df_muestra):,} registros ({len(fechas)} lotes)")
    
    cols = ['velocity_kmh', 'baro_altitude', 'vertical_rate']
    df_corr = df_muestra[cols].dropna()
    corr = df_corr.corr()
    
    plt.figure(figsize=(8, 6))
    sns.heatmap(corr, annot=True, cmap='coolwarm', fmt='.2f', linewidths=0.5)
    plt.title('Mapa de calor de correlación (muestra estratificada global)')
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    buf.seek(0)
    plt.close()
    encoded = base64.b64encode(buf.read()).decode('utf-8')
    
    data = {
        "imagen": encoded,
        "fecha_generacion": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "muestras": len(df_muestra),
        "variables": cols
    }
    with open(OUTPUT_JSON, "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Mapa de calor guardado en '{OUTPUT_JSON}'")
    return data

if __name__ == "__main__":
    generar_mapa_calor_estatico(sample_per_lote=2000)