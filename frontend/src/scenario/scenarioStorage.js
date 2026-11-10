// src/scenario/scenarioStorage.js
// Adaptador de persistencia. Todas las funciones son async a propósito:
// cuando el backend esté listo, solo cambias el interior por fetch('/api/scenarios...')
// y nada más del frontend se entera.

import { newId } from './scenarioSchema';

const KEY = 'tst:scenarios';
const PROJECTS_KEY = 'tst:projects';

const readAll = () => {
  try {
    return JSON.parse(localStorage.getItem(KEY)) ?? {};
  } catch {
    return {};
  }
};

const writeAll = (all) => localStorage.setItem(KEY, JSON.stringify(all));

export async function listScenarios({ projectId } = {}) {
  const all = Object.values(readAll());
  const filtered = projectId ? all.filter((s) => s.projectId === projectId) : all;
  return filtered.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
}

export function geomToFeatures(geom) {
  if (!geom) return { points: [], routes: [], zones: [] };
  let polygon = geom;
  if (geom.type === 'Feature' && geom.geometry) polygon = geom.geometry;
  if (polygon.type === 'Polygon' && Array.isArray(polygon.coordinates)) {
    const coords = polygon.coordinates[0]?.map((pt) => {
      if (Array.isArray(pt)) return { lat: pt[1], lng: pt[0] };
      return pt;
    }) || [];
    if (coords.length > 0) {
      return {
        points: [],
        routes: [],
        zones: [{
          id: 'zone_primary',
          coordinates: coords,
          geoJson: polygon,
          vehiculos_por_hora: 100,
        }],
      };
    }
  }
  return { points: [], routes: [], zones: [] };
}

export function indexarEdges(mods = []) {
  const edges = {};
  if (Array.isArray(mods)) {
    mods.forEach((m) => {
      if (m && m.edge_id) {
        edges[m.edge_id] = {
          lanes: m.carriles,
          maxspeed: m.velocidad_max,
        };
      }
    });
  }
  return edges;
}

export function indexarJunctions(mods = []) {
  const junctions = {};
  if (Array.isArray(mods)) {
    mods.forEach((m) => {
      if (m && m.tls_id) {
        junctions[m.tls_id] = {
          tls: { phases: m.fases || [] },
        };
      }
    });
  }
  return junctions;
}

export function normalizeScenario(s, projectId = null) {
  if (!s) return null;
  const pId = projectId ?? s.proyecto_id ?? s.projectId ?? null;
  const edges = indexarEdges(s.modificaciones_edges);
  const junctions = indexarJunctions(s.modificaciones_semaforos);
  const edits = s.edits ? { edges: { ...edges, ...s.edits.edges }, junctions: { ...junctions, ...s.edits.junctions } } : { edges, junctions };
  const features = s.features && (s.features.points || s.features.routes || s.features.zones)
    ? s.features
    : geomToFeatures(s.zona_geom);

  return {
    id: s.id,
    projectId: pId,
    proyecto_id: pId,
    name: s.nombre || s.name || 'Escenario 1',
    version: 1,
    createdAt: s.fecha_creacion || s.createdAt || new Date().toISOString(),
    updatedAt: s.fecha_creacion || s.updatedAt || new Date().toISOString(),
    area: s.zona_geom || s.area || null,
    features,
    network: s.network || { source: 'osm', importedAt: null },
    backend: { proyectoId: pId, escenarioId: s.id },
    demandaVehicular: s.demanda_vehicular ?? s.demandaVehicular ?? 100,
    duracionSegundos: s.duracion_segundos ?? s.duracionSegundos ?? 3600,
    ultimoResultado: s.resultado ?? s.ultimoResultado ?? null,
    edits,
  };
}

export async function getScenario(id) {
<<<<<<< HEAD
  return readAll()[id] ?? null;
=======
  const token = getToken();
  if (token) {
    try {
      const res = await fetch(`${API_BASE}/escenarios/${id}`, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) {
        const s = await res.json();
        return normalizeScenario(s);
      }
    } catch (e) {
      console.warn("Fallo getScenario backend", e);
    }
  }
  const local = readAll()[id];
  return local ? normalizeScenario(local) : null;
>>>>>>> prueba
}

export async function saveScenario(scenario) {
  const saved = { ...scenario, updatedAt: new Date().toISOString() };
<<<<<<< HEAD
=======
  if (token) {
    try {
      let res;
      const isNew = !scenario.id || typeof scenario.id === 'string';
      let zonaGeom = saved.zona_geom;
      if (!zonaGeom && saved.features?.zones?.[0]?.geoJson) {
        zonaGeom = saved.features.zones[0].geoJson;
      }
      const payload = {
        nombre: saved.name || saved.nombre,
        zona_geom: zonaGeom || null,
        proyecto_id: saved.projectId || saved.proyecto_id,
        demanda_vehicular: saved.demandaVehicular ?? 100,
        duracion_segundos: saved.duracionSegundos ?? 3600,
      };
      
      if (isNew) {
        res = await fetch(`${API_BASE}/escenarios/crear`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify(payload)
        });
      } else {
        res = await fetch(`${API_BASE}/escenarios/modificar/${saved.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify(payload)
        });
      }
      
      if (res.ok) {
        const s = await res.json();
        return normalizeScenario({ ...saved, ...s });
      }
    } catch (e) {
      console.warn("Fallo saveScenario backend", e);
    }
  }

>>>>>>> prueba
  const all = readAll();
  all[saved.id] = saved;
  writeAll(all);
  return normalizeScenario(saved);
}

export async function deleteScenario(id) {
  const all = readAll();
  delete all[id];
  writeAll(all);
}

// ── Proyectos (modo local, mientras el backend no responde) ──────────────────
const readProjects = () => {
  try {
    return JSON.parse(localStorage.getItem(PROJECTS_KEY)) ?? {};
  } catch {
    return {};
  }
};

export async function listProjects() {
  return Object.values(readProjects()).sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
}

export async function saveProject(project) {
  const now = new Date().toISOString();
  const saved = {
    description: '',
    ...project,
    id: project.id ?? newId('prj'),
    createdAt: project.createdAt ?? now,
    updatedAt: now,
  };
  const all = readProjects();
  all[saved.id] = saved;
  localStorage.setItem(PROJECTS_KEY, JSON.stringify(all));
  return saved;
}

export async function renameScenario(id, name) {
  const scenario = await getScenario(id);
  if (!scenario) return null;
  return saveScenario({ ...scenario, name });
}

// Borra el proyecto y, en cascada, todos sus escenarios (irreversible).
export async function deleteProject(id) {
  const its = await listScenarios({ projectId: id });
  const scenarios = readAll();
  its.forEach((s) => delete scenarios[s.id]);
  writeAll(scenarios);

  const projects = readProjects();
  delete projects[id];
  localStorage.setItem(PROJECTS_KEY, JSON.stringify(projects));
}

// Copia un escenario dentro del MISMO proyecto, con id nuevo y nombre "(copia)".
export async function duplicateScenario(id) {
  const original = await getScenario(id);
  if (!original) return null;
  const now = new Date().toISOString();
  return saveScenario({
    ...original,
    id: newId(),
    name: `${original.name} (copia)`,
    createdAt: now,
  });
}

// ── Escenario activo (para resumir al recargar la página) ───────────────────
const ACTIVE_SCENARIO_KEY = 'tst:activeScenarioId';

export function markActiveScenario(id) {
  try {
    if (id) localStorage.setItem(ACTIVE_SCENARIO_KEY, id);
    else localStorage.removeItem(ACTIVE_SCENARIO_KEY);
  } catch {
    /* sin almacenamiento disponible: no pasa nada, solo no se recuerda */
  }
}

export function getActiveScenarioId() {
  try {
    return localStorage.getItem(ACTIVE_SCENARIO_KEY);
  } catch {
    return null;
  }
}