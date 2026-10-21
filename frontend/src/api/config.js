// src/api/config.js
// El frontend habla DIRECTO con el backend (puerto 8000), sin proxy /api de por
// medio — así está en el docker-compose y en el diagrama del README del backend.
// Ajusta VITE_API_URL en tu .env si tu backend corre en otro host/puerto.
export const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

// ws://localhost:8000 a partir de la misma base (sirve tanto en http como https)
export const WS_BASE = API_BASE.replace(/^http/, 'ws');