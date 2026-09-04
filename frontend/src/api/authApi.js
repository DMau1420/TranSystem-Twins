const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';
const BASE_URL = API_BASE.endsWith('/') ? API_BASE.slice(0, -1) : API_BASE;

/**
 * Autentica al usuario en el backend FastAPI
 * @param {{ correo: string, password: string }} credentials
 * @returns {Promise<{ access_token: string, token_type: string }>}
 */
export async function loginApi({ correo, password }) {
  const response = await fetch(`${BASE_URL}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ correo, password }),
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    let errorMsg = 'Error al iniciar sesión.';
    if (data?.detail) {
      if (typeof data.detail === 'string') {
        errorMsg = data.detail;
      } else if (Array.isArray(data.detail)) {
        errorMsg = data.detail.map((err) => err.msg || err.message).join(', ');
      }
    }
    throw new Error(errorMsg);
  }

  return data;
}

/**
 * Registra un nuevo usuario en la base de datos a través de FastAPI
 * @param {{ nombre: string, apodo?: string, correo: string, password: string, rol?: string }} userData
 * @returns {Promise<{ id: string, nombre: string, apodo?: string, correo: string, rol: string }>}
 */
export async function registerApi({ nombre, apodo, correo, password, rol = 'Investigador' }) {
  const response = await fetch(`${BASE_URL}/auth/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      nombre,
      apodo: apodo || null,
      correo,
      password,
      rol,
    }),
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    let errorMsg = 'Error al registrar la cuenta.';
    if (data?.detail) {
      if (typeof data.detail === 'string') {
        errorMsg = data.detail;
      } else if (Array.isArray(data.detail)) {
        errorMsg = data.detail.map((err) => err.msg || err.message).join(', ');
      }
    }
    throw new Error(errorMsg);
  }

  return data;
}
