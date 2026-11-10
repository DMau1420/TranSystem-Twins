// src/api/escenariosApi.js
// Endpoints del backend para Escenarios
// Usa authFetch de http.js con patrón (token, payload) consistente.
import { authFetch } from './http';

// ─── CRUD ─────────────────────────────────────────────────────────────────────

/**
 * GET /escenarios/ → lista de escenarios.
 * Si proyectoId es null/undefined, devuelve todos los del usuario.
 */
export const listarEscenarios = (token, proyectoId) =>
  authFetch(`/escenarios/${proyectoId != null ? `?proyecto_id=${proyectoId}` : '/'}`, { token });

/** GET /escenarios/:id */
export const obtenerEscenario = (token, id) =>
  authFetch(`/escenarios/${id}`, { token });

/**
 * POST /escenarios/crear
 * payload: { proyecto_id, nombre, zona_geom?, demanda_vehicular?, duracion_segundos?, ... }
 */
export const crearEscenario = (token, payload) =>
  authFetch('/escenarios/crear', { token, method: 'POST', body: payload });

/**
 * PUT /escenarios/modificar/:id
 * payload: { nombre?, zona_geom?, ... }
 */
export const actualizarEscenario = (token, id, payload) =>
  authFetch(`/escenarios/modificar/${id}`, { token, method: 'PUT', body: payload });

/** DELETE /escenarios/:id */
export const eliminarEscenario = (token, id) =>
  authFetch(`/escenarios/${id}`, { token, method: 'DELETE' });

// ─── Infraestructura y semáforos ──────────────────────────────────────────────

/**
 * PATCH /escenarios/:escenarioId/infraestructura/:edgeId
 * payload: { carriles, velocidad_max }
 */
export const patchInfraestructura = (token, escenarioId, edgeId, payload) =>
  authFetch(
    `/escenarios/${escenarioId}/infraestructura/${encodeURIComponent(edgeId)}`,
    { token, method: 'PATCH', body: payload }
  );

/**
 * PATCH /escenarios/:escenarioId/semaforo/:tlsId
 * payload: { fases: [{ indice, duracion?, estado? }] }
 */
export const patchSemaforo = (token, escenarioId, tlsId, payload) =>
  authFetch(
    `/escenarios/${escenarioId}/semaforo/${encodeURIComponent(tlsId)}`,
    { token, method: 'PATCH', body: payload }
  );