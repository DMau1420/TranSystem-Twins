// =====================================================================
// ESTADO GLOBAL, ESTILOS Y "¿ESTÁ MODIFICADO?"
// =====================================================================
let redData = null;
let capaRed = null;
let capaSeleccionada = null;
let mapa = null;
let featureSeleccionada = null;

// Valores originales congelados la primera vez que se carga la red.
// Nunca se sobrescriben: sirven para "Restaurar" y para saber qué se modificó.
const originalesCalles = new Map();     // edge_id -> { carriles, velocidad_max }
const originalesSemaforos = new Map();  // tls_id  -> copia profunda de p.programas

const COLOR_MODIFICADA = '#00a86b';
const COLOR_POR_CATEGORIA = { principal: '#1a1aff', rampa: '#9b59b6', calle: '#5c00e6' };

// ---------- Clasificación ----------
function clasificarTipo(tipoRaw) {
    const tipo = (tipoRaw || '').toLowerCase();
    if (tipo.includes('link')) return 'rampa';
    if (tipo.includes('motorway') || tipo.includes('trunk')) return 'principal';
    return 'calle';
}

// ---------- ¿Qué se ha modificado respecto al original? ----------
function calleModificada(p) {
    const o = originalesCalles.get(p.edge_id);
    return !!o && (o.carriles !== p.carriles || o.velocidad_max !== p.velocidad_max);
}

function semaforoModificado(p) {
    const o = originalesSemaforos.get(p.tls_id);
    const id = Object.keys(p.programas || {})[0];
    if (!o || !id || !o[id]) return false;
    return p.programas[id].some((f, i) => o[id][i] && f.duracion !== o[id][i].duracion);
}

function actualizarContadorCambios() {
    if (!redData) return;
    let calles = 0, semaforos = 0;
    redData.features.forEach(f => {
        const p = f.properties;
        if (p.tipo_elemento === 'calle' && calleModificada(p)) calles++;
        if (p.tipo_elemento === 'semaforo' && semaforoModificado(p)) semaforos++;
    });
    const el = document.getElementById('contador-cambios');
    el.style.display = (calles + semaforos) ? 'inline-block' : 'none';
    el.textContent = `${calles} calles · ${semaforos} semáforos modificados`;
}

// ---------- Estilos del mapa ----------
function estiloBase(feature) {
    const p = feature && feature.properties;

    if (p && p.tipo_elemento === 'interseccion') {
        const color = COLOR_POR_CATEGORIA[clasificarTipo(p.tipo)] || COLOR_POR_CATEGORIA.calle;
        return { stroke: false, fillColor: color, fillOpacity: 0.8 };
    }
    if (p && p.tipo_elemento === 'calle' && calleModificada(p)) {
        return { color: COLOR_MODIFICADA, weight: 9, opacity: 0.95, smoothFactor: 1 };
    }
    switch (clasificarTipo(p && p.tipo)) {
        case 'principal': return { color: '#1a1aff', weight: 8, opacity: 0.85, smoothFactor: 1 };
        case 'rampa':     return { color: '#9b59b6', weight: 4, opacity: 0.7, dashArray: '4, 5', smoothFactor: 1 };
        default:          return { color: '#5c00e6', weight: 6, opacity: 0.75, smoothFactor: 1 };
    }
}

function estiloSeleccionado() {
    return { color: '#c96a3a', weight: 6, opacity: 0.95, dashArray: null, smoothFactor: 1 };
}

function estiloHover(feature) {
    return { ...estiloBase(feature), color: '#e67e22', opacity: 0.9 };
}

function estiloSemaforoBase(feature) {
    const mod = !!(feature && feature.properties && semaforoModificado(feature.properties));
    return {
        radius: mod ? 9 : 7,
        color: mod ? '#00805a' : '#c0392b',
        fillColor: mod ? COLOR_MODIFICADA : '#e74c3c',
        fillOpacity: 0.9,
        weight: 2
    };
}

function estiloSemaforoSeleccionado() {
    return { radius: 9, color: '#c96a3a', fillColor: '#c96a3a', fillOpacity: 0.95, weight: 3 };
}
