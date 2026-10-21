// src/scenario/scenarioReducer.js
import { LIMITS, clamp, createScenario } from './scenarioSchema';

const HISTORY_LIMIT = 100;

export const initialState = (scenario = createScenario()) => ({
  past: [],
  present: scenario, // documento en edición (se guarda)
  future: [],
  savedDoc: scenario, // último documento guardado, para calcular "dirty"
  selection: null, // { kind: 'edge' | 'junction', id } — solo UI, no se guarda
});

// Registra un cambio en el historial. Si nada cambió, no hace nada.
function commit(state, next) {
  if (next === state.present) return state;
  return {
    ...state,
    past: [...state.past, state.present].slice(-HISTORY_LIMIT),
    present: next,
    future: [],
  };
}

const withEdits = (doc, edits) => ({ ...doc, edits: { ...doc.edits, ...edits } });

const omit = (obj, key) => {
  const { [key]: _removed, ...rest } = obj;
  return rest;
};

export function scenarioReducer(state, action) {
  const doc = state.present;

  switch (action.type) {
    case 'LOAD': // cargar un escenario guardado: reinicia historial
      return initialState(action.scenario);

    case 'MARK_SAVED': // el guardado devuelve el doc con updatedAt nuevo
      return { ...state, present: action.scenario, savedDoc: action.scenario };

    case 'RENAME':
      return commit(state, { ...doc, name: action.name });

    case 'SET_DEMANDA': // vehículos por hora, total del escenario
      return commit(state, { ...doc, demandaVehicular: Math.max(0, Math.round(action.value)) });

    case 'SET_DURACION': // duración de la simulación, en segundos
      return commit(state, { ...doc, duracionSegundos: Math.max(1, Math.round(action.value)) });

    case 'SET_RESULTADO': // último resultado de simulación recibido (no pasa por el historial)
      return { ...state, present: { ...doc, ultimoResultado: action.resultado } };

    case 'SET_AREA': // zona dibujada/seleccionada + origen de la red
      return commit(state, {
        ...doc,
        area: action.area,
        network: action.network ?? doc.network,
      });

    case 'SET_EDGE_PROP': {
      const { id, prop, value } = action; // prop: 'maxspeed' | 'lanes'
      const range = prop === 'maxspeed' ? LIMITS.maxspeedKmh : LIMITS.lanes;
      let edge = { ...(doc.edits.edges[id] ?? {}) };
      if (value === null || value === undefined || value === '') delete edge[prop];
      else edge[prop] = clamp(value, range);

      const edges =
        Object.keys(edge).length === 0
          ? omit(doc.edits.edges, id)
          : { ...doc.edits.edges, [id]: edge };
      return commit(state, withEdits(doc, { edges }));
    }

    case 'RESET_EDGE':
      return commit(state, withEdits(doc, { edges: omit(doc.edits.edges, action.id) }));

    case 'SET_TLS': {
      const phases = action.phases.map((p) => ({
        ...p,
        duration: clamp(p.duration, LIMITS.phaseSeconds),
      }));
      return commit(
        state,
        withEdits(doc, {
          junctions: { ...doc.edits.junctions, [action.id]: { tls: { phases } } },
        })
      );
    }

    case 'RESET_JUNCTION':
      return commit(state, withEdits(doc, { junctions: omit(doc.edits.junctions, action.id) }));

    case 'SELECT':
      return { ...state, selection: action.selection };

    case 'UNDO': {
      if (!state.past.length) return state;
      const previous = state.past[state.past.length - 1];
      return {
        ...state,
        past: state.past.slice(0, -1),
        present: previous,
        future: [doc, ...state.future],
      };
    }

    case 'REDO': {
      if (!state.future.length) return state;
      const [next, ...rest] = state.future;
      return { ...state, past: [...state.past, doc], present: next, future: rest };
    }

    default:
      return state;
  }
}