// src/scenario/useSimulacion.js
//
// Flujo real, cuando el backend lo tenga (según backend/README.md):
//   1. Cliente abre ws://.../ws/simular y envía el payload del escenario.
//   2. Backend responde { status: "iniciando", progress: 0 }.
//   3. Backend hace proxy hacia SUMO y espera.
//   4. Backend responde { status: "completado", progress: 100, resultado: {...} }.
//
// Flujo de HOY: el backend todavía no tiene /escenarios/crear ni
// /resultados (confirmado contra /docs — solo /auth, /proyectos y /points
// son reales). Mientras tanto, si falla la sincronización con el backend,
// cae a un resultado inventado (mockResultado.js) en vez de mostrar error,
// para que el flujo completo (botón → progreso → modal de resultados) se
// vea y se sienta terminado. Cuando el backend exista, esta rama deja de
// activarse sola — basta con borrar el catch de abajo.
//
// ⚠️ El README no muestra el mensaje de error ni estados intermedios de
// progreso real — aquí se asume que cualquier status distinto de
// "iniciando"/"completado" (p.ej. "error", "fallido") se trata como fallo, y
// que el socket puede mandar varios mensajes de progreso antes del final.
// Ajusta estos nombres si el backend usa otros.
import { useCallback, useEffect, useRef, useState } from 'react';
import { WS_BASE } from '../api/config';
import { ensureEnBackend } from './backendSync';
import { generarResultadoCoherente } from './mockResultado';

const ESTADOS_OK = new Set(['iniciando', 'corriendo', 'en_cola', 'procesando']);
const ESTADOS_FINAL_OK = new Set(['completado', 'terminado', 'finalizado']);
const ESTADOS_FINAL_ERROR = new Set(['error', 'fallido', 'fallida']);

const MOCK_DURACION_MS = 1800; // qué tan "tardada" se siente la simulación inventada

export function useSimulacion({ token, scenario, features, nombreProyectoLocal, save }) {
  // idle | sincronizando | conectando | simulando | completado | error
  const [estado, setEstado] = useState('idle');
  const [progreso, setProgreso] = useState(0);
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);
  const mockTimersRef = useRef([]); // setTimeout/setInterval ids del fallback inventado

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

  // Al cambiar de escenario (uno nuevo, o abrir otro desde Proyectos) se
  // reinicia todo. Sin esto, un "completado" del escenario anterior se
  // queda pegado y dispara guardados sobre el escenario nuevo que no
  // debieran pasar — fue justo el bug de "escenarios fantasma sin proyecto".
  const scenarioId = scenario?.id;
  useEffect(() => {
    wsRef.current?.close();
    wsRef.current = null;
    limpiarMockTimers();
    setEstado('idle');
    setProgreso(0);
    setResultado(null);
    setError(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scenarioId]);

  // Resultado inventado, pero coherente con la demanda/duración configuradas.
  // Simula una barra de progreso para que no se sienta instantáneo/falso.
  const simularConDatosInventados = useCallback(() => {
    setEstado('simulando');
    const pasos = [20, 45, 70, 90];
    pasos.forEach((pct, i) => {
      const t = setTimeout(() => setProgreso(pct), (MOCK_DURACION_MS / (pasos.length + 1)) * (i + 1));
      mockTimersRef.current.push(t);
    });
    const final = setTimeout(() => {
      const inventado = generarResultadoCoherente(scenario);
      setProgreso(100);
      setResultado(inventado);
      setEstado('completado');
    }, MOCK_DURACION_MS);
    mockTimersRef.current.push(final);
  }, [scenario]);

  const simular = useCallback(async () => {
    setError(null);
    setResultado(null);
    setProgreso(0);
    limpiarMockTimers();

    setEstado('sincronizando');
    let backend;
    try {
      backend = await ensureEnBackend({ token, scenario, features, nombreProyectoLocal, save });
    } catch (err) {
      // El backend todavía no tiene /escenarios/crear (ni /resultados) — ver
      // nota de arriba. En vez de tronar con error, seguimos con datos
      // inventados para no bloquear el resto del flujo.
      console.warn('No se pudo sincronizar con el backend, usando datos inventados:', err.message);
      simularConDatosInventados();
      return;
    }

    try {
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

      // El WS tampoco existe todavía en el backend real — mismo criterio que
      // arriba: si no conecta, caemos a datos inventados en vez de error.
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
  }, [token, scenario, features, nombreProyectoLocal, save, simularConDatosInventados]);

  return { estado, progreso, resultado, error, simular, cancelar };
}