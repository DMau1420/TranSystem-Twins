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
import { useAuth } from '../../context/AuthContext';
import { useProyecto } from '../../context/ProyectoContext';
import { actualizarProyecto } from '../../api/proyectosApi';
import { actualizarEscenario } from '../../api/escenariosApi';
import { listProjects } from '../../scenario/scenarioStorage';

const NEW = '__new__';

const inlineInputStyle = {
  background: 'rgba(10, 12, 16, 0.95)',
  border: `1px solid ${sysCore.color.cyan}`,
  color: sysCore.color.ink,
  padding: '4px 6px',
  fontFamily: sysCore.font.mono,
  fontSize: 11,
  borderRadius: 3,
  flex: 1,
  minWidth: 0,
};

const smallBtnStyle = (cyan = true) => ({
  background: cyan ? 'rgba(45, 227, 255, 0.15)' : 'rgba(255, 255, 255, 0.05)',
  border: `1px solid ${cyan ? sysCore.color.cyan : sysCore.color.border}`,
  color: cyan ? sysCore.color.cyan : sysCore.color.inkMuted,
  borderRadius: 3,
  padding: '3px 7px',
  cursor: 'pointer',
  fontFamily: sysCore.font.mono,
  fontSize: 10,
  lineHeight: 1,
});

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
    rename,
    save,
  } = useScenario();
  const { saveNow } = useScenarioSaver();
  const { hydrate } = useMapData();
  const { token } = useAuth();
  const { recargar: recargarProyectos, recargarEscenarios } = useProyecto();

  const [projects, setProjects] = useState([]);
  const [editingProject, setEditingProject] = useState(false);
  const [projNameInput, setProjNameInput] = useState('');
  const [editingScenario, setEditingScenario] = useState(false);
  const [scenNameInput, setScenNameInput] = useState('');

  const refresh = useCallback(async () => {
    setProjects(await listProjects());
  }, []);

  // Refresca la lista al montar o al cambiar de proyecto
  useEffect(() => {
    refresh();
  }, [refresh, scenario.projectId]);

  const total =
    (features?.points?.length ?? 0) +
    (features?.routes?.length ?? 0) +
    (features?.zones?.length ?? 0);

  const currentProjectId = scenario.projectId || scenario.proyecto_id;
  const isSaved = Boolean(currentProjectId);
  const pending = JSON.stringify(features) !== JSON.stringify(scenario.features) || dirty;
  const saving = saveStatus === 'saving';
  const disabled = saving || (!isSaved && total === 0) || (isSaved && !pending);
  const currentProject = projects.find((p) => String(p.id) === String(currentProjectId));
  const projectName = currentProject?.name ?? currentProject?.nombre;

  const startEditProject = () => {
    setProjNameInput(projectName || '');
    setEditingProject(true);
  };

  const handleSaveProjectName = async () => {
    const val = projNameInput.trim();
    if (!val || val === projectName) {
      setEditingProject(false);
      return;
    }
    try {
      if (token && currentProjectId) {
        await actualizarProyecto(token, currentProjectId, { nombre: val });
      }
      setProjects((prev) =>
        prev.map((p) => (String(p.id) === String(currentProjectId) ? { ...p, name: val, nombre: val } : p))
      );
      recargarProyectos?.();
    } catch (e) {
      console.error('Error actualizando nombre de proyecto:', e);
    } finally {
      setEditingProject(false);
    }
  };

  const startEditScenario = () => {
    setScenNameInput(scenario.name || '');
    setEditingScenario(true);
  };

  const handleSaveScenarioName = async () => {
    const val = scenNameInput.trim();
    if (!val || val === scenario.name) {
      setEditingScenario(false);
      return;
    }
    try {
      rename(val);
      await save({ name: val });
      const escId = scenario.backend?.escenarioId || scenario.id;
      if (token && escId && typeof escId === 'number') {
        await actualizarEscenario(token, escId, { nombre: val });
      }
      recargarEscenarios?.();
    } catch (e) {
      console.error('Error actualizando nombre de escenario:', e);
    } finally {
      setEditingScenario(false);
    }
  };

  const startNew = () => {
    if (total > 0 && !window.confirm('Se vaciará lo marcado en el mapa. ¿Continuar?')) return;
    setTargetProjectId(currentProjectId);
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
        <div style={{ marginBottom: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
          {/* Fila Proyecto */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6 }}>
            {editingProject ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, width: '100%' }}>
                <input
                  style={inlineInputStyle}
                  value={projNameInput}
                  onChange={(e) => setProjNameInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSaveProjectName();
                    if (e.key === 'Escape') setEditingProject(false);
                  }}
                  autoFocus
                />
                <button style={smallBtnStyle(true)} onClick={handleSaveProjectName} title="Guardar">✓</button>
                <button style={smallBtnStyle(false)} onClick={() => setEditingProject(false)} title="Cancelar">✕</button>
              </div>
            ) : (
              <>
                <div style={{ ...labelStyle, marginBottom: 0, ...ellipsis, flex: 1 }} title={projectName}>
                  // PROYECTO: <strong style={{ color: sysCore.color.cyan }}>{projectName ?? '…'}</strong>
                </div>
                <button style={smallBtnStyle(true)} onClick={startEditProject} title="Editar nombre del proyecto">
                  ✎
                </button>
              </>
            )}
          </div>

          {/* Fila Escenario */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6 }}>
            {editingScenario ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, width: '100%' }}>
                <input
                  style={inlineInputStyle}
                  value={scenNameInput}
                  onChange={(e) => setScenNameInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSaveScenarioName();
                    if (e.key === 'Escape') setEditingScenario(false);
                  }}
                  autoFocus
                />
                <button style={smallBtnStyle(true)} onClick={handleSaveScenarioName} title="Guardar">✓</button>
                <button style={smallBtnStyle(false)} onClick={() => setEditingScenario(false)} title="Cancelar">✕</button>
              </div>
            ) : (
              <>
                <div style={{ ...labelStyle, marginBottom: 0, ...ellipsis, flex: 1 }}>
                  // ESCENARIO: <strong style={{ color: sysCore.color.ink }}>{scenario.name}</strong>
                </div>
                <button style={smallBtnStyle(false)} onClick={startEditScenario} title="Editar nombre del escenario">
                  ✎
                </button>
              </>
            )}
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