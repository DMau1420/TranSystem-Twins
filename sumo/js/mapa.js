// =====================================================================
// MAPA DE LEAFLET: creación, capas y selección
// =====================================================================
function initMap() {
    mapa = L.map('mapa', { center: [19.4602, -99.1832], zoom: 14, zoomControl: true });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(mapa);
}

function popupCalle(p) {
    const tipo = clasificarTipo(p.tipo);
    const etiqueta = tipo === 'rampa' ? ' (Rampa/enlace)' : tipo === 'principal' ? ' (Vía principal)' : '';
    return `
        <strong>${p.nombre_calle}</strong>${etiqueta}<br>
        ID: ${p.edge_id}<br>
        Carriles: ${p.carriles}<br>
        Velocidad: ${p.velocidad_max} km/h
        ${p.controlado_por_semaforo ? '<br>Llega a semáforo' : ''}`;
}

function agregarCalles(geojson) {
    if (!geojson || !geojson.features) return;

    capaRed = L.geoJSON(geojson, {
        filter: f => f.properties.tipo_elemento !== 'conector_interno' || f.properties.pertenece_a_glorieta === true,
        pointToLayer: (feature, latlng) => L.circleMarker(latlng, estiloSemaforoBase(feature)),
        style: estiloBase,
        onEachFeature: configurarElemento
    }).addTo(mapa);

    if (capaRed.getBounds().isValid()) {
        mapa.fitBounds(capaRed.getBounds(), { padding: [50, 50] });
    }
}

// Define qué hace cada tipo de elemento al hacer clic / hover
function configurarElemento(feature, layer) {
    const p = feature.properties;

    if (p.tipo_elemento === 'semaforo') {
        if (!originalesSemaforos.has(p.tls_id)) {
            originalesSemaforos.set(p.tls_id, JSON.parse(JSON.stringify(p.programas || {})));
        }
        layer.on('click', e => { seleccionarSemaforo(feature, layer); L.DomEvent.stopPropagation(e); });
        return;
    }

    if (p.tipo_elemento === 'conector_interno') return;

    if (p.tipo_elemento === 'interseccion') {
        layer.bindTooltip(
            'Intersección (junction)<br>Área generada automáticamente por el simulador.<br>' +
            'No es una calle y no se puede editar aquí.',
            { sticky: true, direction: 'top', opacity: 0.9, className: 'tooltip-interseccion' }
        );
        return;
    }

    // Calles
    if (!originalesCalles.has(p.edge_id)) {
        originalesCalles.set(p.edge_id, { carriles: p.carriles, velocidad_max: p.velocidad_max });
    }
    layer.on('click', e => { seleccionarCalle(feature, layer); L.DomEvent.stopPropagation(e); });
    layer.on('mouseover', () => { if (layer !== capaSeleccionada) layer.setStyle(estiloHover(feature)); });
    layer.on('mouseout',  () => { if (layer !== capaSeleccionada) layer.setStyle(estiloBase(feature)); });
    layer.bindPopup(popupCalle(p));
}

function limpiarSeleccionActual() {
    if (!capaSeleccionada) return;
    const p = capaSeleccionada.feature && capaSeleccionada.feature.properties;
    if (p && p.tipo_elemento === 'semaforo') {
        capaSeleccionada.setStyle(estiloSemaforoBase(capaSeleccionada.feature));
    } else {
        capaSeleccionada.setStyle(estiloBase(capaSeleccionada.feature));
    }
}

function seleccionarCalle(feature, layer) {
    limpiarSeleccionActual();
    capaSeleccionada = layer;
    featureSeleccionada = feature;
    layer.setStyle(estiloSeleccionado());
    mostrarPanelEdicion(feature, layer);
}

function seleccionarSemaforo(feature, layer) {
    limpiarSeleccionActual();
    capaSeleccionada = layer;
    featureSeleccionada = feature;
    layer.setStyle(estiloSemaforoSeleccionado());
    mostrarPanelEdicionSemaforo(feature, layer);
}
