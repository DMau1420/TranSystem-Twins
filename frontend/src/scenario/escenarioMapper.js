// src/scenario/escenarioMapper.js
//
// Traduce entre el escenario LOCAL (points/routes/zones/edits — lo que guarda
// tu localStorage) y el escenario del BACKEND REAL (zona_geom,
// modificaciones_edges, modificaciones_semaforos, demanda_vehicular).
//
// ⚠️ SUPUESTOS que hay que confirmar con el equipo (el README no especifica
// el shape exacto de CreateEscenario/CreateProyecto; revisa /docs o pregunta
// a Mau si algo de esto no cuadra):
//   - zona_geom se manda como GeoJSON Polygon plano (no como Feature envuelto).
//   - demanda_vehicular es UN SOLO número por escenario: aquí se suma el
//     "vehiculos_por_hora" de todas las zonas marcadas. Si el backend espera
//     demanda por zona, esto hay que rehacerlo.
//   - "fases" dentro de modificaciones_semaforos usa el mismo shape que ya
//     guardas en scenario.edits.junctions[id].tls.phases ({duration, state}).
//   - duracion_segundos: no hay UI para esto todavía, se manda un default de
//     3600 (1 hora) hasta que se agregue un campo en el editor.

const DEFAULT_DURACION_SEGUNDOS = 3600;
// ⚠️ El Swagger real (ver scenario/simulacion.md) muestra el escenario de
// prueba con demanda_sintetica como ARRAY de {vehiculos_por_hora, direccion},
// no un solo demanda_vehicular. Mientras no haya POST /escenarios/crear real
// para confirmarlo, mandamos los dos formatos: el simple (demanda_vehicular,
// por si el crear real resulta parecido al README) y el de array (con una
// sola entrada, direccion genérica). Ajusta esto en cuanto exista el POST real.

// Construye un polígono GeoJSON a partir de lo marcado en el mapa:
// prioriza la primera zona dibujada; si no hay zonas, arma un bbox con todos
// los puntos/rutas disponibles.
export function buildZonaGeom(features) {
  const zone = features?.zones?.[0];
  if (zone?.geoJson) {
    return zone.geoJson.type === 'Polygon' ? zone.geoJson : zone.geoJson.geometry ?? null;
  }

  const coords = [];
  (features?.points ?? []).forEach((p) => coords.push([p.lng, p.lat]));
  (features?.routes ?? []).forEach((r) =>
    (r.coordinates ?? []).forEach(([lat, lng]) => coords.push([lng, lat]))
  );
  if (coords.length === 0) return null;

  const lons = coords.map((c) => c[0]);
  const lats = coords.map((c) => c[1]);
  const [minLon, maxLon, minLat, maxLat] = [
    Math.min(...lons), Math.max(...lons), Math.min(...lats), Math.max(...lats),
  ];
  return {
    type: 'Polygon',
    coordinates: [[
      [minLon, minLat], [maxLon, minLat], [maxLon, maxLat], [minLon, maxLat], [minLon, minLat],
    ]],
  };
}

function edgesToModificaciones(edges = {}) {
  return Object.entries(edges).map(([edge_id, e]) => ({
    edge_id,
    ...(e.lanes != null ? { carriles: e.lanes } : {}),
    ...(e.maxspeed != null ? { velocidad_max: e.maxspeed } : {}),
  }));
}

function junctionsToModificaciones(junctions = {}) {
  return Object.entries(junctions).map(([tls_id, j]) => ({
    tls_id,
    fases: j.tls?.phases ?? [],
  }));
}

// Sin usar por ahora (la demanda ya es un campo único del escenario, ver
// scenario.demandaVehicular). Se deja por si el backend termina pidiendo
// demanda por zona en vez de un total.
function sumaVehiculosPorHora(zones = []) {
  return zones.reduce((total, z) => total + (Number(z.vehiculos_por_hora) || 0), 0);
}

// scenario (local, de ScenarioContext) + features (de MapDataContext) -> payload backend
export function scenarioToEscenarioPayload(scenario, features, proyectoIdBackend) {
  return {
    proyecto_id: proyectoIdBackend,
    nombre: scenario.name,
    zona_geom: buildZonaGeom(features),
    modificaciones_edges: edgesToModificaciones(scenario.edits?.edges),
    modificaciones_semaforos: junctionsToModificaciones(scenario.edits?.junctions),
    demanda_vehicular: scenario.demandaVehicular ?? 0,
    demanda_sintetica: [
      { vehiculos_por_hora: scenario.demandaVehicular ?? 0, direccion: 'general' },
    ],
    duracion_segundos: scenario.duracionSegundos ?? DEFAULT_DURACION_SEGUNDOS,
  };
}

// scenario local -> payload de /proyectos/crear
export function scenarioToProyectoPayload(scenario, features, nombreProyecto) {
  return {
    nombre: nombreProyecto,
    descripcion: '',
    geometria: { geoJson: { type: 'Feature', geometry: buildZonaGeom(features) } },
  };
}