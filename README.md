# ✈️ Proyecto: OpenSky Data Pipeline & Dashboard Analítico

**Diseño e Implementación de un Pipeline de Datos Escalable para la Clasificación Dinámica de Fases de Vuelo y Detección de Anomalías en el Espacio Aéreo Internacional Utilizando la API Abierta de OpenSky Network.**

---

## 1. Descripción General del Proyecto

Este proyecto consiste en un sistema integral de ingeniería de datos y *Machine Learning* no supervisado que captura, procesa, modela y visualiza en tiempo real el tráfico aéreo global. 
A través de un pipeline automatizado, el sistema clasifica las fases aerodinámicas de cada vuelo y aísla comportamientos anómalos o de riesgo sin necesidad de reglas manuales, presentando todos los hallazgos en un **Dashboard Interactivo** vía web.

## 2. Arquitectura y Fases del Pipeline

El sistema está diseñado de manera modular en 7 fases orquestadas por un script principal:

* **Orquestador Principal (`pipeline_principal.py`):** Ejecuta de forma secuencial todo el ciclo de vida del dato.
* **Fase 1 (Ingesta):** Conexión a la API de OpenSky y recolección masiva de telemetría en streaming a formato CSV.
* **Fase 2 (ETL):** Limpieza, depuración y conversión de los datos crudos a formato optimizado `.parquet`.
* **Fases 3 y 4 (Minería de Datos):** Entrenamiento e inferencia de algoritmos de Machine Learning (K-Means y Isolation Forest).
* **Fase 5 (Estadísticas por Lotes):** Agrupación y cálculo de indicadores métricos globales y por intervalos de captura.
* **Fase 6 (Pre-cálculo de Silueta):** Evaluación matemática (Silhouette Score) de la calidad de los clústeres generados.
* **Fase 7 (Pre-cálculo de Mapa de Calor):** Generación de matrices de correlación estáticas (Pearson) entre variables físicas.
* **Capa de Visualización (`Visualizacion/`):** Una API construida en **FastAPI** (`app_api.py`) expone los resultados precalculados hacia un front-end en **HTML/JS/CSS** potenciado con Leaflet y Chart.js.

---

## 3. Guía de Instalación y Ejecución (Windows PowerShell)

Sigue estos pasos para desplegar el proyecto localmente en un entorno Windows utilizando PowerShell.

### A. Preparación del Entorno
```powershell
# 1. Crear el entorno virtual
python -m venv .venv

# 2. Habilitar ejecución de scripts (si es necesario)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 3. Activar el entorno virtual
.venv\Scripts\Activate.ps1

# 4. Actualizar pip e instalar los requerimientos
python.exe -m pip install --upgrade pip
pip install -r requirements.txt
```

### B. Ejecución del Sistema
```powershell
# 1. Ejecutar el Pipeline Completo (Recolección y Procesamiento)
python pipeline_principal.py

# Nota: Opcionalmente puedes ejecutar fases individuales, por ejemplo el mapa de calor:
# python fase7_precalculo_mapa_calor.py

# 2. Iniciar el Servidor Backend (FastAPI)
cd Visualizacion
uvicorn app_api:app --reload

# 3. Visualizar el Dashboard
# Abre el archivo Visualizacion/index.html en tu navegador web de preferencia.
```

### C. Limpieza del Entorno (Opcional)
```powershell
# Para eliminar el entorno y cachés:
Remove-Item -Recurse -Force .venv, __pycache__
```

---

## 4. Algoritmos de Minería de Datos

Dado que los datos de vuelo en vivo no cuentan con etiquetas de la fase operativa (despegue, crucero, etc.), se implementaron técnicas avanzadas de **Aprendizaje No Supervisado**:

### A. Segmentación de Patrones Cinéticos (K-Means)
El algoritmo agrupa matemáticamente cada registro en *clusters* basados en la interacción de la velocidad horizontal (`velocity`), la altitud (`baro_altitude`) y la tasa vertical (`vertical_rate`). 
* **Objetivo:** Descubrir automáticamente las firmas físicas de un vuelo (Tierra/Rodaje, Crucero, Ascenso/Aproximación) mediante el cálculo del **K-Óptimo** (Método del Codo).

### B. Aislamiento de Comportamientos Atípicos (Isolation Forest)
Aísla las observaciones analizando qué tan anómalo o divergente es el comportamiento de una aeronave respecto al tráfico global.
* **Objetivo:** Detectar inconsistencias cinéticas graves o maniobras evasivas/erráticas de forma autónoma.

---

## 5. Descripción Anatómica del Dataset

Cada registro capturado de la red ADS-B representa el "vector de estado" de una aeronave en un momento exacto, agrupando variables en:

* **Identificadores Únicos y Origen:** `icao24` (ID hexadecimal único), `callsign` (código de llamada de la aerolínea) y `origin_country` (país de registro).
* **Variables Geoespaciales:** `longitude` y `latitude` (coordenadas GPS), `baro_altitude` (altitud barométrica).
* **Variables Dinámicas/Físicas:** `velocity` (velocidad horizontal en m/s), `true_track` (rumbo o dirección en grados angulares) y `vertical_rate` (tasa de ascenso/descenso en m/s).
* **Variable de Control Temporal:** `fecha_captura_sistema` (inyectada por el pipeline para gestionar la línea de tiempo por lotes).

---

## 6. Conclusiones y Valor Operativo

* **Auditoría Automatizada de Seguridad Aérea:** El pipeline demuestra ser capaz de detectar anomalías y emitir alertas tempranas de vuelos con parámetros fuera del marco operativo estándar sin intervención humana.
* **Caracterización Aerodinámica Dinámica:** La clusterización establece firmas numéricas precisas que definen el comportamiento de una aeronave de acuerdo a las fases lógicas del vuelo.
* **Análisis de Congestión Espacial:** Las herramientas de visualización permiten mapear las densidades geográficas del tráfico aéreo y detectar cuellos de botella del tránsito transcontinental, aportando un insumo de valor para la optimización de rutas globales.

---

## 7. Valor Estratégico y Aplicaciones Prácticas de los Datos

La información extraída, procesada y mostrada en este Dashboard representa un alto valor para múltiples sectores de la industria aeronáutica y logística. El acceso a estos *insights* analíticos permite:

### A. Para Autoridades de Control de Tráfico Aéreo (ATC)
* **Gestión de Crisis y Alertas Tempranas:** La identificación inmediata de anomalías cinéticas (vuelos con caídas de altitud abruptas o pérdidas de velocidad críticas) permite a los controladores priorizar aeronaves en riesgo proactivamente.
* **Optimización del Espacio Aéreo:** Entender las áreas de congestión (vistas en el mapa) y la distribución global de altitudes ayuda a la reasignación dinámica de corredores aéreos, evitando patrones de espera prolongados.

### B. Para Aerolíneas y Operadores Logísticos
* **Eficiencia de Combustible (Green Aviation):** Al analizar los perfiles de ascenso y descenso (descubiertos por K-Means), las aerolíneas pueden comparar la ejecución real de sus vuelos contra modelos teóricos para auditar si se están realizando aproximaciones eficientes (Continuous Descent Operations).
* **Inteligencia Operativa:** Conocer la cantidad exacta de aviones activos, países de origen y sus fases de vuelo permite a las empresas evaluar la saturación de rutas específicas en tiempo real.

### C. Para Aseguradoras, Gobiernos y Entidades de Investigación
* **Auditoría de Cumplimiento Ambiental y de Ruido:** Las firmas físicas generadas pueden ser utilizadas por autoridades locales para verificar que las aeronaves cumplan con normativas de altitud mínima sobre zonas urbanas pobladas.
* **Reconstrucción y Análisis Forense de Incidentes:** El almacenamiento persistente (vía `.parquet`) de la telemetría histórica detallada sirve como una "caja negra virtual" de respaldo para investigaciones sobre desviaciones de ruta o incidentes, cruzando la información con la matriz de correlaciones y el historial de anomalías.