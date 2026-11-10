// src/ResumeActiveScenario.jsx
// Sin esto, cada recarga de página empezaba con un escenario en blanco
// (projectId: null). Si ya había puntos marcados, el autoguardado creaba un
// proyecto NUEVO en vez de seguir usando el existente — de ahí los varios
// "Proyecto · <misma zona>" repetidos con un solo "Escenario 1" cada uno.
//
// Va DENTRO de ScenarioProvider y de MapDataProvider a la vez (los necesita
// a los dos), como hijo directo en App.jsx. No renderiza nada.
import { useEffect, useRef } from 'react';
import { useScenario } from './scenario/ScenarioContext';
import { useMapData } from './context/MapDataContext';
import { getActiveScenarioId } from './scenario/scenarioStorage';

export default function ResumeActiveScenario() {
  const { scenario, load } = useScenario();
  const { hydrate } = useMapData();
  const triedRef = useRef(false);

  useEffect(() => {
    if (triedRef.current) return;
    triedRef.current = true;

    if (scenario.projectId) return; // ya hay algo cargado, no pisarlo

    const id = getActiveScenarioId();
    if (!id) return;

    (async () => {
      const found = await load(id);
      if (found) hydrate(found.features ?? {}); // repuebla el mapa y vuela hacia la zona
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return null;
}