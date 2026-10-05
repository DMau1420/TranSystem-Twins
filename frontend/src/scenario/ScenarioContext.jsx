// src/scenario/ScenarioContext.jsx
import { createContext, useCallback, useContext, useMemo, useReducer, useState } from 'react';
import { initialState, scenarioReducer } from './scenarioReducer';
import { countEdits, createScenario } from './scenarioSchema';
import { getScenario, saveScenario } from './scenarioStorage';

const ScenarioContext = createContext(null);

const AUTOSAVE_KEY = 'tst:autosave';
const readAutoSave = () => {
  try {
    return localStorage.getItem(AUTOSAVE_KEY) !== 'off'; // por defecto: activado
  } catch {
    return true;
  }
};

export function ScenarioProvider({ children }) {
  const [state, dispatch] = useReducer(scenarioReducer, undefined, () => initialState());
  const { present: scenario, past, future, savedDoc, selection } = state;

  // Estado de interfaz (no se guarda en el escenario)
  const [targetProjectId, setTargetProjectId] = useState(null); // null = proyecto nuevo automático
  const [autoSave, setAutoSaveState] = useState(readAutoSave);
  const [saveStatus, setSaveStatus] = useState('idle'); // idle | saving | saved | error

  const setAutoSave = useCallback((on) => {
    setAutoSaveState(on);
    try {
      localStorage.setItem(AUTOSAVE_KEY, on ? 'on' : 'off');
    } catch {
      /* sin almacenamiento: se mantiene solo en memoria */
    }
  }, []);

  // Edición
  const setArea = useCallback((area, network) => dispatch({ type: 'SET_AREA', area, network }), []);
  const rename = useCallback((name) => dispatch({ type: 'RENAME', name }), []);
  const setEdgeProp = useCallback(
    (id, prop, value) => dispatch({ type: 'SET_EDGE_PROP', id, prop, value }),
    []
  );
  const resetEdge = useCallback((id) => dispatch({ type: 'RESET_EDGE', id }), []);
  const setTls = useCallback((id, phases) => dispatch({ type: 'SET_TLS', id, phases }), []);
  const resetJunction = useCallback((id) => dispatch({ type: 'RESET_JUNCTION', id }), []);

  // Selección (solo UI)
  const select = useCallback((sel) => dispatch({ type: 'SELECT', selection: sel }), []);
  const clearSelection = useCallback(() => dispatch({ type: 'SELECT', selection: null }), []);

  // Historial
  const undo = useCallback(() => dispatch({ type: 'UNDO' }), []);
  const redo = useCallback(() => dispatch({ type: 'REDO' }), []);

  // Persistencia
  // save(patch): aplica proyecto/nombre/features justo al guardar, sin depender de un dispatch previo
  const save = useCallback(async (patch = {}) => {
    const saved = await saveScenario({ ...scenario, ...patch });
    dispatch({ type: 'MARK_SAVED', scenario: saved });
    return saved;
  }, [scenario]);

  const load = useCallback(async (id) => {
    const found = await getScenario(id);
    if (found) {
      dispatch({ type: 'LOAD', scenario: found });
      setSaveStatus('idle');
    }
    return found;
  }, []);

  // Escenario nuevo (vacío)
  const create = useCallback((opts) => {
    dispatch({ type: 'LOAD', scenario: createScenario(opts) });
    setSaveStatus('idle');
  }, []);

  const value = useMemo(
    () => ({
      scenario,
      selection,
      dirty: scenario !== savedDoc, // comparación por referencia: deshacer hasta el guardado => false
      canUndo: past.length > 0,
      canRedo: future.length > 0,
      editCount: countEdits(scenario),
      targetProjectId,
      setTargetProjectId,
      autoSave,
      setAutoSave,
      saveStatus,
      setSaveStatus,
      setArea,
      rename,
      setEdgeProp,
      resetEdge,
      setTls,
      resetJunction,
      select,
      clearSelection,
      undo,
      redo,
      save,
      load,
      create,
    }),
    [
      scenario, selection, savedDoc, past.length, future.length,
      targetProjectId, autoSave, setAutoSave, saveStatus,
      setArea, rename, setEdgeProp, resetEdge, setTls, resetJunction,
      select, clearSelection, undo, redo, save, load, create,
    ]
  );

  return <ScenarioContext.Provider value={value}>{children}</ScenarioContext.Provider>;
}

export function useScenario() {
  const ctx = useContext(ScenarioContext);
  if (!ctx) throw new Error('useScenario debe usarse dentro de <ScenarioProvider>');
  return ctx;
}