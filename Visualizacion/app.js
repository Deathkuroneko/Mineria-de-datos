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
                        value: null,  // se actualizará dinámicamente
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
    // ⚠️ ELIMINAR: plugins: [ChartAnnotation]  <--- Ya no es necesario
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
        
        // Actualizar datos del gráfico
        graficoCodo.data.labels = k_values;
        graficoCodo.data.datasets[0].data = wcss_values;
        graficoCodo.update();
        
        // Calcular el punto de codo (método de máxima distancia)
        if (k_values && k_values.length >= 3) {
            const x1 = k_values[0];
            const y1 = wcss_values[0];
            const x2 = k_values[k_values.length - 1];
            const y2 = wcss_values[wcss_values.length - 1];
            let maxDist = -1;
            let codoK = k_values[1]; // valor por defecto
            for (let i = 1; i < k_values.length - 1; i++) {
                const x0 = k_values[i];
                const y0 = wcss_values[i];
                // Distancia perpendicular desde el punto (x0,y0) a la línea (x1,y1)-(x2,y2)
                const numer = Math.abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1);
                const denom = Math.sqrt((y2 - y1) ** 2 + (x2 - x1) ** 2);
                const dist = numer / denom;
                if (dist > maxDist) {
                    maxDist = dist;
                    codoK = x0;
                }
            }
            // Mostrar K óptimo en el DOM
            const codoElement = document.getElementById('codo-optimo');
            if (codoElement) {
                codoElement.innerText = `K óptimo estimado: ${codoK}`;
            }
            
            // ✅ ACTUALIZAR LA ANOTACIÓN CON EL VALOR DE codoK
            if (graficoCodo.options.plugins && graficoCodo.options.plugins.annotation) {
                graficoCodo.options.plugins.annotation.annotations.codoLine.value = codoK;
                graficoCodo.update(); // <--- necesario para reflejar el cambio
                console.log("Datos del codo recibidos:", k_values, wcss_values);
            }
        }
    } catch (error) {
        console.error("Error cargando el gráfico del codo:", error);
    }
}

// Carga el dendrograma para un lote dado por su fecha
async function cargarDendrogramaLote(fechaLote) {
    try {
        // Si no se pasa fecha, se usará el último lote automáticamente (backend)
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
        
        // Actualizar la imagen en el contenedor
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
        if (ultimoLoteSilhouette === fechaLote) return; // Evita duplicados
        console.log(`Solicitando silueta para lote: ${fechaLote}`);
        const url = `http://127.0.0.1:8000/api/silhouette?fecha_lote=${encodeURIComponent(fechaLote)}&k=${k}`;
        const response = await fetch(url);
        const data = await response.json();
        if (data.error) {
            console.error("Error silueta:", data.error);
            return;
        }
        
        // Actualizar el DOM
        const silMeanElement = document.getElementById('silhouette-mean');
        if (silMeanElement) {
            silMeanElement.innerText = data.silhouette_mean.toFixed(3);
            // Opcional: cambiar color según valor (verde > 0.7, naranja > 0.4, rojo < 0.4)
            if (data.silhouette_mean > 0.7) silMeanElement.style.color = '#4ade80';
            else if (data.silhouette_mean > 0.4) silMeanElement.style.color = '#facc15';
            else silMeanElement.style.color = '#f87171';
        }
        
        // Mostrar silueta por clúster (opcional)
        const silPerClusterElement = document.getElementById('silhouette-per-cluster');
        if (silPerClusterElement) {
            let html = '';
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

        // Agrupar marcas de tiempo únicas del sistema y ordenarlas cronológicamente
        const fechasSet = new Set(baseDeDatosCompleta.map(v => v.fecha_captura_sistema).filter(f => f !== null && f !== undefined));
        listaFechasUnicas = Array.from(fechasSet).sort();
        
        console.log(`Dataset cargado: ${baseDeDatosCompleta.length} registros.`);
        console.log(`Se detectaron ${listaFechasUnicas.length} lotes de tiempo del sistema únicos.`);
        console.log(`Inicio: ${listaFechasUnicas[0]} -> Fin: ${listaFechasUnicas[listaFechasUnicas.length - 1]}`);

        // Ejecuciones iniciales e inicio del temporizador reactivo
        if (listaFechasUnicas.length > 0) {
            ejecutarPasoSimulacion();
            cargarMetodoCodoDinamico(); // Se ejecuta solo UNA VEZ de fondo
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
    // ... (sin cambios, igual que antes)
    if (indiceCronogramaActual >= listaFechasUnicas.length) {
        console.log("Fin de la línea de tiempo alcanzada. Reiniciando simulación...");
        indiceCronogramaActual = 0;
    }

    const fechaLoteActual = listaFechasUnicas[indiceCronogramaActual];
    const avionesDelLote = baseDeDatosCompleta.filter(v => v.fecha_captura_sistema === fechaLoteActual);

    cargarSilhouette(fechaLoteActual, 3); // K=3 fijo
    cargarDendrogramaLote(fechaLoteActual);
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
    
    const elementAnomalias = document.getElementById('contador-anomalias');
    if (elementAnomalias) {
        elementAnomalias.innerText = totalAnomalias;
    }

    console.log(`[Simulador UCE] Lote: ${fechaLoteActual} | Aviones en pantalla: ${mapaAvionesUnicos.size}`);
    indiceCronogramaActual++;
}



// Inicializar el sistema completo
inicializarSimulador();