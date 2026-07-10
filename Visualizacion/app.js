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
            pointRadius: 5,               // Puntos ligeramente más grandes
            pointBackgroundColor: '#a855f7'
        }]
    },
    options: {
        responsive: true,
        plugins: {
            legend: { labels: { color: '#ffffff' } }
        },
        scales: {
            x: { 
                ticks: { color: '#94a3b8' }, 
                grid: { color: '#334155' },
                title: { display: true, text: 'Número de Clusters (K)', color: '#ffffff' }
            },
            y: { 
                // CRÍTICO: No forzar el inicio en 0 para que la escala resalte la curva real
                beginAtZero: false, 
                ticks: { color: '#94a3b8' }, 
                grid: { color: '#334155' },
                title: { display: true, text: 'Inercia (WCSS)', color: '#ffffff' }
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
        
        // Asignar los vectores calculados por Python
        graficoCodo.data.labels = data.k;
        graficoCodo.data.datasets[0].data = data.wcss;
        graficoCodo.update();
        console.log(`✔️ ¡Gráfica del Codo renderizada! Lote analizado: ${data.info_lote} (${data.registros_procesados} aviones).`);
    } catch (error) {
        console.error("Error cargando el gráfico del codo:", error);
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
    if (indiceCronogramaActual >= listaFechasUnicas.length) {
        console.log("Fin de la línea de tiempo alcanzada. Reiniciando simulación...");
        indiceCronogramaActual = 0;
    }

    const fechaLoteActual = listaFechasUnicas[indiceCronogramaActual];
    const avionesDelLote = baseDeDatosCompleta.filter(v => v.fecha_captura_sistema === fechaLoteActual);

    // Filtrar duplicados por ICAO24 dentro del mismo lote por consistencia visual
    const mapaAvionesUnicos = new Map();
    avionesDelLote.forEach(reg => {
        mapaAvionesUnicos.set(reg.icao24, reg);
    });

    // Limpiar pantalla anterior
    capaAviones.clearLayers();
    
    let conteoClusters = [0, 0, 0];
    let totalAnomalias = 0;

    // Renderizar transpondedores del lote actual
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

    // Actualizar elementos dinámicos del DOM
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