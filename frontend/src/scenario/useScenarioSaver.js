// src/scenario/useScenarioSaver.js
// Lógica única de guardado, usada por el botón manual (SaveScenarioForm)
// y por el autoguardado (MapDataPanel).
//
// Primer guardado de un escenario nuevo:
//   - Si el usuario eligió un proyecto existente (targetProjectId), lo usa.
//   - Si no, CREA un proyecto con nombre automático "Proyecto · <ubicación>"
//     (autoNamed: true, para poder refinarlo hasta que el usuario lo renombre).
//   - El escenario se llama "Escenario N".
// Guardados siguientes: actualiza el mismo escenario.
import { useCallback, useEffect } from 'react';
import { useScenario } from './ScenarioContext';
import { locationName } from './scenarioSchema';
import { listProjects, saveProject, listScenarios } from './scenarioStorage';

const AUTOSAVE_DELAY_MS = 1500;

// Compartido entre instancias: evita dos guardados simultáneos
// (autoguardado + clic manual) que crearían proyectos duplicados.
let inFlight = false;

const autoProjectName = (features) =>
  `Proyecto · ${locationName(features)}`.slice(0, 80);

export function useScenarioSaver() {
  const { scenario, save, targetProjectId, setSaveStatus } = useScenario();

  // Devuelve true si guardó, false si falló, null si ya había otro guardado en curso.
  const saveNow = useCallback(
    async (features) => {
      if (inFlight) return null;
      inFlight = true;
      setSaveStatus('saving');

      try {
        let { projectId, name } = scenario;

        if (!projectId) {
          if (targetProjectId) {
            projectId = targetProjectId;
          } else {
            const created = await saveProject({
              name: autoProjectName(features),
              autoNamed: true,
            });
            projectId = created.id;
          }
          name = `Escenario ${(await listScenarios({ projectId })).length + 1}`;
        }

        await save({ projectId, name, features });

        // Marca el proyecto como reciente; si su nombre sigue siendo automático,
        // lo actualiza con la ubicación actual (deja de hacerlo cuando el usuario lo renombra).
        const project = (await listProjects()).find((p) => p.id === projectId);
        if (project) {
          await saveProject(
            project.autoNamed
              ? { ...project, name: autoProjectName(features) }
              : project
          );
        }

        setSaveStatus('saved');
        return true;
      } catch (err) {
        console.error('Error guardando escenario:', err);
        setSaveStatus('error');
        return false;
      } finally {
        inFlight = false;
      }
    },
    [scenario, save, targetProjectId, setSaveStatus]
  );

  return { saveNow };
}

// Guarda solo, unos instantes después del último cambio.
// Úsalo UNA vez, en un componente que esté siempre montado (MapDataPanel).
export function useAutoSave(features) {
  const { scenario, dirty, autoSave } = useScenario();
  const { saveNow } = useScenarioSaver();

  const sig = JSON.stringify(features);
  const total =
    features.points.length + features.routes.length + features.zones.length;
  const changed = sig !== JSON.stringify(scenario.features);

  useEffect(() => {
    if (!autoSave || !(changed || dirty)) return undefined;
    // Un escenario nuevo solo se crea cuando ya hay algo marcado
    if (!scenario.projectId && total === 0) return undefined;

    const timer = setTimeout(() => saveNow(features), AUTOSAVE_DELAY_MS);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoSave, changed, dirty, sig, scenario.projectId, total, saveNow]);
}
