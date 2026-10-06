import { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import { useAuth } from './AuthContext';
import { listarProyectos, listarEscenarios } from '../api/proyectosApi';

const ProyectoContext = createContext(null);

const ACTIVE_STORAGE_KEY = 'transystem_proyecto_activo';
const ACTIVE_ESC_KEY = 'transystem_escenario_activo';

// Acepta lista de objetos [{edge_id, ...}] o un objeto {id: {...}}
function indexarMods(mods, clave) {
  const out = {};
  if (Array.isArray(mods)) {
    mods.forEach((m) => {
      if (m && m[clave] != null) out[m[clave]] = m;
    });
  } else if (mods && typeof mods === 'object') {
    Object.assign(out, mods);
  }
  return out;
}

export function ProyectoProvider({ children }) {
  const { user } = useAuth();
  const [proyectos, setProyectos] = useState([]);
  const [activoId, setActivoId] = useState(() => localStorage.getItem(ACTIVE_STORAGE_KEY));
  const [escenarios, setEscenarios] = useState([]);
  const [escActivoId, setEscActivoId] = useState(() => localStorage.getItem(ACTIVE_ESC_KEY));
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(null);

  // NUEVO: visibilidad de la capa SUMO (antes vivía local en MapContainer)
  const [capaSumoVisible, setCapaSumoVisible] = useState(false);

  const recargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const data = await listarProyectos();
      setProyectos(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('[ProyectoContext] No se pudieron cargar los proyectos:', err);
      setError(err.message);
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    if (user) recargar();
    else setProyectos([]);
  }, [user, recargar]);

  const proyectoActivo = useMemo(
    () => proyectos.find((p) => String(p.id) === String(activoId)) ?? proyectos[0] ?? null,
    [proyectos, activoId]
  );
  const proyectoId = proyectoActivo?.id ?? null;

  const recargarEscenarios = useCallback(async () => {
    if (proyectoId == null) {
      setEscenarios([]);
      return;
    }
    try {
      const data = await listarEscenarios(proyectoId);
      setEscenarios(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('[ProyectoContext] No se pudieron cargar los escenarios:', err);
      setEscenarios([]);
    }
  }, [proyectoId]);

  useEffect(() => {
    recargarEscenarios();
  }, [recargarEscenarios]);

  const escenarioActivo = useMemo(
    () => escenarios.find((e) => String(e.id) === String(escActivoId)) ?? escenarios[0] ?? null,
    [escenarios, escActivoId]
  );

  const modsEdges = useMemo(
    () => indexarMods(escenarioActivo?.modificaciones_edges, 'edge_id'),
    [escenarioActivo]
  );
  const modsSemaforos = useMemo(
    () => indexarMods(escenarioActivo?.modificaciones_semaforos, 'tls_id'),
    [escenarioActivo]
  );

  const seleccionarProyecto = useCallback((id) => {
    localStorage.setItem(ACTIVE_STORAGE_KEY, String(id));
    setActivoId(String(id));
  }, []);

  const seleccionarEscenario = useCallback((id) => {
    localStorage.setItem(ACTIVE_ESC_KEY, String(id));
    setEscActivoId(String(id));
  }, []);

  const value = {
    proyectos, proyectoActivo, seleccionarProyecto, recargar, cargando, error,
    escenarios, escenarioActivo, seleccionarEscenario, recargarEscenarios,
    modsEdges, modsSemaforos,
    capaSumoVisible, setCapaSumoVisible,
  };

  return <ProyectoContext.Provider value={value}>{children}</ProyectoContext.Provider>;
}

export function useProyecto() {
  const context = useContext(ProyectoContext);
  if (!context) throw new Error('useProyecto debe usarse dentro de un ProyectoProvider');
  return context;
}