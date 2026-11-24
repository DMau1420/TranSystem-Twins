import { useMapTheme } from '../../context/MapThemeContext';
import SectionPanel from './SectionPanel';

// Paneles mínimos para que las pestañas dejen de ser un console.log.
// Muestran estados vacíos honestos; se llenan cuando existan los datos reales.

export function RutasPanel({ onClose }) {
  return (
    <SectionPanel tag="// RUT_NET // RUTAS" title="Rutas" onClose={onClose}>
      <div className="tst-projects__status">
        Aún no hay rutas definidas. Aquí se listarán las rutas y los flujos origen-destino del
        escenario activo.
      </div>
    </SectionPanel>
  );
}

export function NotificacionesPanel({ onClose }) {
  return (
    <SectionPanel tag="// COMM_NET // NOTIFICACIONES" title="Notificaciones" onClose={onClose}>
      <div className="tst-projects__status">No tienes notificaciones nuevas.</div>
    </SectionPanel>
  );
}

export function ConfigPanel({ onClose }) {
  const { mapStyle, toggleMapStyle } = useMapTheme();
  const isDark = mapStyle === 'dark';

  return (
    <SectionPanel tag="// CONF_SYS // CONFIGURACIÓN" title="Configuración" onClose={onClose}>
      <label className="tst-projects__label" htmlFor="cfg-mapstyle">
        // ESTILO_DE_MAPA
      </label>
      <button
        id="cfg-mapstyle"
        type="button"
        className="tst-projects__btn tst-projects__btn--cyan"
        onClick={toggleMapStyle}
        aria-pressed={isDark}
        style={{ width: '100%' }}
      >
        {isDark ? 'Mapa oscuro (cambiar a claro)' : 'Mapa claro (cambiar a oscuro)'}
      </button>
    </SectionPanel>
  );
}