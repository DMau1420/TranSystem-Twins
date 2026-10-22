// src/components/editor/SimulationResultsModal.jsx
// Calca el mockup compartido: tarjeta centrada sobre el mapa con el nombre
// del escenario, 5 métricas, un aviso sobre variabilidad, y CERRAR.
//
// ⚠️ Nombres de campo del resultado: el README solo documenta
// tiempo_promedio_espera / velocidad_promedio / longitud_max_fila /
// vehiculos_atendidos. El mockup muestra una métrica más ("Tiempo prom. de
// recorrido") que no está en esa lista. Como no hay un /resultados real
// todavía para confirmar el shape exacto, cada fila prueba varios nombres de
// llave posibles (ver RESULT_FIELDS) — ajusta la lista de alias en cuanto
// veas la respuesta real del backend.
import { sysCore } from '../../styles/sysCore';

const overlayStyle = {
  position: 'fixed', // cubre toda la pantalla, no solo el panel lateral de 360px donde vive este componente
  inset: 0,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  background: 'rgba(5, 6, 9, 0.45)',
  zIndex: 1500,
};

const cardStyle = {
  width: 360,
  background: sysCore.color.panel,
  border: `1px solid ${sysCore.color.borderStrong}`,
  borderRadius: 6,
  padding: '20px 22px',
  fontFamily: sysCore.font.mono,
  color: sysCore.color.ink,
  boxShadow: '0 0 30px rgba(45, 227, 255, 0.1)',
};

const titleStyle = {
  fontSize: 15,
  fontWeight: 700,
  color: sysCore.color.ink,
  marginBottom: 4,
};

const subtitleStyle = {
  fontSize: 11.5,
  color: sysCore.color.inkMuted,
  marginBottom: 16,
};

const rowStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'baseline',
  padding: '9px 0',
  borderBottom: `1px solid ${sysCore.color.border}`,
  fontSize: 12.5,
};

const rowLabelStyle = { color: sysCore.color.ink };
const rowValueStyle = { color: sysCore.color.cyan, fontWeight: 700 };

const noteStyle = {
  marginTop: 14,
  fontSize: 10.5,
  lineHeight: 1.5,
  color: '#ffb020', // amber — mismo tono de aviso que el resto de SYS_CORE
};

const closeButtonStyle = {
  width: '100%',
  marginTop: 16,
  padding: '10px 0',
  background: 'rgba(45, 227, 255, 0.12)',
  color: sysCore.color.cyan,
  border: `1px solid ${sysCore.color.borderStrong}`,
  borderRadius: 4,
  cursor: 'pointer',
  fontFamily: sysCore.font.mono,
  fontSize: 11.5,
  fontWeight: 700,
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
};

// [etiqueta, [llaves posibles en orden de preferencia], unidad]
const RESULT_FIELDS = [
  ['Vehículos atendidos', ['vehiculos_atendidos'], ''],
  ['Tiempo prom. de recorrido', ['tiempo_promedio_recorrido', 'tiempo_recorrido_promedio'], 's'],
  ['Espera promedio', ['espera_promedio', 'tiempo_promedio_espera'], 's'],
  ['Velocidad promedio', ['velocidad_promedio'], 'km/h'],
  ['Fila máxima', ['fila_maxima', 'longitud_max_fila'], ''],
];

function pick(resultado, keys) {
  for (const k of keys) {
    if (resultado[k] !== undefined && resultado[k] !== null) return resultado[k];
  }
  return undefined;
}

const fmt = (v) => (typeof v === 'number' ? v.toLocaleString('es-MX', { maximumFractionDigits: 2 }) : v);

export default function SimulationResultsModal({ scenarioName, resultado, onClose }) {
  if (!resultado) return null;

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div style={cardStyle} onClick={(e) => e.stopPropagation()}>
        <div style={titleStyle}>Resultados de la simulación</div>
        <div style={subtitleStyle}>Escenario: {scenarioName}</div>

        {RESULT_FIELDS.map(([label, keys, unit]) => {
          const value = pick(resultado, keys);
          if (value === undefined) return null;
          return (
            <div key={label} style={rowStyle}>
              <span style={rowLabelStyle}>{label}</span>
              <span style={rowValueStyle}>
                {fmt(value)}
                {unit ? ` ${unit}` : ''}
              </span>
            </div>
          );
        })}

        <div style={noteStyle}>
          Los números pueden variar un poco entre corridas del mismo escenario
          (la demanda aún no usa semilla fija).
        </div>

        <button style={closeButtonStyle} onClick={onClose}>
          CERRAR
        </button>
      </div>
    </div>
  );
}