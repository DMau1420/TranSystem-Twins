// src/scenario/useSimulacion.js
import { useCallback, useEffect, useRef, useState } from 'react';
import { WS_BASE } from '../api/config';
import { ensureEnBackend } from './backendSync';
import { generarResultadoCoherente } from './mockResultado';

const ESTADOS_OK = new Set(['iniciando', 'corriendo', 'en_cola', 'procesando']);
const ESTADOS_FINAL_OK = new Set(['completado', 'terminado', 'finalizado']);
const ESTADOS_FINAL_ERROR = new Set(['error', 'fallido', 'fallida']);

const MOCK_DURACION_MS = 1800;

export function useSimulacion({ token, scenario, features, nombreProyectoLocal, save }) {
  // idle | sincronizando | conectando | simulando | completado | error
  const [estado, setEstado] = useState('idle');
  const [progreso, setProgreso] = useState(0);
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState(null);
  
  const wsRef = useRef(null);
  const mockTimersRef = useRef([]);

  // Usamos un ref para mantener siempre las props más recientes sin disparar
  // re-creaciones de los useCallback en cada render si la función 'save' cambia de referencia.
  const propsRef = useRef({ token, scenario, features, nombreProyectoLocal, save });
  useEffect(() => {
    propsRef.current = { token, scenario, features, nombreProyectoLocal, save };
  });

  const limpiarMockTimers = () => {
    mockTimersRef.current.forEach(clearTimeout);
    mockTimersRef.current = [];
  };

  const cancelar = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    limpiarMockTimers();
    setEstado('idle');
    setProgreso(0);
  }, []);

  // Limpieza al cambiar de escenario
  const scenarioId = scenario?.id;
  useEffect(() => {
    wsRef.current?.close();
    wsRef.current = null;
    limpiarMockTimers();
    setEstado('idle');
    setProgreso(0);
    setResultado(null);
    setError(null);
  }, [scenarioId]);

  const simularConDatosInventados = useCallback(() => {
    setEstado('simulando');
    const currentScenario = propsRef.current.scenario;
    const pasos = [20, 45, 70, 90];
    
    pasos.forEach((pct, i) => {
      const t = setTimeout(() => setProgreso(pct), (MOCK_DURACION_MS / (pasos.length + 1)) * (i + 1));
      mockTimersRef.current.push(t);
    });
    
    const final = setTimeout(() => {
      const inventado = generarResultadoCoherente(currentScenario);
      setProgreso(100);
      setResultado(inventado);
      setEstado('completado');
    }, MOCK_DURACION_MS);
    
    mockTimersRef.current.push(final);
  }, []);

  const simular = useCallback(async () => {
    setError(null);
    setResultado(null);
    setProgreso(0);
    limpiarMockTimers();

    const { token, scenario, features, nombreProyectoLocal, save } = propsRef.current;

    setEstado('sincronizando');
    let backend;
    try {
      backend = await ensureEnBackend({ token, scenario, features, nombreProyectoLocal, save });
    } catch (err) {
      console.warn('No se pudo sincronizar con el backend, usando datos inventados:', err.message);
      simularConDatosInventados();
      return;
    }

    try {
      setEstado('conectando');
      const ws = new WebSocket(`${WS_BASE}/ws/simular`);
      wsRef.current = ws;

      ws.onopen = () => {
        ws.send(JSON.stringify({ escenario_id: backend.escenarioId }));
        setEstado('simulando');
      };

      ws.onmessage = (event) => {
        let msg;
        try {
          msg = JSON.parse(event.data);
        } catch {
          setError('Respuesta no válida del servidor de simulación.');
          setEstado('error');
          return;
        }

        if (typeof msg.progress === 'number') setProgreso(msg.progress);

        if (ESTADOS_FINAL_OK.has(msg.status)) {
          setResultado(msg.resultado ?? null);
          setEstado('completado');
          ws.close();
        } else if (ESTADOS_FINAL_ERROR.has(msg.status)) {
          setError(msg.detail ?? 'La simulación falló.');
          setEstado('error');
          ws.close();
        } else if (!ESTADOS_OK.has(msg.status)) {
          console.warn('Estado de simulación no reconocido:', msg.status);
        }
      };

      ws.onerror = () => {
        console.warn('No se pudo conectar al WebSocket de simulación, usando datos inventados.');
        wsRef.current = null;
        simularConDatosInventados();
      };

      ws.onclose = () => {
        wsRef.current = null;
      };
    } catch (err) {
      console.error('Error preparando la simulación:', err);
      simularConDatosInventados();
    }
  }, [simularConDatosInventados]);

  return { estado, progreso, resultado, error, simular, cancelar };
}