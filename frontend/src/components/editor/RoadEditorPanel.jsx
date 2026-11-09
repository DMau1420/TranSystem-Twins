// src/components/editor/RoadEditorPanel.jsx
// Se abre al hacer clic en una calle o un semáforo de SumoNetworkLayer.
// Edita scenario.edits.edges / scenario.edits.junctions (ya existían en el
// esquema, solo faltaba esta interfaz).
import { useState, useEffect } from 'react';
import { sysCore } from '../../styles/sysCore';
import { useScenario } from '../../scenario/ScenarioContext';
import { effectiveEdge, LIMITS } from '../../scenario/scenarioSchema';

const panelStyle = {
  position: 'absolute',
  bottom: 0,
  left: 0,
  width: 320,
  maxHeight: '60vh',
  overflowY: 'auto',
  background: sysCore.color.panel,
  backdropFilter: 'blur(6px)',
  borderTop: `1px solid ${sysCore.color.borderStrong}`,
  borderRight: `1px solid ${sysCore.color.borderStrong}`,
  zIndex: 1001,
  fontFamily: sysCore.font.mono,
  fontSize: 12.5,
  color: sysCore.color.ink,
};

const headerStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '12px 16px',
  borderBottom: `1px solid ${sysCore.color.border}`,
  fontWeight: 600,
  fontSize: 11,
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  color: sysCore.color.amber ?? '#ffb020',
};

const closeButtonStyle = {
  background: 'none',
  border: 'none',
  color: sysCore.color.inkMuted,
  cursor: 'pointer',
  fontSize: 15,
  lineHeight: 1,
  fontFamily: sysCore.font.mono,
};

const bodyStyle = { padding: 16 };

const fieldLabel = {
  fontSize: 10.5,
  letterSpacing: '0.06em',
  textTransform: 'uppercase',
  color: sysCore.color.inkMuted,
  margin: '10px 0 4px',
};

const inputStyle = {
  width: '100%',
  boxSizing: 'border-box',
  background: 'rgba(10, 12, 16, 0.9)',
  border: `1px solid ${sysCore.color.border}`,
  color: sysCore.color.ink,
  padding: '7px 9px',
  fontFamily: sysCore.font.mono,
  fontSize: 12.5,
};

const rowStyle = { display: 'flex', gap: 8, marginTop: 12 };

const btn = (tone = 'cyan', disabled = false) => ({
  flex: 1,
  padding: '8px 0',
  background: disabled ? 'rgba(255,255,255,0.05)' : `rgba(${tone === 'cyan' ? '45,227,255' : '255,45,111'},0.12)`,
  color: disabled ? sysCore.color.inkMuted : tone === 'cyan' ? sysCore.color.cyan : sysCore.color.magenta,
  border: `1px solid ${disabled ? sysCore.color.border : tone === 'cyan' ? sysCore.color.borderStrong : sysCore.color.magenta}`,
  borderRadius: 4,
  cursor: disabled ? 'default' : 'pointer',
  fontFamily: sysCore.font.mono,
  fontSize: 11,
  fontWeight: 600,
  letterSpacing: '0.04em',
  textTransform: 'uppercase',
});

const meta = { fontSize: 10.5, color: sysCore.color.inkMuted, lineHeight: 1.6 };

const noteStyle = {
  marginTop: 10,
  fontSize: 10,
  lineHeight: 1.5,
  color: '#ffb020',
};

const phaseRow = {
  display: 'flex',
  gap: 6,
  alignItems: 'center',
  marginTop: 6,
};

const phaseInput = { ...inputStyle, width: 70 };

const removePhaseBtn = {
  background: 'none',
  border: 'none',
  color: sysCore.color.magenta,
  cursor: 'pointer',
  fontSize: 13,
  fontFamily: sysCore.font.mono,
};

function EdgeEditor({ selection, scenario, setEdgeProp, resetEdge }) {
  const { id, baseProps } = selection;
  const current = effectiveEdge(baseProps, scenario.edits.edges[id] ?? {});
  const [speed, setSpeed] = useState(current.maxspeed ?? '');
  const [lanes, setLanes] = useState(current.lanes ?? '');

  useEffect(() => {
    setSpeed(current.maxspeed ?? '');
    setLanes(current.lanes ?? '');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const apply = () => {
    if (speed !== '') setEdgeProp(id, 'maxspeed', Number(speed));
    if (lanes !== '') setEdgeProp(id, 'lanes', Number(lanes));
  };

  const revert = () => {
    resetEdge(id);
    setSpeed(current.maxspeed ?? '');
    setLanes(current.lanes ?? '');
  };

  return (
    <div style={bodyStyle}>
      <div style={meta}>
        {baseProps.nombre_calle ?? id}
        {current.edited && <span style={{ color: sysCore.color.amber ?? '#ffb020' }}> · editado</span>}
      </div>

      <div style={fieldLabel}>Velocidad máxima (km/h)</div>
      <input
        type="number"
        style={inputStyle}
        value={speed}
        min={LIMITS.maxspeedKmh[0]}
        max={LIMITS.maxspeedKmh[1]}
        onChange={(e) => setSpeed(e.target.value)}
      />

      <div style={fieldLabel}>Carriles</div>
      <input
        type="number"
        style={inputStyle}
        value={lanes}
        min={LIMITS.lanes[0]}
        max={LIMITS.lanes[1]}
        onChange={(e) => setLanes(e.target.value)}
      />

      <div style={rowStyle}>
        <button style={btn('cyan')} onClick={apply}>Aplicar</button>
        <button style={btn('magenta', !current.edited)} onClick={revert} disabled={!current.edited}>
          Revertir
        </button>
      </div>
    </div>
  );
}

function JunctionEditor({ selection, scenario, setTls, resetJunction }) {
  const { id, baseProps } = selection;
  const saved = scenario.edits.junctions[id]?.tls?.phases;
  const [phases, setPhases] = useState(saved ?? []);
  const edited = Boolean(scenario.edits.junctions[id]);

  useEffect(() => {
    setPhases(scenario.edits.junctions[id]?.tls?.phases ?? []);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const updatePhase = (i, field, value) => {
    setPhases((prev) => prev.map((p, idx) => (idx === i ? { ...p, [field]: value } : p)));
  };

  const addPhase = () => setPhases((prev) => [...prev, { duration: 30, state: '' }]);
  const removePhase = (i) => setPhases((prev) => prev.filter((_, idx) => idx !== i));

  const apply = () => {
    const limpias = phases
      .filter((p) => p.state.trim() !== '')
      .map((p) => ({ duration: Number(p.duration) || 1, state: p.state.trim() }));
    setTls(id, limpias);
  };

  const revert = () => {
    resetJunction(id);
    setPhases([]);
  };

  return (
    <div style={bodyStyle}>
      <div style={meta}>
        Tipo: {baseProps.tipo_control ?? '—'} · Entrantes: {baseProps.calles_entrantes?.length ?? 0} ·
        Salientes: {baseProps.calles_salientes?.length ?? 0}
        {edited && <span style={{ color: sysCore.color.amber ?? '#ffb020' }}> · editado</span>}
      </div>

      <div style={noteStyle}>
        No se pudieron precargar las fases actuales de este semáforo (el dato
        real de /api/red no las trae todavía). Define las fases nuevas que
        quieras aplicar; se guardan como la modificación completa de este
        semáforo.
      </div>

      <div style={fieldLabel}>Fases (duración en segundos · estado SUMO, ej. "GrGr")</div>
      {phases.map((p, i) => (
        <div key={i} style={phaseRow}>
          <span style={{ ...meta, width: 16 }}>{i + 1}</span>
          <input
            type="number"
            style={phaseInput}
            value={p.duration}
            min={LIMITS.phaseSeconds[0]}
            max={LIMITS.phaseSeconds[1]}
            onChange={(e) => updatePhase(i, 'duration', e.target.value)}
          />
          <input
            type="text"
            style={{ ...inputStyle, flex: 1 }}
            placeholder="GrGr"
            value={p.state}
            onChange={(e) => updatePhase(i, 'state', e.target.value)}
          />
          <button style={removePhaseBtn} onClick={() => removePhase(i)} title="Quitar fase">✕</button>
        </div>
      ))}

      <div style={rowStyle}>
        <button style={btn('cyan')} onClick={addPhase}>+ Fase</button>
      </div>
      <div style={rowStyle}>
        <button style={btn('cyan')} onClick={apply}>Aplicar</button>
        <button style={btn('magenta', !edited)} onClick={revert} disabled={!edited}>
          Revertir
        </button>
      </div>
    </div>
  );
}

export default function RoadEditorPanel() {
  const {
    selection, clearSelection, scenario,
    setEdgeProp, resetEdge, setTls, resetJunction,
  } = useScenario();

  if (!selection) return null;

  const isEdge = selection.kind === 'edge';

  return (
    <div style={panelStyle}>
      <div style={headerStyle}>
        // EDITOR // {isEdge ? 'CALLE' : 'SEMAFORO'}
        <button style={closeButtonStyle} onClick={clearSelection} aria-label="Cerrar">✕</button>
      </div>

      {isEdge ? (
        <EdgeEditor selection={selection} scenario={scenario} setEdgeProp={setEdgeProp} resetEdge={resetEdge} />
      ) : (
        <JunctionEditor selection={selection} scenario={scenario} setTls={setTls} resetJunction={resetJunction} />
      )}
    </div>
  );
}