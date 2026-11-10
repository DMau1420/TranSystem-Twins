// src/scenario/backendSync.js
// Antes de simular, el escenario debe existir como fila real en la base de
// datos del backend (la tabla resultados depende de un escenario_id). Esto
// crea el proyecto y el escenario en el backend la primera vez, y reutiliza
// esos ids las veces siguientes — independiente de los ids locales
// (localStorage) que ya usa ProjectsPanel.
import { crearProyecto } from '../api/proyectosApi';
import { crearEscenario, actualizarEscenario } from '../api/escenariosApi';
import { scenarioToProyectoPayload, scenarioToEscenarioPayload } from './escenarioMapper';

/**
 * Garantiza que el escenario local tenga un proyecto y escenario equivalente
 * en el backend real.
 *
 * Devuelve { proyectoId, escenarioId } del backend, creando lo que falte.
 * save(patch) es el `save` de useScenario(), para persistir backend.{...} en
 * el escenario local una vez que el backend confirma los ids.
 */
export async function ensureEnBackend({ token, scenario, features, nombreProyectoLocal, save }) {
  let { proyectoId, escenarioId } = scenario.backend ?? {};

  if (!proyectoId) {
    const proyecto = await crearProyecto(
      token,
      scenarioToProyectoPayload(scenario, features, nombreProyectoLocal)
    );
    proyectoId = proyecto.id;
  }

  const payload = scenarioToEscenarioPayload(scenario, features, proyectoId);

  if (!escenarioId) {
    const creado = await crearEscenario(token, payload);
    escenarioId = creado.id;
  } else {
    // Ya existía: sube los cambios más recientes (ediciones de calles/semáforos,
    // demanda, zona) antes de simular.
    await actualizarEscenario(token, escenarioId, payload);
  }

  const backend = { proyectoId, escenarioId };
  await save({ backend }); // persiste los ids en el escenario local

  return backend;
}