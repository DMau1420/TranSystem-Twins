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
//  El README no muestra el mensaje de error ni estados intermedios de
// progreso real — aquí se asume que cualquier status distinto de
// "iniciando"/"completado" (p.ej. "error", "fallido") se trata como fallo, y
// que el socket puede mandar varios mensajes de progreso antes del final.
// Ajusta estos nombres si el backend usa otros.
import { useCallback, useEffect, useRef, useState } from 'react';
import { ensureEnBackend } from './backendSync';
import { generarResultadoCoherente } from './mockResultado';
import { crearWebSocketSimulacion, obtenerResultadoSimulacion } from '../api/simulacionApi';

const ESTADOS_OK = new Set(['iniciando', 'corriendo', 'en_cola', 'procesando', 'simulando']);
const ESTADOS_FINAL_OK = new Set(['completado', 'terminado', 'finalizado']);
const ESTADOS_FINAL_ERROR = new Set(['error', 'fallido', 'fallida']);

const MOCK_DURACION_MS = 1800; // qué tan "tardada" se siente la simulación inventada

/**
 * Hook que gestiona el ciclo de vida completo de una simulación:
 * 1. Sincroniza el escenario local con el backend (ensureEnBackend).
 * 2. Abre un WebSocket autenticado al endpoint /ws/simular.
 * 3. Al completarse, el backend persiste automáticamente el resultado en BD.
 * 4. Si el WebSocket falla, cae a datos simulados localmente (mock).
 *
 * Props:
 *  - token         JWT del usuario (de useAuth).
 *  - scenario      Escenario activo (de useScenario).
 *  - features      Puntos/rutas/zonas del mapa (de useMapData).
 *  - nombreProyectoLocal  Nombre para el proyecto nuevo si no existe aún.
 *  - save          Función save de useScenario.
 */
export function useSimulacion({ token, scenario, features, nombreProyectoLocal, save }) {
  // idle | sincronizando | conectando | simulando | completado | error
  const [estado, setEstado] = useState('idle');
  const [progreso, setProgreso] = useState(0);
  const [mensaje, setMensaje] = useState('');
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);
  const mockTimersRef = useRef([]); // setTimeout/setInterval ids del fallback inventado

  // Ref para mantener siempre las props más recientes sin disparar re-creaciones.
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
    setMensaje('');
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
    setMensaje('');
    setResultado(null);
    setError(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scenarioId]);

  // Resultado inventado, pero coherente con la demanda/duración configuradas.
  // Simula una barra de progreso para que no se sienta instantáneo/falso.
  const simularConDatosInventados = useCallback(() => {
    setEstado('simulando');
    setMensaje('Simulando con parámetros configurados...');
    const currentScenario = propsRef.current.scenario;
    const pasos = [
      { pct: 20, msg: 'Descargando geometría de calles...' },
      { pct: 45, msg: 'Construyendo red y semáforos...' },
      { pct: 70, msg: 'Generando demanda y rutas de vehículos...' },
      { pct: 90, msg: 'Simulando tráfico en motor local...' },
    ];
    pasos.forEach(({ pct, msg }, i) => {
      const t = setTimeout(() => {
        setProgreso(pct);
        setMensaje(msg);
      }, (MOCK_DURACION_MS / (pasos.length + 1)) * (i + 1));
      mockTimersRef.current.push(t);
    });
    const final = setTimeout(() => {
      const inventado = generarResultadoCoherente(currentScenario);
      setProgreso(100);
      setMensaje('Simulación completada con éxito.');
      setResultado(inventado);
      setEstado('completado');
    }, MOCK_DURACION_MS);
    mockTimersRef.current.push(final);
  }, []);

  // ── Simulación principal ──────────────────────────────────────────────────
  const simular = useCallback(async () => {
    setError(null);
    setResultado(null);
    setProgreso(0);
    setMensaje('Iniciando proceso de simulación...');
    limpiarMockTimers();

    const { token: currentToken, scenario: currentScenario, features: currentFeatures, nombreProyectoLocal: currentProjectName, save: currentSave } = propsRef.current;

    setEstado('sincronizando');
    setMensaje('Sincronizando escenario con el backend...');
    let backend;
    try {
      backend = await ensureEnBackend({
        token: currentToken,
        scenario: currentScenario,
        features: currentFeatures,
        nombreProyectoLocal: currentProjectName,
        save: currentSave,
      });
    } catch (err) {
      console.warn('[useSimulacion] No se pudo sincronizar con el backend, usando datos inventados:', err.message);
      simularConDatosInventados();
      return;
    }

    // 2. Abrir WebSocket de simulación
    try {
      setEstado('conectando');
      setMensaje('Conectando al microservicio de simulación SUMO...');
      const ws = crearWebSocketSimulacion(currentToken);
      wsRef.current = ws;

      ws.onopen = () => {
        ws.send(JSON.stringify({
          escenario_id: backend.escenarioId,
          duracion_segundos: currentScenario.duracionSegundos ?? 3600,
          demanda_vehicular: currentScenario.demandaVehicular ?? 100,
        }));
        setEstado('simulando');
        setMensaje('Enviada solicitud a SUMO, esperando inicio...');
      };

      ws.onmessage = async (event) => {
        let msg;
        try {
          msg = JSON.parse(event.data);
        } catch {
          setError('Respuesta no válida del servidor de simulación.');
          setEstado('error');
          return;
        }

        if (typeof msg.progress === 'number') setProgreso(msg.progress);
        const liveText = msg.message || msg.detail;
        if (liveText) setMensaje(liveText);

        if (ESTADOS_FINAL_OK.has(msg.status)) {
          // Intenta obtener el resultado detallado del backend si el WS no lo envió.
          // El backend ya persiste el resultado automáticamente al completar /ws/simular.
          let resultadoFinal = msg.resultado ?? null;
          if (!resultadoFinal && currentToken) {
            try {
              resultadoFinal = await obtenerResultadoSimulacion(currentToken);
            } catch {
              /* fallback: sin resultado del backend */
            }
          }
          setProgreso(100);
          setMensaje(msg.message || 'Simulación completada exitosamente.');
          setResultado(resultadoFinal);
          setEstado('completado');
          ws.close();
        } else if (ESTADOS_FINAL_ERROR.has(msg.status)) {
          setError(msg.detail ?? msg.message ?? 'La simulación falló.');
          setMensaje(msg.detail ?? msg.message ?? 'Error en la simulación.');
          setEstado('error');
          ws.close();
        } else if (!ESTADOS_OK.has(msg.status)) {
          // status desconocido: lo mostramos igual para no perder información
          console.warn('[useSimulacion] Estado de simulación no reconocido:', msg.status);
        }
      };

      // Si no conecta el WS, caemos a datos inventados en vez de error.
      ws.onerror = () => {
        console.warn('[useSimulacion] No se pudo conectar al WebSocket, usando datos inventados.');
        wsRef.current = null;
        simularConDatosInventados();
      };

      ws.onclose = () => {
        wsRef.current = null;
      };
    } catch (err) {
      console.error('[useSimulacion] Error preparando la simulación:', err);
      simularConDatosInventados();
    }
  }, [simularConDatosInventados]);

  return { estado, progreso, mensaje, resultado, error, simular, cancelar };
}