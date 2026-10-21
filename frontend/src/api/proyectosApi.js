// src/api/proyectosApi.js — endpoints reales documentados en backend/README.md
import { authFetch } from './http';

export const listarProyectos = (token) => authFetch('/proyectos/', { token });

export const crearProyecto = (token, payload) =>
  authFetch('/proyectos/crear', { token, method: 'POST', body: payload });

export const obtenerProyecto = (token, id) => authFetch(`/proyectos/${id}`, { token });

export const actualizarProyecto = (token, id, payload) =>
  authFetch(`/proyectos/modificar/${id}`, { token, method: 'PUT', body: payload });

export const eliminarProyecto = (token, id) =>
  authFetch(`/proyectos/${id}`, { token, method: 'DELETE' });