// src/components/editor/SimularPanel.jsx
// Va debajo de DemandaPanel/SaveScenarioForm en MapDataPanel. Solo tiene
// sentido una vez que el escenario ya se guardó al menos una vez.
import { useEffect, useState } from 'react';
import { sysCore } from '../../styles/sysCore';
import { useAuth } from '../../context/AuthContext'; // ⚠️ mismo caveat de path que en AccountMenu/ProjectsPanel
import { useScenario } from '../../scenario/ScenarioContext';
import { useSimulacion } from '../../scenario/useSimulacion';
import SimulationResultsModal from './SimulationResultsModal';
import VehicleQuickAdd from './VehicleQuickAdd';
import { generarResultadoCoherente } from '../../scenario/mockResultado';

const barStyle = { padding: 14, borderBottom: `1px solid ${sysCore.color.border}` };

const labelStyle = {
  fontSize: 10.5,
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  color: sysCore.color.inkMuted,
  marginBottom: 8,
};

const buttonStyle = (disabled, tone = 'cyan') => ({
  width: '100%',
  padding: '10px 0',
  background: disabled ? 'rgba(255,255,255,0.05)' : `rgba(${tone === 'cyan' ? '45, 227, 255' : '255, 45, 111'}, 0.12)`,
  color: disabled ? sysCore.color.inkMuted : tone === 'cyan' ? sysCore.color.cyan : sysCore.color.magenta,
  border: `1px solid ${disabled ? sysCore.color.border : tone === 'cyan' ? sysCore.color.borderStrong : sysCore.color.magenta}`,
  borderRadius: 4,
  cursor: disabled ? 'default' : 'pointer',
  fontFamily: sysCore.font.mono,
  fontSize: 11.5,
  fontWeight: 600,
  letterSpacing: '0.05em',
  textTransform: 'uppercase',
});

const ghostButtonStyle = {
  width: '100%',
  marginTop: 8,
  padding: '8px 0',
  background: 'transparent',
  color: sysCore.color.inkMuted,
  border: `1px dashed ${sysCore.color.border}`,
  borderRadius: 4,
  cursor: 'pointer',
  fontFamily: sysCore.font.mono,
  fontSize: 10.5,
  letterSpacing: '0.05em',
  textTransform: 'uppercase',
};

const progressTrackStyle = {
  height: 4,
  background: 'rgba(255,255,255,0.08)',
  borderRadius: 2,
  marginTop: 10,
  overflow: 'hidden',
};

const progressFillStyle = (pct) => ({
  height: '100%',
  width: `${pct}%`,
  background: sysCore.color.cyan,
  transition: 'width 0.3s ease',
});

const statusStyle = (kind) => ({
  marginTop: 10,
  fontSize: 11,
  color: kind === 'error' ? sysCore.color.magenta : sysCore.color.cyan,
  background: kind === 'error' ? 'rgba(255, 45, 111, 0.08)' : 'rgba(45, 227, 255, 0.08)',
  border: `1px solid ${kind === 'error' ? 'rgba(255, 45, 111, 0.3)' : 'rgba(45, 227, 255, 0.3)'}`,
  borderRadius: 4,
  padding: '8px 10px',
  fontFamily: sysCore.font.mono,
});

const linkStyle = {
  display: 'block',
  marginTop: 10,
  background: 'none',
  border: 'none',
  color: sysCore.color.inkMuted,
  textDecoration: 'underline',
  cursor: 'pointer',
  fontFamily: sysCore.font.mono,
  fontSize: 10.5,
  padding: 0,
};

const ESTADO_LABEL = {
  sincronizando: 'SINCRONIZANDO CON EL BACKEND…',
  conectando: 'CONECTANDO AL SERVIDOR DE SIMULACIÓN…',
  simulando: 'SIMULANDO…',
};

export default function SimularPanel({ features }) {
  const { token } = useAuth();
  const { scenario, save, setResultado } = useScenario(); // save(patch) del contexto
  const { estado, progreso, resultado, error, simular, cancelar } = useSimulacion({
    token,
    scenario,
    features,
    nombreProyectoLocal: scenario.name,
    save,
  });

  const [showModal, setShowModal] = useState(false);
  const [modalData, setModalData] = useState(null); // resultado real o el mock, lo que se esté mostrando

  // Al completarse de verdad, guarda el resultado en el escenario (para "ver
  // último resultado" después) y abre el modal automáticamente.
  useEffect(() => {
    if (estado === 'completado' && resultado) {
      setResultado(resultado);
      save({ ultimoResultado: resultado });
      setModalData(resultado);
      setShowModal(true);
    }
  }, [estado, resultado, setResultado, save]);

  const isSaved = Boolean(scenario.projectId);
  const running = estado === 'sincronizando' || estado === 'conectando' || estado === 'simulando';

  if (!isSaved) return null; // nada que simular hasta que exista un escenario guardado

  return (
    <div style={barStyle}>
      <div style={labelStyle}>// SIMULACIÓN</div>

      <button style={buttonStyle(running)} onClick={simular} disabled={running}>
        {running ? 'SIMULANDO…' : '▶ SIMULAR ESCENARIO'}
      </button>

      <VehicleQuickAdd />

      {running && (
        <>
          <div style={progressTrackStyle}>
            <div style={progressFillStyle(progreso)} />
          </div>
          <div style={statusStyle('ok')}>
            {ESTADO_LABEL[estado] ?? '// PROCESANDO…'} {progreso > 0 ? `${progreso}%` : ''}
          </div>
          <button style={{ ...buttonStyle(false, 'magenta'), marginTop: 8 }} onClick={cancelar}>
            CANCELAR
          </button>
        </>
      )}

      {estado === 'error' && <div style={statusStyle('error')}>{error}</div>}

      {!running && scenario.ultimoResultado && (
        <button style={linkStyle} onClick={() => { setModalData(scenario.ultimoResultado); setShowModal(true); }}>
          ver último resultado
        </button>
      )}

      {/* TEMPORAL: quítalo cuando haya simulaciones reales que probar */}
      <button
        style={ghostButtonStyle}
        onClick={() => { setModalData(generarResultadoCoherente(scenario)); setShowModal(true); }}
      >
        Ver mockup de resultados
      </button>

      {showModal && modalData && (
        <SimulationResultsModal
          scenarioName={scenario.name}
          resultado={modalData}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  );
}