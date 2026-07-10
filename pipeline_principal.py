import time
import sys
from datetime import datetime
# Importamos los módulos anteriores asegurando la modularidad del software
# Nota: Asegúrate de que tus scripts de Fase 1 y Fase 2 estén en la misma carpeta
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

def orquestar_pipeline_completo(horas_operacion=4, intervalo_muestreo=35):
    """
    Controla de extremo a extremo el flujo de datos del proyecto.
    """
    mostrar_cabecera_pipeline(horas_operacion, intervalo_muestreo)
    
    t_inicio_global = time.time()
    
    # -------------------------------------------------------------
    # PASO 1 Y 2 DEL PIPELINE: INGESTA CONTINUA (Extracción y Almacenamiento Raw)
    # -------------------------------------------------------------
    print("\n⚡ [FASE 1/2]: Activando Tubería de Ingesta Cruda a CSV...")
    try:
        # Se invoca el Módulo 1 de forma controlada
        ejecutar_recoleccion_masiva(intervalo_segundos=intervalo_muestreo, horas_ejecucion=horas_operacion)
        print("\n   Pipeline: Ingesta temporal finalizada por cumplimiento de cronograma.")
        
    except KeyboardInterrupt:
        print("\n🛑 Pipeline: Interrupción manual detectada (Ctrl+C).")
        print("   Iniciando protocolo de cierre seguro de flujos...")
        
    except Exception as e:
        print(f"\n❌ Pipeline: Error crítico detectado en la tubería de ingesta: {e}")
        print("   Forzando paso a la fase de salvaguarda de datos...")

    # -------------------------------------------------------------
    # PASO 3 DEL PIPELINE: PROCESAMIENTO ETL AUTOMÁTICO (Transformación y Carga)
    # -------------------------------------------------------------
    print("\n⚡ [FASE 3/3]: Disparando Orquestador ETL y Conversión a Parquet...")
    t_inicio_etl = time.time()
    
    try:
        # Se invoca el Módulo 2 de limpieza y optimización estructural
        ejecutar_modulo_etl()
        duracion_etl = time.time() - t_inicio_etl
        print(f"   Pipeline: Procesamiento ETL masivo completado en {duracion_etl:.2f} segundos.")
        
    except Exception as e:
        print(f"❌ Pipeline: Error fatal durante la automatización del proceso ETL: {e}")
        return

    # -------------------------------------------------------------
    # MÉTRICAS DE RENDIMIENTO DEL PIPELINE
    # -------------------------------------------------------------
    duracion_total = (time.time() - t_inicio_global) / 60
    print("\n" + "=" * 70)
    print("🏁 RESUMEN DE EJECUCIÓN DEL PIPELINE DE INGENIERÍA")
    print("=" * 70)
    print(f"✔️  Estado general: EXITOSO")
    print(f"⏱️  Tiempo total de operación del Pipeline: {duracion_total:.2f} minutos")
    print(f"💾 Entregable Final Generado: {PARQUET_LIMPIO}")
    print("=" * 70)

if __name__ == "__main__":
    # Parámetros de control: puedes probar con 0.01 horas (aprox. 36 segundos) 
    # para verificar que el pipeline salte de forma automática al ETL.
    # Para producción o recolección real, súbelo a 4 o más horas.
    orquestar_pipeline_completo(horas_operacion=0.02, intervalo_muestreo=35)