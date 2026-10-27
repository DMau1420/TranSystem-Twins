// src/api/simulacionApi.js
// Endpoints del backend para Simulación (HTTP + WebSocket).
// El WebSocket se maneja directamente en useSimulacion.js con WS_BASE de config.js.
import { authFetch } from './http';
import { WS_BASE } from './config';

// ─── HTTP ─────────────────────────────────────────────────────────────────────

/**
 * POST /simular
 * Lanza una simulación de forma síncrona (alternativa al WebSocket).
 * payload: { escenario_id: number }
 */
export const iniciarSimulacion = (token, payload) =>
  authFetch('/simular', { token, method: 'POST', body: payload });

/**
 * GET /red
 * Retorna la red vial importada para la simulación activa.
 */
export const obtenerRed = (token) =>
  authFetch('/red', { token });

/**
 * GET /resultado
 * Retorna el resultado de la última simulación completada.
 */
export const obtenerResultadoSimulacion = (token) =>
  authFetch('/resultado', { token });

/**
 * PATCH /infraestructura/:edgeId
 * Modifica un tramo de la red en el motor de simulación activo.
 * datos: { carriles?, velocidad_max? }
 */
export const patchInfraestructuraSimulacion = (token, edgeId, datos) =>
  authFetch(`/infraestructura/${encodeURIComponent(edgeId)}`, {
    token,
    method: 'PATCH',
    body: datos,
  });

/**
 * PATCH /semaforo/:tlsId
 * Modifica un semáforo en el motor de simulación activo.
 */
export const patchSemaforoSimulacion = (token, tlsId, datos) =>
  authFetch(`/semaforo/${encodeURIComponent(tlsId)}`, {
    token,
    method: 'PATCH',
    body: datos,
  });

// ─── WebSocket ────────────────────────────────────────────────────────────────

/**
 * Crea un WebSocket de simulación ya autenticado.
 * El backend espera que el primer mensaje enviado sea:
 *   { escenario_id: number }
 *
 * Mensajes recibidos del servidor:
 *   { status: string, progress?: number, resultado?: object, detail?: string }
 *
 * @param {string} token - JWT del usuario autenticado.
 * @returns {WebSocket}
 */
export function crearWebSocketSimulacion(token) {
  // Si el backend requiere el token en la query string del WS:
  const url = token
    ? `${WS_BASE}/ws/simular?token=${encodeURIComponent(token)}`
    : `${WS_BASE}/ws/simular`;
  return new WebSocket(url);
}
