import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../context/AuthContext'; // ⚠️ ajustá el path si difiere (mismo caveat que AccountMenu)
import './ProjectsPanel.css';

/**
 * Panel deslizante de proyectos, estilo SYS_CORE (mismo lenguaje visual
 * que LayersPanel / MapDataPanel).
 *
 * Vista 1 (list):    cards de proyectos, cada una con un círculo en la
 *                     esquina mostrando cuántos escenarios contiene.
 * Vista 2 (detail):  al hacer click en un proyecto, se expande mostrando
 *                     cards de sus escenarios.
 *
 * Rutas asumidas (ajustá si tu backend usa otro nombre):
 *  - GET /api/projects                -> [{ id, name, description, scenariosCount, updatedAt }]
 *  - GET /api/projects/:id/scenarios  -> [{ id, name, status, updatedAt }]
 *
 * Props:
 *  - isOpen: boolean
 *  - onClose: () => void
 */
export default function ProjectsPanel({ isOpen, onClose }) {
  const { token } = useAuth();

  const [view, setView] = useState('list'); // 'list' | 'detail'
  const [projects, setProjects] = useState([]);
  const [activeProject, setActiveProject] = useState(null);
  const [scenarios, setScenarios] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingScenarios, setLoadingScenarios] = useState(false);
  const [error, setError] = useState(null);

  const [creating, setCreating] = useState(false);
  const [newProject, setNewProject] = useState({ name: '', description: '' });

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/projects', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`GET /api/projects -> ${res.status}`);
      const data = await res.json();
      setProjects(Array.isArray(data) ? data : data.projects ?? []);
    } catch (err) {
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
        const res = await fetch(`/api/projects/${projectId}/scenarios`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error(`GET /api/projects/${projectId}/scenarios -> ${res.status}`);
        const data = await res.json();
        setScenarios(Array.isArray(data) ? data : data.scenarios ?? []);
      } catch (err) {
        setError('No se pudieron cargar los escenarios de este proyecto.');
      } finally {
        setLoadingScenarios(false);
      }
    },
    [token]
  );

  useEffect(() => {
    if (!isOpen) return;
    setView('list');
    setActiveProject(null);
    setScenarios([]);
    setError(null);
    setCreating(false);
    fetchProjects();
  }, [isOpen, fetchProjects]);

  function handleOpenProject(project) {
    setActiveProject(project);
    setView('detail');
    fetchScenarios(project.id);
  }

  function handleBack() {
    setView('list');
    setActiveProject(null);
    setScenarios([]);
  }

  function handleCreateProject(e) {
    e.preventDefault();
    const name = newProject.name.trim();
    if (!name) return;

    // TODO: reemplazar por POST /api/projects cuando esté lista la
    // integración con el backend. Por ahora la card se agrega localmente.
    const project = {
      id: `local-${Date.now()}`,
      name,
      description: newProject.description.trim(),
      scenariosCount: 0,
      updatedAt: new Date().toISOString().slice(0, 10),
    };

    setProjects((prev) => [project, ...prev]);
    setNewProject({ name: '', description: '' });
    setCreating(false);
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
            <span className="tst-projects__title">
              {view === 'list' ? 'Tus proyectos' : activeProject?.name}
            </span>
          </div>
        </div>
        <div className="tst-projects__header-right">
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
        <p className="tst-projects__subtitle">Aquí encontrarás tus proyectos.</p>
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
                Todavía no tenés proyectos. Creá uno para empezar.
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
                      // UPDATED: {project.updatedAt}
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
                <div key={scenario.id} className="tst-projects__card tst-projects__card--scenario">
                  <span className="tst-projects__card-name">{scenario.name}</span>
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
                      // UPDATED: {scenario.updatedAt}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </aside>
  );
}