// src/components/editor/VehicleQuickAdd.jsx
// Botones rápidos para subir la demanda vehicular del escenario, en vez de
// escribirla a mano. Va debajo del botón SIMULAR en SimularPanel.
import { sysCore } from '../../styles/sysCore';
import { useScenario } from '../../scenario/ScenarioContext';

// Un color distinto por cantidad, para distinguirlos de un vistazo.
// No son los 3 colores de sysCore (cyan/magenta/amber) porque necesitamos 6;
// se quedan dentro de la misma familia "neón sobre fondo oscuro" de SYS_CORE.
const AMOUNTS = [
  { value: 1, color: '#2de3ff' }, // cyan
  { value: 5, color: '#2dff8f' }, // verde
  { value: 10, color: '#ffe62d' }, // amarillo
  { value: 25, color: '#ffb020' }, // ámbar
  { value: 50, color: '#ff6b2d' }, // naranja
  { value: 100, color: '#ff2d6f' }, // magenta
];

const wrapStyle = { marginTop: 10 };

const labelStyle = {
  fontSize: 10,
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  color: sysCore.color.inkMuted,
  marginBottom: 6,
};

const gridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(3, 1fr)',
  gap: 6,
};

const btnStyle = (color) => ({
  padding: '8px 0',
  background: `${color}1f`, // ~12% opacidad en hex (1f ≈ 0.12*255)
  color,
  border: `1px solid ${color}`,
  borderRadius: 4,
  cursor: 'pointer',
  fontFamily: sysCore.font.mono,
  fontSize: 11.5,
  fontWeight: 700,
  letterSpacing: '0.03em',
});

const totalBarStyle = {
  marginTop: 8,
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'baseline',
  fontFamily: sysCore.font.mono,
};

const totalLabelStyle = { fontSize: 10.5, color: sysCore.color.inkMuted };

const totalValueStyle = {
  fontSize: 15,
  fontWeight: 700,
  color: sysCore.color.cyan,
};

const resetLinkStyle = {
  background: 'none',
  border: 'none',
  color: sysCore.color.inkMuted,
  textDecoration: 'underline',
  cursor: 'pointer',
  fontFamily: sysCore.font.mono,
  fontSize: 10,
  padding: 0,
};

export default function VehicleQuickAdd() {
  const { scenario, setDemanda } = useScenario();
  const total = scenario.demandaVehicular ?? 0;

  return (
    <div style={wrapStyle}>
      <div style={labelStyle}>// AGREGAR VEHÍCULOS</div>
      <div style={gridStyle}>
        {AMOUNTS.map(({ value, color }) => (
          <button
            key={value}
            type="button"
            style={btnStyle(color)}
            onClick={() => setDemanda(total + value)}
          >
            +{value}
          </button>
        ))}
      </div>

      <div style={totalBarStyle}>
        <span style={totalLabelStyle}>// TOTAL</span>
        <span style={totalValueStyle}>{total.toLocaleString('es-MX')} vehículos</span>
      </div>

      {total > 0 && (
        <button type="button" style={{ ...resetLinkStyle, marginTop: 4 }} onClick={() => setDemanda(0)}>
          reiniciar a 0
        </button>
      )}
    </div>
  );
}