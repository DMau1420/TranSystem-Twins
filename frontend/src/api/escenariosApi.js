// src/api/escenariosApi.js — endpoints reales documentados en backend/README.md
import { authFetch } from './http';

export const listarEscenarios = (token, proyectoId) =>
  authFetch(`/escenarios/${proyectoId ? `?proyecto_id=${proyectoId}` : ''}`, { token });

export const crearEscenario = (token, payload) =>
  authFetch('/escenarios/crear', { token, method: 'POST', body: payload });

export const obtenerEscenario = (token, id) => authFetch(`/escenarios/${id}`, { token });

export const actualizarEscenario = (token, id, payload) =>
  authFetch(`/escenarios/modificar/${id}`, { token, method: 'PUT', body: payload });

export const eliminarEscenario = (token, id) =>
  authFetch(`/escenarios/${id}`, { token, method: 'DELETE' });

// Patch incremental — útil cuando conectemos el editor de infraestructura vial.
export const patchInfraestructura = (token, escenarioId, edgeId, payload) =>
  authFetch(`/escenarios/${escenarioId}/infraestructura/${edgeId}`, {
    token,
    method: 'PATCH',
    body: payload,
  });

export const patchSemaforo = (token, escenarioId, tlsId, payload) =>
  authFetch(`/escenarios/${escenarioId}/semaforo/${tlsId}`, {
    token,
    method: 'PATCH',
    body: payload,
  });