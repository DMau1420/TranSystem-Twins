// src/scenario/scenarioStorage.js
// Adaptador de persistencia.

import { newId } from './scenarioSchema';

const RAW_API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';
const API_BASE = RAW_API_BASE.endsWith('/') ? RAW_API_BASE.slice(0, -1) : RAW_API_BASE;

const getToken = () => localStorage.getItem('transystem_token');

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
  const token = getToken();
  if (token) {
    try {
      const url = projectId ? `${API_BASE}/escenarios/?proyecto_id=${projectId}` : `${API_BASE}/escenarios/`;
      const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) {
        const data = await res.json();
        const arr = Array.isArray(data) ? data : data.scenarios ?? [];
        return arr.map(s => ({ ...s, name: s.nombre, updatedAt: s.fecha_creacion })).sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
      }
    } catch (e) {
      console.warn("Fallo listScenarios backend", e);
    }
  }

  // Fallback local
  const all = Object.values(readAll());
  const filtered = projectId
    ? all.filter((s) => s.projectId === projectId)
    : all;
  return filtered.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
}

export async function getScenario(id) {
  const token = getToken();
  if (token) {
    try {
      const res = await fetch(`${API_BASE}/escenarios/${id}`, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) {
        const s = await res.json();
        return { ...s, name: s.nombre, updatedAt: s.fecha_creacion };
      }
    } catch (e) {
      console.warn("Fallo getScenario backend", e);
    }
  }
  return readAll()[id] ?? null;
}

export async function saveScenario(scenario) {
  const token = getToken();
  const saved = { ...scenario, updatedAt: new Date().toISOString() };
  if (token) {
    try {
      let res;
      // Asume que si no tiene id numerico es nuevo, o si es string como tst_...
      const isNew = !scenario.id || typeof scenario.id === 'string';
      const payload = {
        nombre: saved.name || saved.nombre,
        zona_geom: saved.zona_geom || saved.features,
        proyecto_id: saved.projectId
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
        return { ...s, ...saved, id: s.id, name: s.nombre, updatedAt: s.fecha_creacion };
      }
    } catch (e) {
      console.warn("Fallo saveScenario backend", e);
    }
  }

  const all = readAll();
  all[saved.id] = saved;
  writeAll(all);
  return saved;
}

export async function deleteScenario(id) {
  const token = getToken();
  if (token) {
    try {
      const res = await fetch(`${API_BASE}/escenarios/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) return;
    } catch (e) {
      console.warn("Fallo deleteScenario backend", e);
    }
  }

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
  const token = getToken();
  if (token) {
    try {
      const res = await fetch(`${API_BASE}/proyectos/`, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) {
        const data = await res.json();
        const arr = Array.isArray(data) ? data : data.projects ?? [];
        return arr.map(p => ({ ...p, name: p.nombre, description: p.descripcion, updatedAt: p.fecha_creacion })).sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
      }
    } catch (e) {
      console.warn("Fallo listProjects backend", e);
    }
  }

  return Object.values(readProjects()).sort((a, b) =>
    b.updatedAt.localeCompare(a.updatedAt)
  );
}

export async function saveProject(project) {
  const token = getToken();
  const now = new Date().toISOString();
  
  if (token) {
    try {
      let res;
      const isNew = !project.id || typeof project.id === 'string';
      const payload = {
        nombre: project.name || project.nombre,
        descripcion: project.description || project.descripcion || ''
      };
      
      if (isNew) {
        res = await fetch(`${API_BASE}/proyectos/crear`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify(payload)
        });
      } else {
        res = await fetch(`${API_BASE}/proyectos/modificar/${project.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify(payload)
        });
      }
      
      if (res.ok) {
        const p = await res.json();
        return { ...p, ...project, id: p.id, name: p.nombre, description: p.descripcion, updatedAt: p.fecha_creacion };
      }
    } catch (e) {
      console.warn("Fallo saveProject backend", e);
    }
  }

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

export async function deleteProject(id) {
  const token = getToken();
  if (token) {
    try {
      const res = await fetch(`${API_BASE}/proyectos/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) return;
    } catch (e) {
      console.warn("Fallo deleteProject backend", e);
    }
  }

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
