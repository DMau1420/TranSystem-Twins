// Red vial SUMO en formato GeoJSON (mismo formato que devuelve GET /red del backend).
// Features: tipo_elemento "calle" (LineString) y "semaforo" (Point).
// Orden de cada coordenada en el GeoJSON: [lng, lat]. Leaflet usa [lat, lng].

export const PRINCIPALES = [
  'motorway',
  'trunk',
  'primary',
  'secondary',
  'motorway_link',
  'primary_link',
  'secondary_link',
];

export const TIPO_TXT = {
  residential: 'Residencial',
  service: 'Servicio',
  secondary: 'Secundaria',
  tertiary: 'Terciaria',
  primary: 'Primaria',
  motorway: 'Autopista',
  motorway_link: 'Enlace',
  primary_link: 'Enlace',
  secondary_link: 'Enlace',
  living_street: 'Peatonal',
  unclassified: 'Sin clasificar',
};

// Fuentes en orden de prioridad: backend real (proxy de Vite) y luego archivo estático.
export const FUENTES_RED = [
  { url: '/api/red', nombre: 'backend' },
  { url: '/red.geojson', nombre: 'archivo local' },
];

export function esRedValida(gj) {
  return (
    !!gj &&
    gj.type === 'FeatureCollection' &&
    Array.isArray(gj.features) &&
    gj.features.some((f) => f?.properties?.tipo_elemento === 'calle')
  );
}

/**
 * Prueba cada fuente hasta encontrar una red válida.
 * Ojo: en desarrollo Vite responde index.html (200) a rutas desconocidas,
 * por eso se valida el contenido y no solo r.ok.
 */
export async function cargarRed(signal) {
  for (const { url, nombre } of FUENTES_RED) {
    try {
      const r = await fetch(url, { signal });
      if (!r.ok) continue;
      const gj = await r.json();
      if (esRedValida(gj)) return { geojson: gj, fuente: nombre };
    } catch (e) {
      if (e?.name === 'AbortError') throw e;
      // probar la siguiente fuente
    }
  }
  throw new Error('No se pudo cargar la red vial (backend ni archivo local)');
}

/** GeoJSON -> estructuras listas para Leaflet, con índices por id. */
export function convertirRed(gj) {
  const calles = [];
  const semaforos = [];
  for (const f of gj.features) {
    const p = f.properties ?? {};
    const g = f.geometry?.coordinates;
    if (!g) continue;
    if (p.tipo_elemento === 'calle') {
      calles.push({
        id: p.edge_id,
        tipo: String(p.tipo ?? '').replace('highway.', ''),
        carriles: p.carriles,
        velocidad: p.velocidad_max,
        longitud: Math.round(p.longitud ?? 0),
        puntos: g.map(([lng, lat]) => [lat, lng]),
      });
    } else if (p.tipo_elemento === 'semaforo') {
      semaforos.push({
        id: p.tls_id,
        pos: [g[1], g[0]],
        entrantes: p.calles_entrantes ?? [],
        salientes: p.calles_salientes ?? [],
        programas: p.programas ?? {},
      });
    }
  }
  const idxCalles = Object.fromEntries(calles.map((c) => [c.id, c]));
  const idxSemaforos = Object.fromEntries(semaforos.map((s) => [s.id, s]));
  return { calles, semaforos, idxCalles, idxSemaforos };
}

export const esPrincipal = (c) => PRINCIPALES.includes(c.tipo);
export const esRampa = (c) => c.tipo.includes('link');
export const etiquetaCalle = (c) => `${TIPO_TXT[c.tipo] || c.tipo} ${c.id}`;
export const fasesOriginales = (s) => Object.values(s.programas)[0] ?? [];

/** La calle opuesta de una vía bidireccional (SUMO: "-123" vs "123"), si existe. */
export function calleOpuesta(red, id) {
  const o = id.startsWith('-') ? id.slice(1) : `-${id}`;
  return red.idxCalles[o] ? o : null;
}

// ---- Estilos (paleta SYS_CORE) ----
export const COLORES = {
  principal: '#2de3ff', // cyan
  calle: '#2de3ff',
  rampa: '#ffb020', // amber
  seleccion: '#ff2d6f', // magenta
  modificada: '#7dff9a',
  semaforo: '#ffb020',
};

export function estiloCalle(c, { seleccionada, modificada, soloPrincipales } = {}) {
  const w = Math.min(8, 1.5 + (c.carriles ?? 1) * 1.2);
  const prin = esPrincipal(c);
  if (seleccionada) return { color: COLORES.seleccion, weight: w + 2, opacity: 1, dashArray: null };
  if (modificada) return { color: COLORES.modificada, weight: w + 2, opacity: 0.95, dashArray: null };
  if (soloPrincipales && !prin) return { color: COLORES.calle, weight: 1.5, opacity: 0.1, dashArray: null };
  if (esRampa(c)) return { color: COLORES.rampa, weight: w, opacity: 0.8, dashArray: '4,5' };
  return { color: COLORES.calle, weight: w, opacity: prin ? 0.9 : 0.45, dashArray: null };
}

export function estiloSemaforo({ seleccionado, modificado } = {}) {
  if (seleccionado) return { radius: 9, color: COLORES.seleccion, fillColor: COLORES.seleccion, fillOpacity: 1, weight: 3 };
  if (modificado) return { radius: 8, color: COLORES.modificada, fillColor: COLORES.modificada, fillOpacity: 0.95, weight: 2 };
  return { radius: 6, color: '#1a1200', fillColor: COLORES.semaforo, fillOpacity: 0.95, weight: 2 };
}
