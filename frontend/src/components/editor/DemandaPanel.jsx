// src/components/editor/DemandaPanel.jsx
// El contador de vehículos que pediste: demanda total (veh/h) + duración de
// la simulación. Va arriba de SimularPanel, dentro de MapDataPanel.
// Corresponde a lo que la tarjeta del escenario muestra como
// "// DEMANDA: 100 · 3600s" en el mockup que compartiste.
import { sysCore } from '../../styles/sysCore';
import { useScenario } from '../../scenario/ScenarioContext';
import { StepperInput } from '../common/StepperInput';

const barStyle = { padding: 14, borderBottom: `1px solid ${sysCore.color.border}` };

const labelStyle = {
  fontSize: 10.5,
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  color: sysCore.color.inkMuted,
  marginBottom: 8,
};

const row = { display: 'flex', flexDirection: 'column', gap: 10 };

const durationFieldStyle = {
  width: '100%',
  boxSizing: 'border-box',
  background: 'rgba(10, 12, 16, 0.9)',
  border: `1px solid ${sysCore.color.border}`,
  color: sysCore.color.ink,
  padding: '8px 10px',
  fontFamily: sysCore.font.mono,
  fontSize: 12.5,
};

const subLabel = {
  fontSize: 10,
  color: sysCore.color.inkMuted,
  marginBottom: 4,
  display: 'block',
};

const MIN_VEHICULOS = 0;
const MAX_VEHICULOS = 99999;

export default function DemandaPanel() {
  const { scenario, setDemanda, setDuracion } = useScenario();

  return (
    <div style={barStyle}>
      <div style={labelStyle}>// DEMANDA VEHICULAR</div>
      <div style={row}>
        <StepperInput
          label="Vehículos por hora"
          value={scenario.demandaVehicular ?? 0}
          onChange={(valOrFn) => {
            const current = scenario.demandaVehicular ?? 0;
            const next = typeof valOrFn === 'function' ? valOrFn(current) : valOrFn;
            setDemanda(next);
          }}
          min={MIN_VEHICULOS}
          max={MAX_VEHICULOS}
        />

        <div>
          <span style={subLabel}>Duración de la simulación (segundos)</span>
          <input
            type="number"
            style={durationFieldStyle}
            value={scenario.duracionSegundos ?? 3600}
            min={1}
            onChange={(e) => setDuracion(Number(e.target.value) || 1)}
          />
        </div>
      </div>
    </div>
  );
}