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
  const filtered = projectId
    ? all.filter((s) => s.projectId === projectId)
    : all;
  return filtered.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
}

export async function getScenario(id) {
  return readAll()[id] ?? null;
}

export async function saveScenario(scenario) {
  const saved = { ...scenario, updatedAt: new Date().toISOString() };
  const all = readAll();
  all[saved.id] = saved;
  writeAll(all);
  return saved;
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
  return Object.values(readProjects()).sort((a, b) =>
    b.updatedAt.localeCompare(a.updatedAt)
  );
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
