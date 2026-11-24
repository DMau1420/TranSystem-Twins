import { useMemo } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useScenario } from '../../scenario/ScenarioContext';
import {
  listarResultados,
  obtenerResultado,
  eliminarResultado,
} from '../../api/resultadosApi';
import ResultadosPanel from '../resultados/ResultadosPanel';
import SectionPanel from './SectionPanel';

/**
 * Pestaña "Simulaciones" del Sidebar: historial de corridas del escenario abierto en el editor (CU-14).
 *
 * El historial vive en el backend, así que necesita el id del escenario EN EL BACKEND:
 *  - scenario.backend.escenarioId : lo fija ensureEnBackend la primera vez que se simula
 *  - scenario.id numérico         : escenarios que se abrieron desde Proyectos (ya vienen del backend)
 * Un escenario creado solo en el navegador (id local) no tiene historial hasta que se sincroniza.
 *
 * VERIFICAR: que resultadosApi exporte estas 3 funciones y que reciban (token, id).
 */
export default function SimulacionesPanel({ onClose }) {
  const { token } = useAuth();
  const { scenario } = useScenario();

  const escenarioId =
    scenario?.backend?.escenarioId ?? (typeof scenario?.id === 'number' ? scenario.id : null);
  const nombre = scenario?.name || 'sin nombre';

  // IMPORTANTE: `api` debe ser estable; si se recrea en cada render,
  // ResultadosPanel vuelve a pedir la lista en bucle.
  const api = useMemo(
    () => ({
      listarResultados: (id) => listarResultados(token, id),
      obtenerResultado: (id) => obtenerResultado(token, id),
      eliminarResultado: (id) => eliminarResultado(token, id),
    }),
    [token],
  );

  return (
    <SectionPanel tag="// SIM_ST // SIMULACIONES" title="Historial de corridas" onClose={onClose}>
      {escenarioId ? (
        <ResultadosPanel escenarioId={escenarioId} api={api} />
      ) : (
        <div className="tst-projects__status">
          <p style={{ margin: '0 0 8px' }}>
            El escenario <strong>{nombre}</strong> todavía no está sincronizado con el backend, así
            que no tiene historial de corridas.
          </p>
          <p style={{ margin: 0 }}>
            Pulsa <strong>SIMULAR ESCENARIO</strong>: al simular se crea en el backend y este panel
            se actualiza solo. Si no se crea, revisa la consola (F12) por el aviso
            «No se pudo sincronizar con el backend».
          </p>
        </div>
      )}
    </SectionPanel>
  );
}