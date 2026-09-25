// src/components/editor/SaveScenarioForm.jsx
// Barra de guardado del MapDataPanel.
//
// - AUTOGUARDADO (activado por defecto): al marcar algo en el mapa se crea solo el proyecto
//   ("Proyecto · <ubicación>") y el escenario ("Escenario 1"), y luego se actualiza solo.
//   El botón queda como guardado manual inmediato.
// - Antes de marcar puedes elegir un proyecto existente en "GUARDAR_EN".
// - "+ NUEVO ESCENARIO" vacía el mapa y empieza otro escenario dentro del MISMO proyecto.
import { useCallback, useEffect, useState } from 'react';
import { sysCore } from '../../styles/sysCore';
import { useScenario } from '../../scenario/ScenarioContext';
import { useScenarioSaver } from '../../scenario/useScenarioSaver';
import { useMapData } from '../../context/MapDataContext';
import { listProjects } from '../../scenario/scenarioStorage';

const NEW = '__new__';

const barStyle = {
  padding: 14,
  borderBottom: `1px solid ${sysCore.color.border}`,
};

const labelStyle = {
  fontSize: 10.5,
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  color: sysCore.color.inkMuted,
  marginBottom: 6,
};

const ellipsis = { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' };

const selectStyle = {
  width: '100%',
  boxSizing: 'border-box',
  marginBottom: 10,
  padding: '8px 10px',
  background: 'rgba(10, 12, 16, 0.9)',
  color: sysCore.color.ink,
  border: `1px solid ${sysCore.color.border}`,
  borderRadius: 4,
  fontFamily: sysCore.font.mono,
  fontSize: 11.5,
};

const buttonStyle = (disabled, ghost = false) => ({
  width: '100%',
  padding: '10px 0',
  background: disabled
    ? 'rgba(255,255,255,0.05)'
    : ghost
      ? 'transparent'
      : 'rgba(45, 227, 255, 0.12)',
  color: disabled ? sysCore.color.inkMuted : sysCore.color.cyan,
  border: `1px solid ${disabled ? sysCore.color.border : sysCore.color.borderStrong}`,
  borderRadius: 4,
  cursor: disabled ? 'default' : 'pointer',
  fontFamily: sysCore.font.mono,
  fontSize: 11.5,
  fontWeight: 600,
  letterSpacing: '0.05em',
  textTransform: 'uppercase',
});

const statusStyle = (kind) => ({
  marginTop: 8,
  fontSize: 11,
  color: kind === 'error' ? sysCore.color.magenta : sysCore.color.cyan,
  background: kind === 'error' ? 'rgba(255, 45, 111, 0.08)' : 'rgba(45, 227, 255, 0.08)',
  border: `1px solid ${kind === 'error' ? 'rgba(255, 45, 111, 0.3)' : 'rgba(45, 227, 255, 0.3)'}`,
  borderRadius: 4,
  padding: '6px 10px',
  fontFamily: sysCore.font.mono,
});

const autoSaveToggleStyle = (on) => ({
  background: 'none',
  border: `1px solid ${on ? sysCore.color.borderStrong : sysCore.color.border}`,
  color: on ? sysCore.color.cyan : sysCore.color.inkMuted,
  borderRadius: 3,
  padding: '2px 8px',
  cursor: 'pointer',
  fontFamily: sysCore.font.mono,
  fontSize: 10,
  letterSpacing: '0.06em',
});

const timeOf = (iso) =>
  iso ? new Date(iso).toLocaleTimeString('es-MX', { hour12: false }) : '';

export default function SaveScenarioForm({ features }) {
  const {
    scenario, dirty, create,
    autoSave, setAutoSave,
    targetProjectId, setTargetProjectId,
    saveStatus,
  } = useScenario();
  const { saveNow } = useScenarioSaver();
  const { hydrate } = useMapData();

  const [projects, setProjects] = useState([]);

  const refresh = useCallback(async () => {
    setProjects(await listProjects());
  }, []);

  // Refresca la lista al montar y después de cada guardado (cambia updatedAt)
  useEffect(() => {
    refresh();
  }, [refresh, scenario.updatedAt, scenario.projectId]);

  const total =
    (features?.points?.length ?? 0) +
    (features?.routes?.length ?? 0) +
    (features?.zones?.length ?? 0);

  const isSaved = Boolean(scenario.projectId);
  const pending = JSON.stringify(features) !== JSON.stringify(scenario.features) || dirty;
  const saving = saveStatus === 'saving';
  const disabled = saving || (!isSaved && total === 0) || (isSaved && !pending);
  const projectName = projects.find((p) => p.id === scenario.projectId)?.name;

  const startNew = () => {
    if (total > 0 && !window.confirm('Se vaciará lo marcado en el mapa. ¿Continuar?')) return;
    setTargetProjectId(scenario.projectId); // el siguiente escenario queda en el mismo proyecto
    create({ projectId: null });
    hydrate();
  };

  let statusLine = null;
  if (saveStatus === 'error') {
    statusLine = { kind: 'error', text: 'No se pudo guardar el escenario.' };
  } else if (saving) {
    statusLine = { kind: 'ok', text: '// GUARDANDO…' };
  } else if (isSaved && pending && autoSave) {
    statusLine = { kind: 'ok', text: '// CAMBIOS PENDIENTES · se guardan solos' };
  } else if (isSaved) {
    statusLine = { kind: 'ok', text: `// GUARDADO · ${timeOf(scenario.updatedAt)}` };
  } else if (autoSave && total === 0) {
    statusLine = { kind: 'ok', text: '// Marca un punto, ruta o zona y se guardará solo.' };
  }

  return (
    <div style={barStyle}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 10,
        }}
      >
        <span style={{ ...labelStyle, marginBottom: 0 }}>// GUARDADO</span>
        <button
          style={autoSaveToggleStyle(autoSave)}
          onClick={() => setAutoSave(!autoSave)}
          title="Guardar automáticamente al marcar o editar"
        >
          AUTOGUARDADO: {autoSave ? 'ON' : 'OFF'}
        </button>
      </div>

      {isSaved ? (
        <div style={{ marginBottom: 10 }}>
          <div style={{ ...labelStyle, marginBottom: 2, ...ellipsis }} title={projectName}>
            // PROYECTO: {projectName ?? '…'}
          </div>
          <div style={{ ...labelStyle, marginBottom: 0, ...ellipsis }}>
            // ESCENARIO: {scenario.name}
          </div>
        </div>
      ) : (
        <>
          <div style={labelStyle}>// GUARDAR_EN</div>
          <select
            style={selectStyle}
            value={targetProjectId ?? NEW}
            onChange={(e) => setTargetProjectId(e.target.value === NEW ? null : e.target.value)}
            onFocus={refresh}
          >
            <option value={NEW}>+ Proyecto nuevo (nombre automático)</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </>
      )}

      <button style={buttonStyle(disabled)} onClick={() => saveNow(features)} disabled={disabled}>
        {saving
          ? 'GUARDANDO…'
          : isSaved
            ? pending
              ? `GUARDAR AHORA · ${total}`
              : `GUARDADO ✓ · ${total}`
            : `GUARDAR ESCENARIO · ${total}`}
      </button>

      {isSaved && (
        <button style={{ ...buttonStyle(false, true), marginTop: 8 }} onClick={startNew}>
          + NUEVO ESCENARIO
        </button>
      )}

      {statusLine && <div style={statusStyle(statusLine.kind)}>{statusLine.text}</div>}
    </div>
  );
}