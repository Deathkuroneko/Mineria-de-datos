import requests
import pandas as pd
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import os
import csv

TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
CLIENT_ID = "ekkd-api-client"
CLIENT_SECRET = "0hxu5eVaza4rmdimK79qXdKbwzIwtUtH"
TOKEN_REFRESH_MARGIN = 30

CSV_OUTPUT = "opensky_datos_masivos.csv"

COLUMNAS = [
    "icao24", "callsign", "origin_country", "time_position", 
    "last_contact", "longitude", "latitude", "baro_altitude", 
    "on_ground", "velocity", "true_track", "vertical_rate", 
    "sensors", "geo_altitude", "squawk", "spi", "position_source",
    "fecha_captura_sistema"
]

class TokenManager:
    """
    Gestiona la obtención y actualización del token de acceso para la API de OpenSky.
    """
    def __init__(self):
        self.token = None
        self.expires_at = None
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        self.session.mount('https://', HTTPAdapter(max_retries=retries))

    def get_token(self):
        if self.token and self.expires_at and datetime.now() < self.expires_at:
            return self.token
        return self._refresh()

    def _refresh(self):
        try:
            r = self.session.post(
                TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                },
                timeout=10
            )
            r.raise_for_status()
            data = r.json()
            self.token = data["access_token"]
            expires_in = data.get("expires_in", 1800)
            self.expires_at = datetime.now() + timedelta(seconds=expires_in - TOKEN_REFRESH_MARGIN)
            print("\n[TOKEN] Token de acceso de OpenSky actualizado con éxito.")
            return self.token
        except requests.exceptions.RequestException as e:
            print(f"\n[ERROR TOKEN] Error al obtener/refrescar el token: {e}")
            self.token = None
            self.expires_at = None
            raise

    def headers(self):
        return {"Authorization": f"Bearer {self.get_token()}"}


def inicializar_archivo_csv():
    """
    Crea el archivo CSV de salida y escribe las cabeceras si este no existe.
    """
    if not os.path.exists(CSV_OUTPUT):
        with open(CSV_OUTPUT, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(COLUMNAS)
        print(f"📁 Archivo '{CSV_OUTPUT}' creado e inicializado con cabeceras.")
    else:
        print(f"📂 El archivo '{CSV_OUTPUT}' ya existe. Los nuevos datos se anexarán al final.")

def guardar_lote_en_csv(vectores_aviones):
    """
    Añade un lote de registros de aviones al archivo CSV de salida.
    """
    timestamp_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(CSV_OUTPUT, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for avion in vectores_aviones:
            if len(avion) < 17:
                avion = list(avion) + [None] * (17 - len(avion))
            fila_final = list(avion[:17]) + [timestamp_actual]
            writer.writerow(fila_final)

session_api = requests.Session()
retries_api = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
session_api.mount('https://', HTTPAdapter(max_retries=retries_api))
tokens = TokenManager()

def ejecutar_recoleccion_masiva(intervalo_segundos=35, horas_ejecucion=4):
    """
    Ejecuta el proceso de recolección de datos de manera cíclica y almacena los resultados en disco.
    Retorna un diccionario que contiene las métricas del proceso de recolección.
    """
    inicializar_archivo_csv()
    
    ciclos_totales = int((horas_ejecucion * 3600) / intervalo_segundos)
    total_registros_guardados = 0
    ciclos_ejecutados = 0
    t_inicio_general = time.time()
    
    print(f"\n🚀 Iniciando tubería de recolección masiva por {horas_ejecucion} horas.")
    print("Presiona Ctrl+C en cualquier momento para detener el script de forma segura.\n")
    print("-" * 80)

    try:
        for ciclo in range(1, ciclos_totales + 1):
            t_inicio = time.time()
            hora_log = datetime.now().strftime("%H:%M:%S")
            
            try:
                response = session_api.get(
                    "https://opensky-network.org/api/states/all",
                    headers=tokens.headers(),
                    timeout=30
                )
                response.raise_for_status()
                datos_json = response.json()
                
                if 'states' in datos_json and datos_json['states'] is not None:
                    vectores_aviones = datos_json['states']
                    num_aviones = len(vectores_aviones)
                    guardar_lote_en_csv(vectores_aviones)
                    total_registros_guardados += num_aviones
                    ciclos_ejecutados += 1
                    print(f"[{hora_log}] Lote {ciclo}/{ciclos_totales} -> Guardados {num_aviones} registros. (Total acumulado: {total_registros_guardados:,})")
                else:
                    print(f"[{hora_log}] Lote {ciclo} -> Respuesta de la API vacía.")
                    
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    print(f"⚠️ [{hora_log}] Lote {ciclo} -> Límite de tasa excedido (429). Esperando un minuto extra...")
                    time.sleep(60)
                else:
                    print(f"❌ [{hora_log}] Lote {ciclo} -> Error HTTP ({e.response.status_code})")
            except Exception as e:
                print(f"❌ [{hora_log}] Lote {ciclo} -> Error imprevisto: {e}")
                
            duracion_peticion = time.time() - t_inicio
            tiempo_espera_real = max(1, intervalo_segundos - duracion_peticion)
            time.sleep(tiempo_espera_real)

    except KeyboardInterrupt:
        print("\n🛑 Recolección interrumpida manualmente. Guardando datos acumulados...")

    tiempo_total = time.time() - t_inicio_general
    print(f"\n📊 Resumen de ingesta: {ciclos_ejecutados} ciclos ejecutados, {total_registros_guardados:,} registros guardados.")
    print(f"⏱️ Tiempo de ejecución: {tiempo_total/60:.2f} minutos")

    return {
        "total_registros": total_registros_guardados,
        "ciclos_ejecutados": ciclos_ejecutados,
        "ciclos_totales": ciclos_totales,
        "tiempo_ejecucion_segundos": round(tiempo_total, 2),
        "archivo_csv": CSV_OUTPUT
    }

if __name__ == "__main__":
    try:
        resultado = ejecutar_recoleccion_masiva(intervalo_segundos=35, horas_ejecucion=4)
        print("\n✅ Ingesta finalizada correctamente.")
    except KeyboardInterrupt:
        print("\n🛑 Proceso detenido manualmente. El archivo CSV está a salvo.")