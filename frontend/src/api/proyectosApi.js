// src/api/proyectosApi.js
// Endpoints del backend para Proyectos
// Usa authFetch de http.js para mantener el patrón centralizado de auth.
import { authFetch } from './http';

// ─── Proyectos ────────────────────────────────────────────────────────────────

/** GET /proyectos/ → lista de proyectos del usuario autenticado */
export const listarProyectos = (token) =>
  authFetch('/proyectos/', { token });

/** GET /proyectos/:id → proyecto por ID */
export const obtenerProyecto = (token, id) =>
  authFetch(`/proyectos/${id}`, { token });

/** POST /proyectos/crear → crea un nuevo proyecto */
export const crearProyecto = (token, payload) =>
  authFetch('/proyectos/crear', {
    token,
    method: 'POST',
    body: payload, // { nombre, descripcion?, geometria? }
  });

/** PUT /proyectos/modificar/:id → actualiza un proyecto */
export const actualizarProyecto = (token, id, payload) =>
  authFetch(`/proyectos/modificar/${id}`, {
    token,
    method: 'PUT',
    body: payload,
  });

/** DELETE /proyectos/:id */
export const eliminarProyecto = (token, id) =>
  authFetch(`/proyectos/${id}`, { token, method: 'DELETE' });

// ─── Escenarios (filtrados por proyecto) ─────────────────────────────────────

/**
 * GET /escenarios/?proyecto_id=:id
 * Si proyectoId es null/undefined, devuelve todos los escenarios del usuario.
 */
export const listarEscenarios = (token, proyectoId) =>
  authFetch(`/escenarios/${proyectoId != null ? `?proyecto_id=${proyectoId}` : '/'}`, { token });
