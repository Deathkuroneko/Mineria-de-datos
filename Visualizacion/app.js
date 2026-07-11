// ======================================================================
// 1. INICIALIZAR EL MAPA GLOBAL
// ======================================================================
const mapa = L.map('mapa').setView([20.0, -10.0], 2);
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap &copy; CARTO'
}).addTo(mapa);

let capaAviones = L.layerGroup().addTo(mapa);

// Variables Globales de Simulación por Lotes del Sistema
let baseDeDatosCompleta = [];
let listaFechasUnicas = [];
let indiceCronogramaActual = 0;
let ultimoLoteSilhouette = null;
let ultimoLoteScatter = null;
let ultimoLoteEstadisticas = null;
let datosEvolucionCompleta = [];
const VENTANA_LOTES = 6;
let ultimoLoteMapaCalor = null;

// 🔥 OPTIMIZACIÓN 1: Map para acceso rápido por fecha
let baseDatosPorFecha = new Map();

// Registrar el plugin de anotación (después de cargar Chart.js y el plugin)
if (typeof ChartAnnotation !== 'undefined') {
    Chart.register(ChartAnnotation);
}

// ======================================================================
// 2. INICIALIZAR LOS GRÁFICOS CON CHART.JS
// ======================================================================

// Gráfico A: Distribución de Clústeres (K-Means)
const ctxKMeans = document.getElementById('chartKmeans').getContext('2d');
const graficoKMeans = new Chart(ctxKMeans, {
    type: 'bar',
    data: {
        labels: ['Perfil 0 (Tierra / Rodaje)', 'Perfil 1 (Crucero)', 'Perfil 2 (Ascenso / Aproximación)'],
        datasets: [{
            label: 'Cantidad de Aeronaves Activas',
            data: [0, 0, 0],
            backgroundColor: ['#38bdf8', '#a855f7', '#eab308'],
            borderWidth: 0
        }]
    },
    options: {
        responsive: true,
        scales: { y: { beginAtZero: true } }
    }
});

// Gráfico B: Optimización Dinámica (Método del Codo)
const ctxCodo = document.getElementById('chartCodo').getContext('2d');
const graficoCodo = new Chart(ctxCodo, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Inercia Matemática (WCSS)',
            data: [],
            borderColor: '#a855f7',
            backgroundColor: 'rgba(168, 85, 247, 0.1)',
            borderWidth: 2,
            tension: 0.3,
            pointRadius: 5,
            pointBackgroundColor: '#a855f7'
        }]
    },
    options: {
        responsive: true,
        plugins: {
            legend: { labels: { color: '#ffffff' } },
            annotation: {
                annotations: {
                    codoLine: {
                        type: 'line',
                        mode: 'vertical',
                        scaleID: 'x',
                        value: null,
                        borderColor: '#ef4444',
                        borderWidth: 2,
                        borderDash: [5, 5],
                        label: {
                            content: 'Codo',
                            enabled: true,
                            position: 'top',
                            backgroundColor: 'rgba(239, 68, 68, 0.8)',
                            color: '#fff',
                            font: { weight: 'bold', size: 10 }
                        }
                    }
                }
            }
        },
        scales: {
            x: {
                ticks: { color: '#94a3b8' },
                grid: { color: '#334155' },
                title: { display: true, text: 'Número de Clusters (K)', color: '#ffffff' }
            },
            y: {
                beginAtZero: false,
                ticks: { color: '#94a3b8' },
                grid: { color: '#334155' },
                title: { display: true, text: 'Inercia (WCSS)', color: '#ffffff' }
            }
        }
    }
});

// Gráfico C: Scatter Velocidad vs Altitud
const ctxScatter = document.getElementById('chartScatter').getContext('2d');
const graficoScatter = new Chart(ctxScatter, {
    type: 'scatter',
    data: {
        datasets: [
            {
                label: 'Clúster 0 (Tierra/Rodaje)',
                data: [],
                backgroundColor: '#38bdf8',
                pointRadius: 3,
            },
            {
                label: 'Clúster 1 (Crucero)',
                data: [],
                backgroundColor: '#a855f7',
                pointRadius: 3,
            },
            {
                label: 'Clúster 2 (Ascenso/Descenso)',
                data: [],
                backgroundColor: '#eab308',
                pointRadius: 3,
            }
        ]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { labels: { color: '#f8fafc' } },
            tooltip: {
                callbacks: {
                    label: function(context) {
                        const raw = context.raw;
                        return `Vel: ${raw.x.toFixed(0)} km/h, Alt: ${raw.y.toFixed(0)} m`;
                    }
                }
            }
        },
        scales: {
            x: {
                type: 'linear',
                position: 'bottom',
                ticks: { color: '#94a3b8' },
                grid: { color: '#334155' },
                title: { display: true, text: 'Velocidad (km/h)', color: '#f8fafc' }
            },
            y: {
                ticks: { color: '#94a3b8' },
                grid: { color: '#334155' },
                title: { display: true, text: 'Altitud Barométrica (m)', color: '#f8fafc' }
            }
        }
    }
});

// Gráfico D: Evolución Temporal
const ctxEvolucion = document.getElementById('chartEvolucion').getContext('2d');
const graficoEvolucion = new Chart(ctxEvolucion, {
    type: 'line',
    data: {
        labels: [],
        datasets: [
            {
                label: 'Total aviones',
                data: [],
                borderColor: '#38bdf8',
                backgroundColor: 'rgba(56, 189, 248, 0.1)',
                tension: 0.3,
                pointRadius: 3,
                yAxisID: 'y',
            },
            {
                label: 'Anomalías',
                data: [],
                borderColor: '#ef4444',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                tension: 0.3,
                pointRadius: 3,
                yAxisID: 'y1',
            }
        ]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { labels: { color: '#f8fafc' } }
        },
        scales: {
            x: {
                ticks: { color: '#94a3b8', maxTicksLimit: 10 },
                grid: { color: '#334155' },
                title: { display: true, text: 'Lote (fecha/hora)', color: '#f8fafc' }
            },
            y: {
                type: 'linear',
                display: true,
                position: 'left',
                ticks: { color: '#94a3b8' },
                grid: { color: '#334155' },
                title: { display: true, text: 'Aviones', color: '#f8fafc' }
            },
            y1: {
                type: 'linear',
                display: true,
                position: 'right',
                ticks: { color: '#94a3b8' },
                grid: { drawOnChartArea: false },
                title: { display: true, text: 'Anomalías', color: '#f8fafc' }
            }
        }
    }
});

// ======================================================================
// 3. FUNCIONES ASÍNCRONAS DE CARGA DE DATOS (FASTAPI)
// ======================================================================

// Consulta del Método del Codo Basado en el Último Lote de Captura
async function cargarMetodoCodoDinamico() {
    try {
        console.log("Solicitando cálculo optimizado del Método del Codo al Backend...");
        const response = await fetch('http://127.0.0.1:8000/api/metodo-codo');
        const data = await response.json();
        
        if (data.error) {
            console.error("Error en el cálculo del codo:", data.error);
            return;
        }
        
        const k_values = data.k;
        const wcss_values = data.wcss;
        
        graficoCodo.data.labels = k_values;
        graficoCodo.data.datasets[0].data = wcss_values;
        graficoCodo.update();
        
        if (k_values && k_values.length >= 3) {
            const x1 = k_values[0];
            const y1 = wcss_values[0];
            const x2 = k_values[k_values.length - 1];
            const y2 = wcss_values[wcss_values.length - 1];
            let maxDist = -1;
            let codoK = k_values[1];
            for (let i = 1; i < k_values.length - 1; i++) {
                const x0 = k_values[i];
                const y0 = wcss_values[i];
                const numer = Math.abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1);
                const denom = Math.sqrt((y2 - y1) ** 2 + (x2 - x1) ** 2);
                const dist = numer / denom;
                if (dist > maxDist) {
                    maxDist = dist;
                    codoK = x0;
                }
            }
            const codoElement = document.getElementById('codo-optimo');
            if (codoElement) {
                codoElement.innerText = `K óptimo estimado: ${codoK}`;
            }
            if (graficoCodo.options.plugins && graficoCodo.options.plugins.annotation) {
                graficoCodo.options.plugins.annotation.annotations.codoLine.value = codoK;
                graficoCodo.update();
                console.log("Datos del codo recibidos:", k_values, wcss_values);
            }
        }
    } catch (error) {
        console.error("Error cargando el gráfico del codo:", error);
    }
}

async function actualizarScatter(fechaLote) {
    try {
        if (ultimoLoteScatter === fechaLote) return;
        console.log(`Solicitando scatter para lote: ${fechaLote}`);
        const url = `http://127.0.0.1:8000/api/scatter-lote?fecha_lote=${encodeURIComponent(fechaLote)}`;
        const response = await fetch(url);
        const data = await response.json();
        if (data.error) {
            console.error("Error scatter:", data.error);
            return;
        }

        const clusters = [[], [], []];
        data.registros.forEach(row => {
            const cluster = row.cluster_vuelo;
            if (cluster !== undefined && cluster !== null && cluster >= 0 && cluster < 3) {
                clusters[cluster].push({
                    x: row.velocity_kmh,
                    y: row.baro_altitude
                });
            }
        });

        graficoScatter.data.datasets.forEach((dataset, index) => {
            dataset.data = clusters[index] || [];
        });
        graficoScatter.update();

        ultimoLoteScatter = fechaLote;
        console.log(`Scatter actualizado para lote: ${fechaLote} (${data.total} registros)`);
    } catch (error) {
        console.error("Error cargando scatter:", error);
    }
}

// Carga el dendrograma para un lote dado por su fecha
async function cargarDendrogramaLote(fechaLote) {
    try {
        let url = 'http://127.0.0.1:8000/api/dendrograma-lote?';
        if (fechaLote) {
            url += `fecha_lote=${encodeURIComponent(fechaLote)}&`;
        }
        url += 'sample_size=400';
        
        console.log(`Solicitando dendrograma para lote: ${fechaLote || 'último'}`);
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.error) {
            console.error("Error dendrograma:", data.error);
            return;
        }
        
        const imgElement = document.getElementById('dendrograma-img');
        if (imgElement) {
            imgElement.src = `data:image/png;base64,${data.imagen}`;
            imgElement.alt = `Dendrograma - Lote ${data.fecha_lote} (${data.muestras} muestras)`;
        }
        console.log(`Dendrograma actualizado para lote: ${data.fecha_lote} (${data.muestras} muestras)`);
    } catch (error) {
        console.error("Error cargando dendrograma:", error);
    }
}

// cargar de parametro Silhouette
async function cargarSilhouette(fechaLote, k = 3) {
    try {
        if (ultimoLoteSilhouette === fechaLote) return;
        console.log(`Solicitando silueta precalculada para lote: ${fechaLote}`);
        const url = `http://127.0.0.1:8000/api/silhouette-precalc?fecha_lote=${encodeURIComponent(fechaLote)}`;
        const response = await fetch(url);
        const data = await response.json();
        if (data.error) {
            console.error("Error silueta:", data.error);
            return;
        }
        
        // ✅ ACTUALIZAR EL DOM
        const silMeanElement = document.getElementById('silhouette-mean');
        if (silMeanElement) {
            silMeanElement.innerText = data.silhouette_mean.toFixed(3);
            // Cambiar color según valor
            if (data.silhouette_mean > 0.7) {
                silMeanElement.style.color = '#4ade80'; // verde
            } else if (data.silhouette_mean > 0.4) {
                silMeanElement.style.color = '#facc15'; // amarillo
            } else {
                silMeanElement.style.color = '#f87171'; // rojo
            }
        }
        
        const silPerClusterElement = document.getElementById('silhouette-per-cluster');
        if (silPerClusterElement) {
            let html = '';
            // data.silhouette_per_cluster es un objeto { "0": 0.12, "1": 0.34, ... }
            for (const [cluster, value] of Object.entries(data.silhouette_per_cluster)) {
                html += `<span style="margin-right: 15px;">Clúster ${cluster}: ${parseFloat(value).toFixed(3)}</span>`;
            }
            silPerClusterElement.innerHTML = html;
        }
        
        ultimoLoteSilhouette = fechaLote;
        console.log(`Silueta actualizada para lote: ${fechaLote} (media: ${data.silhouette_mean.toFixed(3)})`);
    } catch (error) {
        console.error("Error cargando silueta:", error);
    }
}

async function actualizarEstadisticas(fechaLote) {
    try {
        if (ultimoLoteEstadisticas === fechaLote) return;
        console.log(`Solicitando estadísticas para lote: ${fechaLote}`);
        const url = `http://127.0.0.1:8000/api/estadisticas-lote?fecha_lote=${encodeURIComponent(fechaLote)}`;
        const response = await fetch(url);
        const data = await response.json();
        if (data.error) {
            console.error("Error estadísticas:", data.error);
            document.getElementById('tabla-estadisticas').innerHTML = `<p style="color: #ef4444;">Error: ${data.error}</p>`;
            return;
        }

        const html = `
            <table style="width:100%; color:#f8fafc; border-collapse: collapse; font-size:0.9rem;">
                <tr>
                    <th style="text-align:left; padding:6px 8px; border-bottom:1px solid #334155;">Métrica</th>
                    <th style="text-align:right; padding:6px 8px; border-bottom:1px solid #334155;">Valor</th>
                </tr>
                <tr><td style="padding:4px 8px;">✈️ Total aeronaves (únicas)</td><td style="text-align:right; padding:4px 8px;">${data.total_aviones}</td></tr>
                <tr><td style="padding:4px 8px;">⚠️ Anomalías</td><td style="text-align:right; padding:4px 8px;">${data.anomalias} (${data.porcentaje_anomalias}%)</td></tr>
                <tr><td style="padding:4px 8px;">🚀 Velocidad media ± std</td><td style="text-align:right; padding:4px 8px;">${data.velocidad.media} ± ${data.velocidad.std} km/h</td></tr>
                <tr><td style="padding:4px 8px;">⛰️ Altitud media ± std</td><td style="text-align:right; padding:4px 8px;">${data.altitud.media} ± ${data.altitud.std} m</td></tr>
                <tr><td style="padding:4px 8px;">📈 Tasa vertical media ± std</td><td style="text-align:right; padding:4px 8px;">${data.tasa_vertical.media} ± ${data.tasa_vertical.std} m/s</td></tr>
                <tr><td style="padding:4px 8px;">🌍 Top países</td><td style="text-align:right; padding:4px 8px;">${Object.entries(data.top_paises).map(([pais, count]) => `${pais} (${count})`).join(', ')}</td></tr>
                <tr><td style="padding:4px 8px;">📊 Distribución clústeres</td><td style="text-align:right; padding:4px 8px;">${Object.entries(data.cluster_distribucion).map(([k, v]) => `C${k}: ${v}`).join(' | ')}</td></tr>
                <tr><td style="padding:4px 8px;">🛬 En tierra</td><td style="text-align:right; padding:4px 8px;">${data.en_tierra}</td></tr>
                <tr><td style="padding:4px 8px;">📅 Fecha lote</td><td style="text-align:right; padding:4px 8px;">${data.fecha_lote}</td></tr>
            </table>
        `;
        document.getElementById('tabla-estadisticas').innerHTML = html;
        ultimoLoteEstadisticas = fechaLote;
        console.log(`Estadísticas actualizadas para lote: ${fechaLote}`);
    } catch (error) {
        console.error("Error cargando estadísticas:", error);
        document.getElementById('tabla-estadisticas').innerHTML = `<p style="color: #ef4444;">Error al cargar estadísticas.</p>`;
    }
}

async function cargarMapaCalor(fechaLote) {
    try {
        if (ultimoLoteMapaCalor === fechaLote) return;
        console.log(`Solicitando mapa de calor para lote: ${fechaLote}`);
        const url = `http://127.0.0.1:8000/api/mapa-calor?fecha_lote=${encodeURIComponent(fechaLote)}`;
        const response = await fetch(url);
        const data = await response.json();
        if (data.error) {
            console.error("Error mapa de calor:", data.error);
            return;
        }
        const imgElement = document.getElementById('mapa-calor-img');
        if (imgElement) {
            imgElement.src = `data:image/png;base64,${data.imagen}`;
            ultimoLoteMapaCalor = fechaLote;
            console.log(`Mapa de calor actualizado para lote: ${fechaLote}`);
        }
    } catch (error) {
        console.error("Error cargando mapa de calor:", error);
    }
}

// FUNCIÓN MAESTRA: Inicialización General del Simulador
async function inicializarSimulador() {
    try {
        console.log("Cargando dataset histórico desde FastAPI...");
        const response = await fetch('http://127.0.0.1:8000/api/vuelos');
        baseDeDatosCompleta = await response.json();
        
        if (baseDeDatosCompleta.error || baseDeDatosCompleta.length === 0) {
            console.error("Error o dataset vacío:", baseDeDatosCompleta.error);
            return;
        }

        // 🔥 OPTIMIZACIÓN 2: Agrupar por fecha
        baseDatosPorFecha = new Map();
        baseDeDatosCompleta.forEach(record => {
            const date = record.fecha_captura_sistema;
            if (!baseDatosPorFecha.has(date)) {
                baseDatosPorFecha.set(date, []);
            }
            baseDatosPorFecha.get(date).push(record);
        });

        // Obtener fechas únicas
        const fechasSet = new Set(baseDeDatosCompleta.map(v => v.fecha_captura_sistema).filter(f => f !== null && f !== undefined));
        listaFechasUnicas = Array.from(fechasSet).sort();
        
        console.log(`Dataset cargado: ${baseDeDatosCompleta.length} registros.`);
        console.log(`Se detectaron ${listaFechasUnicas.length} lotes.`);
        console.log(`Inicio: ${listaFechasUnicas[0]} -> Fin: ${listaFechasUnicas[listaFechasUnicas.length - 1]}`);

        // 🔥 OPTIMIZACIÓN 3: Calcular evolución usando el Map
        datosEvolucionCompleta = listaFechasUnicas.map(fecha => {
            const aviones = baseDatosPorFecha.get(fecha) || [];
            const total = aviones.length;
            const anomalias = aviones.filter(a => a.es_anomalia === true).length;
            const velocidades = aviones.map(a => a.velocity_kmh).filter(v => v != null);
            const velMedia = velocidades.length ? velocidades.reduce((a,b) => a+b, 0) / velocidades.length : 0;
            return { fecha, total, anomalias, velMedia };
        });

        // Inicializar gráfico de evolución vacío
        graficoEvolucion.data.labels = [];
        graficoEvolucion.data.datasets[0].data = [];
        graficoEvolucion.data.datasets[1].data = [];
        graficoEvolucion.update();

        // 🔥 OPTIMIZACIÓN 4: Cargar mapa de calor estático una sola vez con el primer lote
        if (listaFechasUnicas.length > 0) {
            cargarMapaCalor(listaFechasUnicas[0]);
            ejecutarPasoSimulacion();
            cargarMetodoCodoDinamico();
            setInterval(ejecutarPasoSimulacion, 5000);
        }

    } catch (error) {
        console.error("Fallo al inicializar el simulador:", error);
    }
}

// ======================================================================
// 4. MOTOR DE LA SIMULACIÓN TEMPORAL (ITERADOR)
// ======================================================================
function ejecutarPasoSimulacion() {
    // 🔥 OPTIMIZACIÓN 5: Eliminar 'return' para que no deje el gráfico en blanco
    if (indiceCronogramaActual >= listaFechasUnicas.length) {
        console.log("Fin de la línea de tiempo alcanzada. Reiniciando simulación...");
        indiceCronogramaActual = 0;
        // Continuar para procesar el primer lote
    }

    const fechaLoteActual = listaFechasUnicas[indiceCronogramaActual];
    // 🔥 OPTIMIZACIÓN 6: Usar el Map en lugar de filter
    const avionesDelLote = baseDatosPorFecha.get(fechaLoteActual) || [];

    // Cargar métricas para el lote actual (sin mapa de calor)
    cargarSilhouette(fechaLoteActual, 3);
    cargarDendrogramaLote(fechaLoteActual);
    actualizarScatter(fechaLoteActual);
    actualizarEstadisticas(fechaLoteActual);
    // 🔥 OPTIMIZACIÓN 7: Eliminada la llamada a cargarMapaCalor

    // ===== ACTUALIZAR GRÁFICO DE EVOLUCIÓN (con los datos hasta el lote actual) =====
    const inicio = Math.max(0, indiceCronogramaActual - VENTANA_LOTES + 1);
    const fin = indiceCronogramaActual + 1;
    const puntosAMostrar = datosEvolucionCompleta.slice(inicio, fin);

    if (puntosAMostrar.length > 0) {
        graficoEvolucion.data.labels = puntosAMostrar.map(d => new Date(d.fecha).toLocaleTimeString());
        graficoEvolucion.data.datasets[0].data = puntosAMostrar.map(d => d.total);
        graficoEvolucion.data.datasets[1].data = puntosAMostrar.map(d => d.anomalias);
    } else {
        graficoEvolucion.data.labels = [];
        graficoEvolucion.data.datasets[0].data = [];
        graficoEvolucion.data.datasets[1].data = [];
    }
    graficoEvolucion.update();

    // Filtrar duplicados por ICAO24 dentro del mismo lote
    const mapaAvionesUnicos = new Map();
    avionesDelLote.forEach(reg => {
        mapaAvionesUnicos.set(reg.icao24, reg);
    });

    capaAviones.clearLayers();
    
    let conteoClusters = [0, 0, 0];
    let totalAnomalias = 0;

    mapaAvionesUnicos.forEach(avion => {
        if(avion.cluster_vuelo !== undefined && avion.cluster_vuelo !== null) {
            conteoClusters[avion.cluster_vuelo]++;
        }
        if(avion.es_anomalia === true) {
            totalAnomalias++;
        }

        if (avion.latitude !== null && avion.longitude !== null) {
            const colorMarcador = avion.es_anomalia ? '#ef4444' : '#38bdf8';
            
            const velocidad = avion.velocity_kmh ? `${Math.round(avion.velocity_kmh)} km/h` : '0 km/h';
            const tasaVertical = avion.vertical_rate ? `${Math.round(avion.vertical_rate)} m/s` : '0 m/s';
            const altitud = avion.baro_altitude ? `${Math.round(avion.baro_altitude)} m` : 'En superficie';
            const callsignLimpio = avion.callsign ? avion.callsign.trim() : 'S/N';

            L.circleMarker([avion.latitude, avion.longitude], {
                radius: 5,
                fillColor: colorMarcador,
                color: '#ffffff',
                weight: 0.5,
                fillOpacity: 0.9
            })
            .bindPopup(`
                <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 12px;">
                    <strong style="color: #1e293b; font-size: 14px;">✈️ Vuelo: ${callsignLimpio}</strong><br>
                    <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 4px 0;">
                    <b>🌍 País Origen:</b> ${avion.origin_country}<br>
                    <b>📍 Coordenadas:</b> ${parseFloat(avion.latitude).toFixed(4)}, ${parseFloat(avion.longitude).toFixed(4)}<br>
                    <b>⛰️ Altitud Barométrica:</b> ${altitud}<br>
                    <b>⚡ Velocidad:</b> ${velocidad}<br>
                    <b>📈 Tasa Vertical:</b> ${tasaVertical}<br>
                    <span style="display:inline-block; margin-top:5px; padding:2px 6px; background:#f1f5f9; border-radius:4px; font-weight:bold;">
                        🤖 Perfil Asignado: Clúster ${avion.cluster_vuelo}
                    </span>
                </div>
            `)
            .addTo(capaAviones);
        }
    });

    graficoKMeans.data.datasets[0].data = conteoClusters;
    graficoKMeans.update();
    
    document.getElementById('total-aviones').innerText = mapaAvionesUnicos.size;
    document.getElementById('contador-anomalias').innerText = totalAnomalias;

    console.log(`[Simulador UCE] Lote: ${fechaLoteActual} | Aviones en pantalla: ${mapaAvionesUnicos.size}`);
    indiceCronogramaActual++;
}

// Inicializar el sistema completo
inicializarSimulador();