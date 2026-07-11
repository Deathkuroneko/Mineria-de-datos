## INSTALACION DE ENTORNO (POWERSHELL)
**Crear entorno**
python -m venv .venv
**Para ejecutar Script**
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
**Activar entorno**
.venv\Scripts\Activate.ps1
**Instalar Requerimientos**
python.exe -m pip install --upgrade pip
pip install -r requirements.txt
**Ejecutar el Script desde Visualizacion**
python test.py
**Abrir el index en un navegador**
index.html

**Borrar entorno**
Remove-Item -Recurse -Force .venv, __pycache__
----
Datos del mapa de calor

python .\fase7_precalculo_mapa_calor.py
📊 Generando mapa de calor estático con muestreo estratificado...
   Registros totales: 5,628,989
   Muestra total: 1,252,000 registros (626 lotes)
✅ Mapa de calor guardado en 'Visualizacion\mapa_calor_estatico.json'

----


# PROPUESTA DE PROYECTO DE INVESTIGACIÓN Y MINERÍA DE DATOS

## 1. TÍTULO DEL PROYECTO

**Diseño e Implementación de un Pipeline de Datos Escalable para la Clasificación Dinámica de Fases de Vuelo y Detección de Anomalías en el Espacio Aéreo Internacional Utilizando la API Abierta de OpenSky Network.**

---

## 2. ANTECEDENTES Y JUSTIFICACIÓN DEL DATASET

El monitoreo del tránsito aéreo global genera flujos masivos de datos geoespaciales y físicos por segundo. Tradicionalmente, la auditoría de estos datos dependía de umbrales rígidos o de la revisión manual de analistas de control de tráfico.

La elección de la API de **OpenSky Network** se justifica bajo tres pilares de la Ingeniería de Sistemas:

1. **Volumen y Escala Real:** Permite la recolección de millones de registros capturados por receptores ADS-B distribuidos por todo el planeta, ofreciendo un escenario real de *Big Data* idóneo para el entorno de desarrollo.
2. **Naturaleza Multidimensional:** Combina variables categóricas, espaciales y físicas que interactúan entre sí de forma compleja, lo que impide el análisis mediante software estadístico convencional y exige el uso de algoritmos avanzados de Machine Learning.
3. **Dinámica de Tiempo Real:** El dataset documenta la física del vuelo en intervalos continuos, permitiendo evaluar la resiliencia y escalabilidad de la arquitectura de software implementada (Pipeline e ingesta en *streaming* a disco).

---

## 3. DESCRIPCIÓN ANATÓMICA DEL DATASET (¿De qué va la información extraída?)

Cada registro capturado en el archivo CSV consolidado representa el "vector de estado" de una aeronave en un instante de tiempo específico. Los datos se agrupan en tres categorías analíticas esenciales:

* **Identificadores Únicos y Origen:** `icao24` (ID único de la aeronave en hexadecimal), `callsign` (código de llamada del vuelo, ej. AVA012), y `origin_country` (país de registro de la aeronave o de la estación base).
* **Variables Geoespaciales:** `longitude` (longitud), `latitude` (latitud), `baro_altitude` (altitud barométrica en metros) y `geo_altitude` (altitud geométrica dada por GPS).
* **Variables Dinámicas/Físicas:** `velocity` (velocidad horizontal en m/s), `true_track` (rumbo o dirección en grados angulares con respecto al norte), `vertical_rate` (velocidad de ascenso o descenso en m/s), y `on_ground` (bandera booleana que indica si el avión se encuentra en pista).
* **Variable de Control Temporal:** `fecha_captura_sistema` (métrica inyectada por nuestro pipeline para auditoría cronológica).

---

## 4. ALGORITMOS DE MINERÍA DE DATOS A APLICAR (ETAPA 4)

Para extraer el conocimiento oculto en los millones de filas, se seleccionaron dos técnicas de aprendizaje no supervisado debido a que los datos no vienen etiquetados de origen:

### A. Segmentación de Patrones Cinéticos (Clustering con K-Means)

El algoritmo agrupará de manera matemática las filas del dataset en cúmulos (*clusters*) basados puramente en la correlación entre `velocity`, `baro_altitude`, `vertical_rate` y `on_ground`.

* **Justificación:** Permitirá descubrir las firmas físicas abstractas de un vuelo sin mapear reglas manuales, separando dinámicamente las fases de crucero, aproximación, maniobra de despegue y rodaje en pista.

### B. Aislamiento de Comportamientos Atípicos (Detección de Anomalías con Isolation Forest)

Este algoritmo aísla observaciones basándose en qué tan rápido se separan del comportamiento de la masa de datos.

* **Justificación:** Evaluará de forma simultánea si un vector de vuelo presenta inconsistencias físicas graves (como variaciones extremas de la tasa vertical a baja altura o rumbos erráticos).

---

## 5. JUSTIFICACIÓN OPERATIVA Y CONCLUSIONES RELEVANTES A OBTENER (¿Qué se va a conseguir al finalizar?)

La implementación de los algoritmos de minería de datos permitirá extraer conclusiones de alto valor estratégico y operativo que justifican plenamente el proyecto:

### 1. Auditoría Automatizada de Seguridad Aérea (Detección de Anomalías)

* **Resultado Extraído:** El algoritmo identificará aeronaves con comportamientos cinéticos peligrosos o atípicos (por ejemplo, descensos extremadamente pronunciados `vertical_rate < -15 m/s` en zonas de baja altitud).
* **Conclusión/Impacto:** Se demuestra la viabilidad de construir sistemas de alerta temprana autónomos capaces de notificar incidentes o maniobras de emergencia en el espacio aéreo sin intervención humana directa.

### 2. Caracterización Automática del Comportamiento Aerodinámico (Clustering)

* **Resultado Extraído:** Al concluir el particionamiento de K-Means, el sistema perfilará los límites numéricos exactos que definen el comportamiento de una aeronave comercial promedio.
* **Conclusión/Impacto:** Permite establecer "huellas operativas estándar" por aerolínea o país. Si un cluster mezcla aviones comerciales con aviación ligera de manera errónea, el modelo revelará ineficiencias en la asignación de corredores aéreos.

### 3. Descubrimiento de Inconsistencias de Instrumentación (ETL Crosstabs)

* **Resultado Extraído:** El análisis comparativo de la brecha entre `baro_altitude` (presión de aire) y `geo_altitude` (sensores satelitales) en millones de datos.
* **Conclusión/Impacto:** Permite identificar zonas geográficas específicas del planeta donde los radares terrestres sufren distorsiones climáticas u obsolescencia tecnológica, sirviendo como insumo para auditorías de infraestructura de telecomunicaciones aéreas.

### 4. Mapeo de Densidad de Tráfico e Identificación de Saturation Points

* **Resultado Extraído:** Al agrupar las coordenadas espaciales (`latitude`, `longitude`) cruzadas con el tiempo de captura.
* **Conclusión/Impacto:** Se logrará concluir de manera cuantitativa cuáles son las horas pico reales del tráfico transcontinental y qué países actúan como los mayores cuellos de botella del tránsito global, optimizando la planificación de rutas para reducir el consumo de combustible a nivel macro.

---

## 6. CRONOGRAMA TÉCNICO DE IMPLEMENTACIÓN (Flujo en Google Colab / VS Code)

1. **Fase 1: Ingesta** -> Ejecución del script OAuth2 en streaming masivo anexando lotes al disco duro (CSV).
2. **Fase 2: ETL** -> Carga del archivo CSV gigante a un DataFrame, eliminación de ruido (duplicados de transpondedor, nulos espaciales) e ingeniería de características (conversión de m/s a nudos/kmh).
3. **Fase 3: Modelamiento** -> Entrenamiento de los algoritmos de Scikit-Learn sobre la infraestructura local o escalada a Colab utilizando GPUs/TPUs si el dataset supera los millones de filas.
4. **Fase 4: Visualización** -> Renderizado de mapas de dispersión geográfica e histogramas de clusters para la sustentación final ante el tribunal docente.