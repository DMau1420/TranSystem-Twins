// src/api/http.js
import { API_BASE } from './config';

export class ApiError extends Error {
  constructor(message, status, body) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

// token viene de useAuth() (AuthContext) — mismo patrón que AccountMenu/ProjectsPanel.
export async function authFetch(path, { token, method = 'GET', body } = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      ...(body ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let detail = null;
    try {
      detail = await res.json();
    } catch {
      /* respuesta sin cuerpo JSON */
    }
    throw new ApiError(
      detail?.detail ?? `${method} ${path} -> ${res.status}`,
      res.status,
      detail
    );
  }

  if (res.status === 204) return null; // DELETE sin contenido
  return res.json();
}