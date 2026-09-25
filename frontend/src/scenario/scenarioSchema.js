// src/scenario/scenarioSchema.js
// Forma del documento de escenario: TODO lo que se guarda vive aquí.
// Lo que es solo UI (selección actual, paneles abiertos) NO va en el documento.

export const SCENARIO_VERSION = 1;

export const LIMITS = {
  maxspeedKmh: [5, 130],
  lanes: [1, 8],
  phaseSeconds: [1, 180],
};

export const newId = (prefix = 'scn') =>
  `${prefix}_${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`;

export const clamp = (value, [min, max]) =>
  Math.min(max, Math.max(min, Math.round(Number(value))));

export function createScenario({
  projectId = null,
  name = 'Nuevo escenario',
} = {}) {
  const now = new Date().toISOString();
  return {
    id: newId(),
    projectId, // vínculo con el proyecto (ProjectsPanel)
    name,
    version: SCENARIO_VERSION,
    createdAt: now,
    updatedAt: now,

    // Zona seleccionada en el mapa (lo que dibujas con Geoman).
    // bbox = [south, west, north, east]; polygon = Feature<Polygon> GeoJSON o null
    area: null,

    // Lo dibujado/marcado en el mapa (panel PUNTOS_DEL_MAPA), como GeoJSON.
    // Es lo mismo que muestra la pestaña JSON del panel.
    features: { points: [], routes: [], zones: [] },

    // De dónde salió la red base
    network: { source: null, importedAt: null }, // source: 'osm' | 'sumo'

    // Cambios del usuario sobre la red base, indexados por id del elemento.
    // Solo se guardan las diferencias, no la red completa.
    edits: {
      edges: {}, //     { [edgeId]: { maxspeed?: km/h, lanes?: n } }
      junctions: {}, // { [nodeId]: { tls: { phases: [{ duration, state }] } } }
    },
  };
}

// "maxspeed" de OSM llega como "50", "50 km/h" o "30 mph"
export function parseMaxspeed(raw) {
  if (raw == null) return null;
  const n = parseFloat(String(raw));
  if (Number.isNaN(n)) return null;
  return /mph/i.test(String(raw)) ? Math.round(n * 1.609) : Math.round(n);
}

// Valor efectivo = edición del usuario si existe, si no el valor base de la red.
// Ajusta los nombres de propiedades a lo que traiga tu GeoJSON (/api/red u Overpass).
export function effectiveEdge(baseProps = {}, edit = {}) {
  return {
    maxspeed:
      edit.maxspeed ?? parseMaxspeed(baseProps.maxspeed ?? baseProps.speed),
    lanes:
      edit.lanes ?? (Number(baseProps.lanes ?? baseProps.numLanes) || null),
    edited: Object.keys(edit).length > 0,
  };
}

export const countEdits = (scenario) =>
  Object.keys(scenario.edits.edges).length +
  Object.keys(scenario.edits.junctions).length;

// Nombre genérico a partir de la ubicación de lo marcado en el mapa.
// Prioridad: calle del primer punto → displayName (solo el primer tramo) → coordenadas.
export function locationName({ points = [] } = {}) {
  const street = points.find((p) => p.street)?.street;
  if (street) return street;
  const display = points.find((p) => p.displayName)?.displayName;
  if (display) return String(display).split(',')[0].trim();
  const p = points[0];
  if (p && typeof p.lat === 'number')
    return `${p.lat.toFixed(3)}, ${p.lng.toFixed(3)}`;
  return 'Sin ubicación';
}
