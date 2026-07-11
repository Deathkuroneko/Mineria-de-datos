import time
import sys
import json
import os
from datetime import datetime
# Importamos los módulos anteriores asegurando la modularidad del software
try:
    from fase1_ingesta import ejecutar_recoleccion_masiva, CSV_OUTPUT
    from fase2_etl import ejecutar_modulo_etl, PARQUET_LIMPIO
except ImportError:
    print("⚠️ Alerta de estructura: Para correr el pipeline completo de forma modular,")
    print("se sugiere tener los códigos de Ingesta y ETL en el mismo directorio.")
    sys.exit(1)

def mostrar_cabecera_pipeline(horas, intervalo):
    print("=" * 70)
    print("🌐 UNIVERSIDAD CENTRAL DEL ECUADOR - FACULTAD DE INGENIERÍA")
    print("🚀 PIPELINE AUTOMATIZADO DE DATOS: OPENSKY NETWORK")
    print("=" * 70)
    print(f"⏱️  Configuración: Ejecución por {horas} horas | Intervalo: {intervalo}s")
    print(f"📅 Inicio de operación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

def guardar_metricas_pipeline(metricas):
    """Guarda las métricas en un archivo JSON."""
    try:
        with open("pipeline_metrics.json", "w") as f:
            json.dump(metricas, f, indent=2)
        print(f"\n📊 Métricas del pipeline guardadas en 'pipeline_metrics.json'")
    except Exception as e:
        print(f"⚠️ No se pudieron guardar las métricas: {e}")

def orquestar_pipeline_completo(horas_operacion=4, intervalo_muestreo=35):
    """
    Controla de extremo a extremo el flujo de datos del proyecto.
    """
    mostrar_cabecera_pipeline(horas_operacion, intervalo_muestreo)
    
    t_inicio_global = time.time()
    metricas = {
        "timestamp_inicio": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "horas_operacion": horas_operacion,
        "intervalo_muestreo": intervalo_muestreo
    }
    
    # -------------------------------------------------------------
    # PASO 1 Y 2 DEL PIPELINE: INGESTA CONTINUA (Extracción y Almacenamiento Raw)
    # -------------------------------------------------------------
    print("\n⚡ [FASE 1/2]: Activando Tubería de Ingesta Cruda a CSV...")
    metricas_ingesta = None
    ingesta_exitosa = False
    
    try:
        # Se invoca el Módulo 1 de forma controlada y se capturan las métricas
        metricas_ingesta = ejecutar_recoleccion_masiva(
            intervalo_segundos=intervalo_muestreo,
            horas_ejecucion=horas_operacion
        )
        # Verificar que el diccionario tenga las claves esperadas
        if metricas_ingesta and "total_registros" in metricas_ingesta:
            ingesta_exitosa = True
            metricas["ingesta"] = metricas_ingesta
            print(f"\n   ✅ Ingesta completada: {metricas_ingesta['total_registros']:,} registros en {metricas_ingesta['ciclos_ejecutados']} ciclos.")
        else:
            print("\n   ⚠️ La ingesta no retornó métricas válidas. Continuando con ETL...")
            metricas["ingesta"] = {"error": "No se obtuvieron métricas válidas"}
            
    except KeyboardInterrupt:
        print("\n🛑 Pipeline: Interrupción manual detectada (Ctrl+C).")
        print("   Iniciando protocolo de cierre seguro de flujos...")
        # Si la interrupción ocurrió durante la ingesta, podemos intentar capturar lo que haya
        if metricas_ingesta and "total_registros" in metricas_ingesta:
            ingesta_exitosa = True
            metricas["ingesta"] = metricas_ingesta
            print(f"   Se recuperaron {metricas_ingesta['total_registros']:,} registros antes de la interrupción.")
        else:
            metricas["ingesta"] = {"error": "Interrupción manual durante la ingesta"}
        
    except Exception as e:
        print(f"\n❌ Pipeline: Error crítico detectado en la tubería de ingesta: {e}")
        print("   Forzando paso a la fase de salvaguarda de datos...")
        metricas["ingesta"] = {"error": str(e)}

    # Si la ingesta no generó datos (archivo CSV vacío o no existe), no tiene sentido ejecutar ETL
    if not os.path.exists(CSV_OUTPUT):
        print(f"\n⚠️ El archivo CSV '{CSV_OUTPUT}' no existe. No se puede ejecutar ETL.")
        metricas["etl"] = {"error": "CSV no generado"}
        metricas["estado_general"] = "FALLIDO (sin datos)"
        guardar_metricas_pipeline(metricas)
        return

    # -------------------------------------------------------------
    # PASO 3 DEL PIPELINE: PROCESAMIENTO ETL AUTOMÁTICO (Transformación y Carga)
    # -------------------------------------------------------------
    print("\n⚡ [FASE 3/3]: Disparando Orquestador ETL y Conversión a Parquet...")
    t_inicio_etl = time.time()
    metricas_etl = None
    
    try:
        # Se invoca el Módulo 2 de limpieza y optimización estructural
        metricas_etl = ejecutar_modulo_etl()
        
        # Verificar si hubo error en el retorno
        if isinstance(metricas_etl, dict) and "error" in metricas_etl:
            print(f"❌ Error en ETL: {metricas_etl['error']}")
            metricas["etl"] = metricas_etl
            metricas["estado_general"] = "FALLIDO (ETL)"
            guardar_metricas_pipeline(metricas)
            return
        
        duracion_etl = time.time() - t_inicio_etl
        metricas["etl"] = metricas_etl
        metricas["etl"]["duracion_total_segundos"] = round(duracion_etl, 2)
        print(f"   Pipeline: Procesamiento ETL masivo completado en {duracion_etl:.2f} segundos.")
        
    except Exception as e:
        print(f"❌ Pipeline: Error fatal durante la automatización del proceso ETL: {e}")
        metricas["etl"] = {"error": str(e)}
        metricas["estado_general"] = "FALLIDO (ETL)"
        guardar_metricas_pipeline(metricas)
        return

    # -------------------------------------------------------------
    # MÉTRICAS DE RENDIMIENTO DEL PIPELINE (globales)
    # -------------------------------------------------------------
    duracion_total = (time.time() - t_inicio_global) / 60
    metricas["tiempo_total_minutos"] = round(duracion_total, 2)
    metricas["timestamp_fin"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Determinar estado general
    if "error" in metricas.get("ingesta", {}) or "error" in metricas.get("etl", {}):
        metricas["estado_general"] = "PARCIALMENTE EXITOSO"
    else:
        metricas["estado_general"] = "EXITOSO"
    
    # Guardar métricas consolidadas
    guardar_metricas_pipeline(metricas)
    
    # Mostrar resumen en consola
    print("\n" + "=" * 70)
    print("🏁 RESUMEN DE EJECUCIÓN DEL PIPELINE DE INGENIERÍA")
    print("=" * 70)
    print(f"✔️  Estado general: {metricas['estado_general']}")
    print(f"⏱️  Tiempo total de operación del Pipeline: {duracion_total:.2f} minutos")
    print(f"💾 Entregable Final Generado: {PARQUET_LIMPIO}")
    if metricas_etl:
        print(f"📊 Registros finales: {metricas_etl.get('registros_finales', 'N/A'):,}")
        print(f"📉 Reducción de almacenamiento: {metricas_etl.get('reduccion_porcentaje', 'N/A')}%")
    print("=" * 70)

if __name__ == "__main__":
    # Parámetros de control: puedes probar con 0.01 horas (aprox. 36 segundos) 
    # para verificar que el pipeline salte de forma automática al ETL.
    # Para producción o recolección real, súbelo a 4 o más horas.
    orquestar_pipeline_completo(horas_operacion=4, intervalo_muestreo=35)