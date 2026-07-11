// ======================================================================
// 1. INICIALIZAR EL MAPA GLOBAL
// ======================================================================
const mapa = L.map('mapa', {
    worldCopyJump: false,  // Evita que el mundo se repita al desplazarse
    maxBounds: L.latLngBounds([-90, -180], [90, 180]), // Limita al mundo real
    maxZoom: 18,  // Zoom máximo (acercar)
    minZoom: 2    // Zoom mínimo (alejar) - con 2 ves el mundo completo sin repetición
}).setView([20.0, -10.0], 2);
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
const VENTANA_LOTES = 4;
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

// Cargar resultados de minería (centroides, anomalías, etc.)
async function cargarResultadosMineria() {
    try {
        const response = await fetch('http://127.0.0.1:8000/api/mineria-resultados');
        const data = await response.json();
        if (data.error) {
            console.error("Error resultados minería:", data.error);
            return;
        }

        // 1. Mostrar porcentaje de anomalías
        const porcentajeEl = document.getElementById('global-porcentaje-anomalias');
        if (porcentajeEl) {
            porcentajeEl.textContent = data.porcentaje_anomalias.toFixed(2) + '%';
        }

        // 2. Obtener distribución global de clústeres (desde estadísticas globales)
        let clusterDist = {};
        try {
            const statsResponse = await fetch('http://127.0.0.1:8000/api/estadisticas-globales');
            const statsData = await statsResponse.json();
            if (!statsData.error && statsData.cluster_global) {
                clusterDist = JSON.parse(statsData.cluster_global);
            }
        } catch (err) {
            console.warn("No se pudo obtener la distribución de clústeres:", err);
        }

        // 3. Generar tarjetas de centroides dinámicamente
        const container = document.getElementById('centroides-container');
        if (!container) {
            console.warn("Contenedor 'centroides-container' no encontrado en el DOM.");
            return;
        }

        // Nombres descriptivos para los primeros 3 clústeres (si existen)
        const nombresPerfiles = {
            0: '🌍 Tierra / Rodaje',
            1: '✈️ Crucero',
            2: '⬆️ Ascenso / Aproximación',
            3: '🔄 Maniobra / Espera',      // si aparece un cuarto perfil
            4: '📦 Carga / Militar',         // si aparece un quinto
        };
        // Paleta de colores (se repetirá cíclicamente si hay más de 3)
        const colores = [
            '#38bdf8', // azul
            '#a855f7', // morado
            '#eab308', // amarillo
            '#f97316', // naranja
            '#ec4899', // rosa
            '#14b8a6', // turquesa
            '#8b5cf6', // violeta
            '#f59e0b'  // ámbar
        ];

        // Construir HTML de las tarjetas
        let html = '';
        data.centroides.forEach((centroide, index) => {
            const perfil = centroide.perfil;
            // Usar nombre descriptivo si existe, o genérico
            const nombre = nombresPerfiles[perfil] || `Perfil ${perfil}`;
            const color = colores[perfil % colores.length];
            const count = clusterDist[perfil] || 0;
            
            // Convertir color hex a rgb para el fondo semitransparente
            const rgb = hexToRgb(color);
            
            html += `
                <div style="background: rgba(${rgb}, 0.1); border: 1px solid ${color}; border-radius: 8px; padding: 0.8rem; text-align: center;">
                    <div style="font-weight: bold; color: ${color};">${nombre}</div>
                    <div style="font-size: 0.9rem; color: #94a3b8; margin: 0.3rem 0;">
                        Aviones: <span style="color: #f8fafc; font-weight: bold;">${count.toLocaleString()}</span>
                    </div>
                    <div style="font-size: 0.9rem; color: #cbd5e1; margin-top: 0.3rem;">
                        Alt: ${centroide.altitud.toFixed(0)} m<br>
                        Vel: ${centroide.velocidad.toFixed(0)} km/h<br>
                        TV: ${centroide.tasa_vertical.toFixed(1)} m/s
                    </div>
                </div>
            `;
        });
        container.innerHTML = html;

        console.log("✅ Resultados de minería cargados (dinámicos):", data);
    } catch (error) {
        console.error("Error cargando resultados de minería:", error);
    }
}

// Función auxiliar para convertir hex a rgb
function hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? `${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}` : '255,255,255';
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
        
        // Actualizar valor medio
        const silMeanElement = document.getElementById('silhouette-mean');
        if (silMeanElement) {
            const valor = data.silhouette_mean;
            silMeanElement.innerText = valor.toFixed(3);
            // Color según valor
            let color;
            if (valor > 0.7) color = '#4ade80';
            else if (valor > 0.4) color = '#facc15';
            else color = '#f87171';
            silMeanElement.style.color = color;
            
            // Actualizar barra de progreso
            const bar = document.getElementById('silhouette-bar');
            if (bar) {
                // Escalar el valor a porcentaje (0-1 → 0-100%)
                const porcentaje = Math.min(valor * 100, 100);
                bar.style.width = porcentaje + '%';
                bar.style.background = color;
            }
        }
        
        // Actualizar valores por clúster (badges)
        const silPerClusterElement = document.getElementById('silhouette-per-cluster');
        if (silPerClusterElement) {
            const clusterColors = ['#38bdf8', '#a855f7', '#eab308']; // azul, morado, amarillo
            let html = '';
            const entries = Object.entries(data.silhouette_per_cluster);
            for (const [cluster, value] of entries) {
                const color = clusterColors[parseInt(cluster)] || '#94a3b8';
                html += `
                    <span style="display: inline-block; background: rgba(51, 65, 85, 0.5); border-left: 4px solid ${color}; padding: 0.3rem 0.8rem; border-radius: 4px; font-size: 0.9rem; color: #e2e8f0;">
                        Clúster ${cluster}: <strong style="color: ${color};">${parseFloat(value).toFixed(3)}</strong>
                    </span>
                `;
            }
            silPerClusterElement.innerHTML = html || '<span style="color: #94a3b8;">No hay datos</span>';
        }
        
        // Actualizar fecha del lote
        const fechaElement = document.getElementById('silhouette-fecha');
        if (fechaElement) {
            fechaElement.innerText = `Lote: ${data.fecha_lote}`;
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

async function cargarMapaCalor() {
    try {
        if (ultimoLoteMapaCalor === 'estatico') return;
        console.log("Solicitando mapa de calor estático...");
        const response = await fetch('http://127.0.0.1:8000/api/mapa-calor');
        const data = await response.json();
        if (data.error) {
            console.error("Error mapa de calor:", data.error);
            return;
        }
        const imgElement = document.getElementById('mapa-calor-img');
        if (imgElement) {
            imgElement.src = `data:image/png;base64,${data.imagen}`;
            ultimoLoteMapaCalor = 'estatico';
            console.log("Mapa de calor estático cargado.");
        }
    } catch (error) {
        console.error("Error cargando mapa de calor:", error);
    }
}

async function cargarMetricasPipeline() {
    try {
        const response = await fetch('http://127.0.0.1:8000/api/pipeline-metrics');
        const data = await response.json();
        if (data.error) {
            console.error("Error métricas pipeline:", data.error);
            // Mostrar mensaje de "No disponible"
            document.querySelectorAll('[id^="metric-"]').forEach(el => el.innerText = 'N/A');
            document.getElementById('pipeline-estado').innerText = 'No disponible';
            return;
        }

        // ===== DATOS GLOBALES =====
        document.getElementById('pipeline-estado').innerText = data.estado_general || 'EXITOSO';
        document.getElementById('pipeline-inicio').innerText = data.timestamp_inicio || '---';
        document.getElementById('pipeline-fin').innerText = data.timestamp_fin || '---';
        document.getElementById('pipeline-tiempo-total').innerText = data.tiempo_total_minutos.toFixed(1) + ' min';
        document.getElementById('pipeline-config').innerText = `${data.horas_operacion}h / ${data.intervalo_muestreo}s`;
        document.getElementById('pipeline-csv-nombre').innerText = data.ingesta.archivo_csv || '---';
        document.getElementById('pipeline-parquet-nombre').innerText = data.etl.archivo_parquet || '---';

        // ===== INGESTA =====
        const ing = data.ingesta;
        document.getElementById('ingesta-registros').innerText = ing.total_registros.toLocaleString();
        document.getElementById('ingesta-ciclos').innerText = ing.ciclos_ejecutados;
        document.getElementById('ingesta-ciclos-totales').innerText = ing.ciclos_totales;
        // Convertir segundos a formato legible (minutos)
        const ingTiempoMin = (ing.tiempo_ejecucion_segundos / 60).toFixed(1);
        document.getElementById('ingesta-tiempo').innerText = ingTiempoMin + ' min';

        // ===== ETL =====
        const etl = data.etl;
        document.getElementById('etl-registros-iniciales').innerText = etl.registros_iniciales.toLocaleString();
        document.getElementById('etl-registros-finales').innerText = etl.registros_finales.toLocaleString();
        document.getElementById('etl-tamano-csv').innerText = etl.tamano_csv_mb.toFixed(1) + ' MB';
        document.getElementById('etl-tamano-parquet').innerText = etl.tamano_parquet_mb.toFixed(1) + ' MB';
        document.getElementById('etl-reduccion').innerText = etl.reduccion_porcentaje.toFixed(1) + '%';
        document.getElementById('etl-tiempo').innerText = etl.duracion_segundos.toFixed(1) + ' s';

        // Barra de reducción
        const barra = document.getElementById('etl-reduccion-barra');
        if (barra) {
            const reduccion = Math.min(etl.reduccion_porcentaje, 100);
            barra.style.width = reduccion + '%';
            // Cambiar color según el valor
            if (reduccion > 70) barra.style.background = '#34d399';
            else if (reduccion > 40) barra.style.background = '#fbbf24';
            else barra.style.background = '#f87171';
        }

        console.log("Métricas del pipeline cargadas:", data);
    } catch (error) {
        console.error("Error cargando métricas del pipeline:", error);
        document.querySelectorAll('[id^="metric-"]').forEach(el => el.innerText = 'Error');
    }
}

async function cargarEstadisticasGlobales() {
    try {
        const response = await fetch('http://127.0.0.1:8000/api/estadisticas-globales');
        const data = await response.json();
        if (data.error) {
            console.error("Error estadísticas globales:", data.error);
            return;
        }
        // Actualizar DOM (métricas rápidas)
        document.getElementById('global-total-registros').innerText = data.total_registros.toLocaleString();
        document.getElementById('global-aviones-unicos').innerText = data.total_aviones_unicos.toLocaleString();
        document.getElementById('global-lotes').innerText = data.total_lotes;
        document.getElementById('global-anomalias').innerText = data.total_anomalias.toLocaleString();
        document.getElementById('global-velocidad-media').innerText = data.velocidad_global_media.toFixed(1);
        document.getElementById('global-altitud-media').innerText = data.altitud_global_media.toFixed(0);
        document.getElementById('global-tv-media').innerText = data.tv_global_media.toFixed(1);

        // Porcentaje de anomalías
        const porcentajeAnomalias = (data.total_anomalias / data.total_registros * 100).toFixed(2);
        document.getElementById('global-porcentaje-anomalias').innerText = porcentajeAnomalias + '%';

        console.log("Estadísticas globales cargadas:", data);
    } catch (error) {
        console.error("Error cargando estadísticas globales:", error);
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
            ejecutarPasoSimulacion();
            cargarMetodoCodoDinamico();
            await cargarEstadisticasGlobales();
            await cargarResultadosMineria();
            cargarMetricasPipeline();
            cargarMapaCalor();
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
            // Colores por clúster
            const coloresCluster = ['#38bdf8', '#a855f7', '#eab308'];
            const cluster = avion.cluster_vuelo;
            const fillColor = (cluster !== undefined && cluster !== null && cluster >= 0 && cluster < coloresCluster.length) 
                ? coloresCluster[cluster] 
                : '#94a3b8'; // gris por defecto
            const borderColor = avion.es_anomalia ? '#ef4444' : '#ffffff';
            const borderWeight = avion.es_anomalia ? 2 : 0.5;
            
            const velocidad = avion.velocity_kmh ? `${Math.round(avion.velocity_kmh)} km/h` : '0 km/h';
            const tasaVertical = avion.vertical_rate ? `${Math.round(avion.vertical_rate)} m/s` : '0 m/s';
            const altitud = avion.baro_altitude ? `${Math.round(avion.baro_altitude)} m` : 'En superficie';
            const callsignLimpio = avion.callsign ? avion.callsign.trim() : 'S/N';

            L.circle([avion.latitude, avion.longitude], {
                radius: 800,  // Radio en metros (ajusta este valor según prefieras)
                fillColor: fillColor,
                color: borderColor,
                weight: borderWeight,
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