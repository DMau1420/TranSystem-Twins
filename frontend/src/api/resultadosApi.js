// src/api/resultadosApi.js
// Endpoints del backend para Resultados de simulación.
// Endpoints documentados en backend/routers/r_resultados.py:
//   GET    /resultados/                → lista (filtrables por escenario_id)
//   GET    /resultados/:id             → por ID
//   POST   /resultados/crear           → registrar un resultado nuevo
//   DELETE /resultados/:id             → eliminar un resultado
import { authFetch } from './http';

/**
 * GET /resultados/
 * Lista los resultados del usuario. Si escenarioId es provisto, filtra por escenario.
 * @param {string} token
 * @param {number|null} [escenarioId]
 */
export const listarResultados = (token, escenarioId) =>
  authFetch(
    `/resultados/${escenarioId != null ? `?escenario_id=${escenarioId}` : '/'}`,
    { token }
  );

/**
 * GET /resultados/:id
 */
export const obtenerResultado = (token, id) =>
  authFetch(`/resultados/${id}`, { token });

/**
 * POST /resultados/crear
 * Registra manualmente un resultado de simulación.
 * payload: {
 *   escenario_id: number,
 *   tiempo_promedio_espera?: number,
 *   velocidad_promedio?: number,
 *   longitud_max_fila?: number,
 *   vehiculos_atendidos?: number,
 *   reporte_pdf_url?: string,
 * }
 */
export const crearResultado = (token, payload) =>
  authFetch('/resultados/crear', { token, method: 'POST', body: payload });

/**
 * DELETE /resultados/:id
 */
export const eliminarResultado = (token, id) =>
  authFetch(`/resultados/${id}`, { token, method: 'DELETE' });
