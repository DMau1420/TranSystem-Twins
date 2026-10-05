import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../context/AuthContext'; // ⚠️ ajustá el path si difiere (mismo caveat que AccountMenu)
import { useMapData } from '../../context/MapDataContext';
import { useScenario } from '../../scenario/ScenarioContext';
import {
  listProjects,
  saveProject,
  deleteProject,
  listScenarios,
  renameScenario,
  deleteScenario,
  duplicateScenario,
} from '../../scenario/scenarioStorage';
import { sysCore } from '../../styles/sysCore';
import './ProjectsPanel.css';

// false = todo se lee/guarda del almacenamiento local del navegador (sin llamadas al backend).
// Ponlo en true cuando el backend esté listo: intenta la API y cae al modo local si falla.
const USE_API = false;

// Mismo patrón de confirmación que AccountMenu (DELETE_CONFIRM_WORD) para
// borrados de un solo elemento, sin cascada. El proyecto, al borrar en
// cascada sus escenarios, pide en cambio el nombre exacto del proyecto
// (mismo patrón que GitHub/Vercel para borrados irreversibles de mayor peso).
const DELETE_WORD = 'ELIMINAR';

const shortDate = (v) => (v ? String(v).slice(0, 10) : '');

async function loadLocalProjects() {
  const local = await listProjects();
  return Promise.all(
    local.map(async (p) => ({
      ...p,
      scenariosCount: (await listScenarios({ projectId: p.id })).length,
    }))
  );
}

// ── Estilos in-line (mismos tokens SYS_CORE que MapDataPanel/SaveScenarioForm) ──
const iconBtnStyle = (danger = false) => ({
  background: 'none',
  border: 'none',
  color: danger ? sysCore.color.magenta : sysCore.color.inkMuted,
  cursor: 'pointer',
  fontSize: 13,
  lineHeight: 1,
  padding: 4,
  fontFamily: sysCore.font.mono,
  opacity: 0.85,
});

const overlayStyle = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(5, 6, 9, 0.7)',
  backdropFilter: 'blur(2px)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 2000,
};

const modalStyle = {
  width: 340,
  background: sysCore.color.panel,
  border: `1px solid ${sysCore.color.borderStrong}`,
  borderRadius: 6,
  padding: 18,
  fontFamily: sysCore.font.mono,
  color: sysCore.color.ink,
  boxShadow: '0 0 30px rgba(255, 45, 111, 0.12)',
};

const dangerTagStyle = {
  display: 'block',
  fontSize: 10.5,
  letterSpacing: '0.08em',
  color: sysCore.color.magenta,
  marginBottom: 10,
};

const warnTextStyle = { fontSize: 12, lineHeight: 1.5, color: sysCore.color.ink, marginBottom: 14 };

const modalLabelStyle = {
  display: 'block',
  fontSize: 10.5,
  color: sysCore.color.inkMuted,
  marginBottom: 6,
};

const dangerInputStyle = {
  width: '100%',
  boxSizing: 'border-box',
  background: 'rgba(10, 12, 16, 0.9)',
  border: `1px solid ${sysCore.color.border}`,
  color: sysCore.color.ink,
  padding: '8px 10px',
  fontFamily: sysCore.font.mono,
  fontSize: 12.5,
};

const modalButtonStyle = (disabled, danger) => ({
  flex: 1,
  padding: '9px 0',
  background: disabled ? 'rgba(255,255,255,0.05)' : danger ? 'rgba(255, 45, 111, 0.12)' : 'transparent',
  color: disabled ? sysCore.color.inkMuted : danger ? sysCore.color.magenta : sysCore.color.ink,
  border: `1px solid ${disabled ? sysCore.color.border : danger ? sysCore.color.magenta : sysCore.color.border}`,
  borderRadius: 4,
  cursor: disabled ? 'default' : 'pointer',
  fontFamily: sysCore.font.mono,
  fontSize: 11,
  fontWeight: 600,
  letterSpacing: '0.05em',
  textTransform: 'uppercase',
});

/**
 * Panel deslizante de proyectos, estilo SYS_CORE (mismo lenguaje visual
 * que LayersPanel / MapDataPanel).
 *
 * Vista 1 (list):    cards de proyectos, cada una con un círculo en la
 *                     esquina mostrando cuántos escenarios contiene.
 * Vista 2 (detail):  al hacer click en un proyecto, se expande mostrando
 *                     cards de sus escenarios. Click en un escenario => lo abre
 *                     en el mapa. El nombre del proyecto se puede editar (✎) o
 *                     borrar (🗑, borra también sus escenarios). Cada escenario
 *                     tiene sus propios ✎ / 🗑.
 *
 * Rutas asumidas cuando USE_API = true (ajustá si tu backend usa otro nombre):
 *  - GET /api/projects                -> [{ id, name, description, scenariosCount, updatedAt }]
 *  - GET /api/projects/:id/scenarios  -> [{ id, name, status, updatedAt }]
 *
 * Props:
 *  - isOpen: boolean
 *  - onClose: () => void
 */
export default function ProjectsPanel({ isOpen, onClose }) {
  const { token } = useAuth();
  const { hydrate } = useMapData();
  const { load } = useScenario();

  const [view, setView] = useState('list'); // 'list' | 'detail'
  const [projects, setProjects] = useState([]);
  const [activeProject, setActiveProject] = useState(null);
  const [scenarios, setScenarios] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingScenarios, setLoadingScenarios] = useState(false);
  const [error, setError] = useState(null);
  const [localMode, setLocalMode] = useState(true);

  const [creating, setCreating] = useState(false);
  const [newProject, setNewProject] = useState({ name: '', description: '' });

  const [renaming, setRenaming] = useState(false); // renombrando el proyecto activo
  const [renameValue, setRenameValue] = useState('');
  const [renamingScenarioId, setRenamingScenarioId] = useState(null);
  const [scenarioRenameValue, setScenarioRenameValue] = useState('');

  // { kind: 'project' | 'scenario', id, name, count? }
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [confirmInput, setConfirmInput] = useState('');
  const [deleting, setDeleting] = useState(false);

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (USE_API) {
        try {
          const res = await fetch('/api/projects', {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (!res.ok) throw new Error(`GET /api/projects -> ${res.status}`);
          const data = await res.json();
          setProjects(Array.isArray(data) ? data : data.projects ?? []);
          setLocalMode(false);
          return;
        } catch {
          /* backend no disponible: cae al modo local */
        }
      }
      setProjects(await loadLocalProjects());
      setLocalMode(true);
    } catch {
      setError('No se pudieron cargar los proyectos.');
    } finally {
      setLoading(false);
    }
  }, [token]);

  const fetchScenarios = useCallback(
    async (projectId) => {
      setLoadingScenarios(true);
      setError(null);
      try {
        if (USE_API) {
          try {
            const res = await fetch(`/api/projects/${projectId}/scenarios`, {
              headers: { Authorization: `Bearer ${token}` },
            });
            if (!res.ok) throw new Error(`GET /api/projects/${projectId}/scenarios -> ${res.status}`);
            const data = await res.json();
            setScenarios(Array.isArray(data) ? data : data.scenarios ?? []);
            return;
          } catch {
            /* backend no disponible: cae al modo local */
          }
        }
        setScenarios(await listScenarios({ projectId }));
      } catch {
        setError('No se pudieron cargar los escenarios de este proyecto.');
      } finally {
        setLoadingScenarios(false);
      }
    },
    [token]
  );

  // Escape cierra el modal de eliminar (si no se está borrando ya)
  useEffect(() => {
    if (!confirmDelete) return undefined;
    const onKey = (e) => {
      if (e.key === 'Escape' && !deleting) setConfirmDelete(null);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [confirmDelete, deleting]);

  useEffect(() => {
    if (!isOpen) return;
    setView('list');
    setActiveProject(null);
    setScenarios([]);
    setError(null);
    setCreating(false);
    setRenaming(false);
    setRenamingScenarioId(null);
    setConfirmDelete(null);
    fetchProjects();
  }, [isOpen, fetchProjects]);

  function handleOpenProject(project) {
    setActiveProject(project);
    setView('detail');
    setRenaming(false);
    setRenamingScenarioId(null);
    fetchScenarios(project.id);
  }

  function handleBack() {
    setView('list');
    setActiveProject(null);
    setScenarios([]);
    setRenaming(false);
    setRenamingScenarioId(null);
    fetchProjects(); // refresca contadores
  }

  async function handleCreateProject(e) {
    e.preventDefault();
    const name = newProject.name.trim();
    if (!name) return;

    try {
      // TODO: reemplazar por POST /api/projects cuando esté lista la integración con el backend.
      await saveProject({ name, description: newProject.description.trim() });
      setNewProject({ name: '', description: '' });
      setCreating(false);
      await fetchProjects();
    } catch {
      setError('No se pudo crear el proyecto.');
    }
  }

  // ── Renombrar proyecto ──────────────────────────────────────────────────
  function startRename() {
    setRenameValue(activeProject?.name ?? '');
    setRenaming(true);
  }

  async function commitRename() {
    const name = renameValue.trim();
    setRenaming(false);
    if (!name || name === activeProject.name) return;

    try {
      // TODO: PATCH /api/projects/:id cuando esté lista la integración con el backend.
      const { scenariosCount, ...base } = activeProject;
      await saveProject({ ...base, name, autoNamed: false }); // ya no se autoactualiza el nombre
      setActiveProject((p) => ({ ...p, name }));
      setProjects((prev) => prev.map((p) => (p.id === activeProject.id ? { ...p, name } : p)));
    } catch {
      setError('No se pudo renombrar el proyecto.');
    }
  }

  // ── Renombrar escenario ─────────────────────────────────────────────────
  function startRenameScenario(scenario) {
    setScenarioRenameValue(scenario.name);
    setRenamingScenarioId(scenario.id);
  }

  async function commitRenameScenario(scenario) {
    const name = scenarioRenameValue.trim();
    setRenamingScenarioId(null);
    if (!name || name === scenario.name) return;

    try {
      // TODO: PATCH /api/projects/:id/scenarios/:id cuando esté lista la integración con el backend.
      await renameScenario(scenario.id, name);
      setScenarios((prev) => prev.map((s) => (s.id === scenario.id ? { ...s, name } : s)));
    } catch {
      setError('No se pudo renombrar el escenario.');
    }
  }

  // ── Eliminar (proyecto en cascada / escenario) ──────────────────────────
  function askDeleteProject() {
    if (!activeProject) return;
    setConfirmInput('');
    setConfirmDelete({ kind: 'project', id: activeProject.id, name: activeProject.name, count: scenarios.length });
  }

  function askDeleteScenario(scenario) {
    setConfirmInput('');
    setConfirmDelete({ kind: 'scenario', id: scenario.id, name: scenario.name });
  }

  async function handleDuplicateScenario(scenario) {
    setError(null);
    try {
      // TODO: POST /api/scenarios/:id/duplicate cuando esté lista la integración con el backend.
      await duplicateScenario(scenario.id);
      setScenarios(await listScenarios({ projectId: activeProject.id }));
    } catch {
      setError('No se pudo duplicar el escenario.');
    }
  }

  const matchOk =
    confirmDelete?.kind === 'project'
      ? confirmInput === confirmDelete.name
      : confirmInput === DELETE_WORD;

  async function confirmDeleteNow() {
    if (!confirmDelete || !matchOk) return;
    setDeleting(true);
    setError(null);
    try {
      // TODO: DELETE /api/projects/:id o /api/scenarios/:id cuando esté lista la integración con el backend.
      if (confirmDelete.kind === 'project') {
        await deleteProject(confirmDelete.id);
        setConfirmDelete(null);
        handleBack();
      } else {
        await deleteScenario(confirmDelete.id);
        setScenarios((prev) => prev.filter((s) => s.id !== confirmDelete.id));
        setConfirmDelete(null);
      }
    } catch {
      setError(`No se pudo eliminar ${confirmDelete.kind === 'project' ? 'el proyecto' : 'el escenario'}.`);
    } finally {
      setDeleting(false);
    }
  }

  async function handleOpenScenario(scenario) {
    setError(null);
    try {
      const found = await load(scenario.id);
      if (!found) {
        setError('No se pudo abrir el escenario.');
        return;
      }
      hydrate(found.features ?? {}); // repuebla puntos, rutas y zonas, y vuela hacia ellos
      onClose();
    } catch {
      setError('No se pudo abrir el escenario.');
    }
  }

  if (!isOpen) return null;

  return (
    <aside className="tst-projects__panel">
      <div className="tst-projects__reticle tst-projects__reticle--tl" />
      <div className="tst-projects__reticle tst-projects__reticle--br" />
      <div className="tst-projects__scanline" />

      <header className="tst-projects__header">
        <div className="tst-projects__header-left">
          {view === 'detail' && (
            <button
              type="button"
              className="tst-projects__back"
              onClick={handleBack}
              aria-label="Volver a proyectos"
            >
              ‹
            </button>
          )}
          <div className="tst-projects__header-text">
            <span className="tst-projects__tag">
              {view === 'list' ? '// PROJECTS // USER_SPACE' : '// SCENARIOS // PROJECT_NODE'}
            </span>
            <span
              className="tst-projects__title"
              title={view === 'detail' ? activeProject?.name : undefined}
            >
              {view === 'list' ? (
                'Tus proyectos'
              ) : renaming ? (
                <input
                  className="tst-projects__input"
                  style={{ padding: '4px 8px' }}
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  onBlur={commitRename}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') e.currentTarget.blur();
                    if (e.key === 'Escape') setRenaming(false);
                  }}
                  maxLength={80}
                  autoFocus
                />
              ) : (
                activeProject?.name
              )}
            </span>
          </div>
        </div>
        <div className="tst-projects__header-right">
          {view === 'detail' && !renaming && (
            <>
              <button
                type="button"
                className="tst-projects__add"
                onClick={startRename}
                aria-label="Renombrar proyecto"
                title="Renombrar proyecto"
              >
                ✎
              </button>
              <button
                type="button"
                className="tst-projects__add"
                onClick={askDeleteProject}
                aria-label="Eliminar proyecto"
                title="Eliminar proyecto"
                style={{ color: sysCore.color.magenta }}
              >
                🗑
              </button>
            </>
          )}
          {view === 'list' && (
            <button
              type="button"
              className="tst-projects__add"
              onClick={() => setCreating((c) => !c)}
              aria-label="Nuevo proyecto"
              title="Nuevo proyecto"
            >
              +
            </button>
          )}
          <button type="button" className="tst-projects__close" onClick={onClose} aria-label="Cerrar y volver al menú">
            ×
          </button>
        </div>
      </header>

      {view === 'list' && (
        <p className="tst-projects__subtitle">
          Aquí encontrarás tus proyectos.
          {localMode && ' // MODO_LOCAL: se guardan en este navegador.'}
        </p>
      )}

      {error && <div className="tst-projects__error">{error}</div>}

      {view === 'list' && creating && (
        <form className="tst-projects__new-form" onSubmit={handleCreateProject}>
          <label className="tst-projects__label">// NOMBRE</label>
          <input
            className="tst-projects__input"
            value={newProject.name}
            onChange={(e) => setNewProject((p) => ({ ...p, name: e.target.value }))}
            placeholder="Ej. Corredor Insurgentes"
            autoFocus
          />

          <label className="tst-projects__label">// DESCRIPCIÓN_CORTA</label>
          <textarea
            className="tst-projects__input tst-projects__input--textarea"
            value={newProject.description}
            onChange={(e) => setNewProject((p) => ({ ...p, description: e.target.value }))}
            placeholder="Una línea sobre de qué trata este proyecto"
            maxLength={140}
            rows={2}
          />

          <div className="tst-projects__form-actions">
            <button type="submit" className="tst-projects__btn tst-projects__btn--cyan" disabled={!newProject.name.trim()}>
              CREAR
            </button>
            <button
              type="button"
              className="tst-projects__btn tst-projects__btn--ghost"
              onClick={() => {
                setCreating(false);
                setNewProject({ name: '', description: '' });
              }}
            >
              CANCELAR
            </button>
          </div>
        </form>
      )}

      <div className="tst-projects__body">
        {view === 'list' && (
          <>
            {loading && <div className="tst-projects__status">// CARGANDO_PROYECTOS...</div>}

            {!loading && projects.length === 0 && !error && (
              <div className="tst-projects__status">
                Todavía no tenés proyectos. Guardá un escenario desde el mapa o creá uno con +.
              </div>
            )}

            <div className="tst-projects__grid">
              {projects.map((project) => (
                <button
                  type="button"
                  key={project.id}
                  className="tst-projects__card"
                  onClick={() => handleOpenProject(project)}
                >
                  <span className="tst-projects__card-badge">
                    {project.scenariosCount ?? 0}
                  </span>
                  <span className="tst-projects__card-name">{project.name}</span>
                  {project.description && (
                    <span className="tst-projects__card-desc">{project.description}</span>
                  )}
                  {project.updatedAt && (
                    <span className="tst-projects__card-meta">
                      // UPDATED: {shortDate(project.updatedAt)}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </>
        )}

        {view === 'detail' && (
          <>
            {loadingScenarios && (
              <div className="tst-projects__status">// CARGANDO_ESCENARIOS...</div>
            )}

            {!loadingScenarios && scenarios.length === 0 && !error && (
              <div className="tst-projects__status">
                Este proyecto todavía no tiene escenarios.
              </div>
            )}

            <div className="tst-projects__grid">
              {scenarios.map((scenario) => (
                <div
                  key={scenario.id}
                  className="tst-projects__card tst-projects__card--scenario"
                  style={{ position: 'relative' }}
                >
                  <div style={{ position: 'absolute', top: 6, right: 6, display: 'flex', gap: 2 }}>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDuplicateScenario(scenario);
                      }}
                      title="Duplicar escenario"
                      aria-label="Duplicar escenario"
                      style={iconBtnStyle()}
                    >
                      ⧉
                    </button>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        startRenameScenario(scenario);
                      }}
                      title="Renombrar escenario"
                      aria-label="Renombrar escenario"
                      style={iconBtnStyle()}
                    >
                      ✎
                    </button>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        askDeleteScenario(scenario);
                      }}
                      title="Eliminar escenario"
                      aria-label="Eliminar escenario"
                      style={iconBtnStyle(true)}
                    >
                      🗑
                    </button>
                  </div>

                  <div
                    role="button"
                    tabIndex={0}
                    onClick={() => handleOpenScenario(scenario)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleOpenScenario(scenario);
                    }}
                    style={{ cursor: 'pointer', paddingRight: 64 }}
                    title="Abrir en el mapa"
                  >
                    {renamingScenarioId === scenario.id ? (
                      <input
                        className="tst-projects__input"
                        style={{ padding: '4px 8px' }}
                        value={scenarioRenameValue}
                        onChange={(e) => setScenarioRenameValue(e.target.value)}
                        onClick={(e) => e.stopPropagation()}
                        onBlur={() => commitRenameScenario(scenario)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') e.currentTarget.blur();
                          if (e.key === 'Escape') setRenamingScenarioId(null);
                        }}
                        maxLength={80}
                        autoFocus
                      />
                    ) : (
                      <span className="tst-projects__card-name">{scenario.name}</span>
                    )}
                    {scenario.status && (
                      <span
                        className={`tst-projects__status-pill tst-projects__status-pill--${(
                          scenario.status || ''
                        ).toLowerCase()}`}
                      >
                        {scenario.status}
                      </span>
                    )}
                    {scenario.updatedAt && (
                      <span className="tst-projects__card-meta">
                        // UPDATED: {shortDate(scenario.updatedAt)}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {confirmDelete && (
        <div style={overlayStyle} onClick={() => !deleting && setConfirmDelete(null)}>
          <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
            <span style={dangerTagStyle}>// WARNING // DATA_LOSS</span>

            {confirmDelete.kind === 'project' ? (
              <>
                <p style={warnTextStyle}>
                  Esto eliminará el proyecto <strong>{confirmDelete.name}</strong>
                  {confirmDelete.count > 0 && (
                    <>
                      {' '}
                      y sus <strong>{confirmDelete.count}</strong> escenario(s)
                    </>
                  )}
                  . No se puede deshacer.
                </p>
                <label style={modalLabelStyle}>Escribe el nombre del proyecto para confirmar</label>
              </>
            ) : (
              <>
                <p style={warnTextStyle}>
                  Esto eliminará el escenario <strong>{confirmDelete.name}</strong>. No se puede deshacer.
                </p>
                <label style={modalLabelStyle}>
                  Escribe <strong>{DELETE_WORD}</strong> para confirmar
                </label>
              </>
            )}

            <input
              style={dangerInputStyle}
              value={confirmInput}
              onChange={(e) => setConfirmInput(e.target.value)}
              disabled={deleting}
              autoComplete="off"
              autoFocus
            />

            <div style={{ display: 'flex', gap: 8, marginTop: 14 }}>
              <button
                style={modalButtonStyle(!matchOk || deleting, true)}
                disabled={!matchOk || deleting}
                onClick={confirmDeleteNow}
              >
                {deleting
                  ? 'ELIMINANDO…'
                  : confirmDelete.kind === 'project'
                    ? 'ELIMINAR PROYECTO'
                    : 'ELIMINAR ESCENARIO'}
              </button>
              <button
                type="button"
                style={modalButtonStyle(false, false)}
                onClick={() => setConfirmDelete(null)}
                disabled={deleting}
              >
                CANCELAR
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}