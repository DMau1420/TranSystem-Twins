const API_BASE = import.meta.env.VITE_API_BASE_URL;
console.log('API_BASE:', API_BASE);

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
