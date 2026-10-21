// src/scenario/useSimulacion.js
//
// Flujo (según backend/README.md):
//   1. Cliente abre ws://.../ws/simular y envía el payload del escenario.
//   2. Backend responde { status: "iniciando", progress: 0 }.
//   3. Backend hace proxy hacia SUMO y espera.
//   4. Backend responde { status: "completado", progress: 100, resultado: {...} }.
//
// ⚠️ El README no muestra el mensaje de error ni estados intermedios de
// progreso real — aquí se asume que cualquier status distinto de
// "iniciando"/"completado" (p.ej. "error", "fallido") se trata como fallo, y
// que el socket puede mandar varios mensajes de progreso antes del final.
// Ajusta estos nombres si el backend usa otros.
import { useCallback, useRef, useState } from 'react';
import { WS_BASE } from '../api/config';
import { ensureEnBackend } from './backendSync';

const ESTADOS_OK = new Set(['iniciando', 'corriendo', 'en_cola', 'procesando']);
const ESTADOS_FINAL_OK = new Set(['completado', 'terminado', 'finalizado']);
const ESTADOS_FINAL_ERROR = new Set(['error', 'fallido', 'fallida']);

export function useSimulacion({ token, scenario, features, nombreProyectoLocal, save }) {
  // idle | sincronizando | conectando | simulando | completado | error
  const [estado, setEstado] = useState('idle');
  const [progreso, setProgreso] = useState(0);
  const [resultado, setResultado] = useState(scenario.features === features ? null : null);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);

  const cancelar = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    setEstado('idle');
    setProgreso(0);
  }, []);

  const simular = useCallback(async () => {
    setError(null);
    setResultado(null);
    setProgreso(0);

    try {
      setEstado('sincronizando');
      const backend = await ensureEnBackend({ token, scenario, features, nombreProyectoLocal, save });

      setEstado('conectando');
      const ws = new WebSocket(`${WS_BASE}/ws/simular`);
      wsRef.current = ws;

      ws.onopen = () => {
        // Se manda el id del escenario ya persistido en el backend; algunos
        // backends esperan además el payload completo — si el tuyo lo
        // requiere, agrégalo aquí junto a escenario_id.
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
          // status desconocido: lo mostramos igual para no perder información
          console.warn('Estado de simulación no reconocido:', msg.status);
        }
      };

      ws.onerror = () => {
        setError('No se pudo conectar con el servidor de simulación.');
        setEstado('error');
      };

      ws.onclose = () => {
        wsRef.current = null;
      };
    } catch (err) {
      console.error('Error preparando la simulación:', err);
      setError(err.message ?? 'No se pudo iniciar la simulación.');
      setEstado('error');
    }
  }, [token, scenario, features, nombreProyectoLocal, save]);

  return { estado, progreso, resultado, error, simular, cancelar };
}