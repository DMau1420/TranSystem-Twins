import { createContext, useContext, useMemo, useEffect, useRef } from 'react';
import { useAuth } from './AuthContext';
import { useScenario } from '../scenario/ScenarioContext';
import { useMapData } from './MapDataContext';
import { useSimulacion } from '../scenario/useSimulacion';

const SimulacionContext = createContext(null);

export function SimulacionProvider({ children }) {
  const { token } = useAuth();
  const { scenario, save, setResultado } = useScenario();
  const { points, routes, zones } = useMapData();
  const features = useMemo(() => ({ points, routes, zones }), [points, routes, zones]);

  const sim = useSimulacion({
    token,
    scenario,
    features,
    nombreProyectoLocal: scenario?.name || 'Proyecto',
    save,
  });

  const ultimoGuardadoRef = useRef(null);

  // Guardar resultado automáticamente cuando se complete (UNA SOLA VEZ por simulación)
  useEffect(() => {
    if (
      sim.estado === 'completado' &&
      sim.resultado &&
      ultimoGuardadoRef.current !== sim.resultado
    ) {
      ultimoGuardadoRef.current = sim.resultado;
      setResultado(sim.resultado);
      save({ ultimoResultado: sim.resultado });
    }
  }, [sim.estado, sim.resultado, setResultado, save]);

  // Si se vuelve a iniciar o se limpia, resetear la referencia
  useEffect(() => {
    if (sim.estado === 'idle' || sim.estado === 'sincronizando') {
      ultimoGuardadoRef.current = null;
    }
  }, [sim.estado]);

  const running = sim.estado === 'sincronizando' || sim.estado === 'conectando' || sim.estado === 'simulando';

  const value = useMemo(
    () => ({
      ...sim,
      running,
      features,
    }),
    [sim, running, features]
  );

  return <SimulacionContext.Provider value={value}>{children}</SimulacionContext.Provider>;
}

export function useSimulacionContext() {
  const context = useContext(SimulacionContext);
  if (!context) {
    throw new Error('useSimulacionContext debe usarse dentro de un SimulacionProvider');
  }
  return context;
}
