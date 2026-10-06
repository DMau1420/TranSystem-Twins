const RAW_API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';
const API_BASE = RAW_API_BASE.endsWith('/') ? RAW_API_BASE.slice(0, -1) : RAW_API_BASE;

// Misma llave que usa AuthContext
const TOKEN_STORAGE_KEY = 'transystem_token';

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

function mensajeDeError(data, status) {
  if (typeof data?.detail === 'string') return data.detail;
  if (Array.isArray(data?.detail)) return data.detail.map((d) => d.msg).join(', ');
  return `Error ${status}`;
}

async function authFetch(path, options = {}) {
  const token = localStorage.getItem(TOKEN_STORAGE_KEY);
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, mensajeDeError(data, res.status));
  return data;
}

// OJO: con barra final. Sin ella FastAPI responde 307 y el navegador
// pierde el token y se salta el proxy.
export function listarProyectos() {
  return authFetch('/proyectos/');
}

// 409 = el proyecto todavía no tiene red importada (se importa al simular por primera vez)
export function obtenerRed(proyectoId, signal) {
  return authFetch(`/proyectos/${proyectoId}/red`, { signal });
}

export function crearProyecto({ nombre, descripcion, geometria }) {
  return authFetch('/proyectos/crear', {
    method: 'POST',
    body: JSON.stringify({
      nombre,
      descripcion: descripcion || null,
      ...(geometria ? { geometria } : {}),
    }),
  });
}

export function listarEscenarios(proyectoId) {
  return authFetch(`/escenarios/proyecto/${proyectoId}`);
}

// encodeURIComponent convierte el '#' de "128255275#2" en %23
export function modificarEdge(escenarioId, edgeId, datos) {
  return authFetch(`/escenarios/${escenarioId}/infraestructura/${encodeURIComponent(edgeId)}`, {
    method: 'PATCH',
    body: JSON.stringify(datos), // { carriles, velocidad_max }
  });
}

export function modificarSemaforo(escenarioId, tlsId, fases) {
  return authFetch(`/escenarios/${escenarioId}/semaforo/${encodeURIComponent(tlsId)}`, {
    method: 'PATCH',
    body: JSON.stringify({ fases }), // [{ indice, duracion, estado }]
  });
}

export function importarProyecto(proyectoId) {
  // In TranSystem-Twins, simular implicitly imports the network
  return Promise.resolve();
}

export function crearEscenario({ proyecto_id, nombre, demanda_vehicular = 100, duracion_segundos = 3600 }) {
  return authFetch('/escenarios/crear', {
    method: 'POST',
    body: JSON.stringify({ proyecto_id, nombre, demanda_vehicular, duracion_segundos }),
  });
}

export async function simularEscenario(escenarioId) {
  const res = await authFetch(`/simular`, { method: 'POST', body: JSON.stringify({ escenario_id: escenarioId }) });
  return res && typeof res.json === 'function' ? await res.json() : res;
}