const RAW_API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';
const API_BASE = RAW_API_BASE.endsWith('/') ? RAW_API_BASE.slice(0, -1) : RAW_API_BASE;

export async function createPoints(payload) {
  const response = await fetch(`${API_BASE}/points`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(
      errorBody ? JSON.stringify(errorBody) : `Error ${response.status}`
    );
  }

  return response.json();
}

export async function listPoints() {
  const response = await fetch(`${API_BASE}/points`);
  if (!response.ok) throw new Error(`Error ${response.status}`);
  return response.json();
}
