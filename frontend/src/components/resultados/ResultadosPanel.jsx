import { useCallback, useEffect, useRef, useState } from 'react';
import '../shared/sysBlocks.css';
import './ResultadosPanel.css';

// CU-14: historial de corridas de un escenario.
// Lista (listarResultados), detalle (obtenerResultado) y eliminación (eliminarResultado).
//
// Props:
//   escenarioId   id del escenario activo
//   api           { listarResultados, obtenerResultado, eliminarResultado }
//   onEliminado   (id) => void   opcional, para refrescar la "última corrida" del modal
//   onSeleccionar (resultado) => void  opcional, p. ej. para pintar el resultado en el mapa

const normalizaLista = (res) =>
  Array.isArray(res) ? res : (res?.resultados ?? res?.items ?? res?.data ?? []);

const fechaDe = (r) => r?.creado_en ?? r?.created_at ?? r?.fecha ?? r?.timestamp ?? null;

function formatFecha(valor) {
  if (!valor) return 'Sin fecha';
  const d = new Date(valor);
  if (Number.isNaN(d.getTime())) return String(valor);
  return d.toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' });
}

// Aplana objetos anidados a filas clave/valor; recorta textos largos (p. ej. PDF en base64).
function aplana(obj, prefijo = '', filas = [], nivel = 0) {
  if (obj == null) return filas;
  for (const [k, v] of Object.entries(obj)) {
    const clave = prefijo ? `${prefijo}.${k}` : k;
    if (v && typeof v === 'object' && nivel < 3) {
      aplana(v, clave, filas, nivel + 1);
    } else {
      let texto = v == null ? '—' : String(v);
      if (texto.length > 120) texto = `${texto.slice(0, 120)}… (${texto.length} caracteres)`;
      filas.push([clave, texto]);
    }
  }
  return filas;
}

export default function ResultadosPanel({ escenarioId, api, onEliminado, onSeleccionar }) {
  const [lista, setLista] = useState([]);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(null);

  const [seleccionId, setSeleccionId] = useState(null);
  const [detalle, setDetalle] = useState(null);
  const [cargandoDetalle, setCargandoDetalle] = useState(false);
  const [errorDetalle, setErrorDetalle] = useState(null);

  const [confirmarId, setConfirmarId] = useState(null);
  const [eliminandoId, setEliminandoId] = useState(null);

  // Evita que una respuesta lenta pise a una más reciente.
  const reqLista = useRef(0);
  const reqDetalle = useRef(0);

  const cargarLista = useCallback(async () => {
    if (!escenarioId) {
      setLista([]);
      return;
    }
    const id = ++reqLista.current;
    setCargando(true);
    setError(null);
    try {
      const res = await api.listarResultados(escenarioId);
      if (id !== reqLista.current) return;
      const items = normalizaLista(res);
      // Más reciente primero
      items.sort((a, b) => new Date(fechaDe(b) ?? 0) - new Date(fechaDe(a) ?? 0));
      setLista(items);
    } catch (e) {
      if (id !== reqLista.current) return;
      setError(e?.message || 'No se pudo cargar el historial de corridas.');
    } finally {
      if (id === reqLista.current) setCargando(false);
    }
  }, [api, escenarioId]);

  useEffect(() => {
    setSeleccionId(null);
    setDetalle(null);
    setConfirmarId(null);
    cargarLista();
  }, [cargarLista]);

  const verDetalle = async (resultado) => {
    const rid = resultado.id;
    if (rid === seleccionId) {
      setSeleccionId(null);
      setDetalle(null);
      return;
    }
    const id = ++reqDetalle.current;
    setSeleccionId(rid);
    setDetalle(null);
    setErrorDetalle(null);
    setCargandoDetalle(true);
    try {
      const res = await api.obtenerResultado(rid);
      if (id !== reqDetalle.current) return;
      setDetalle(res);
      onSeleccionar?.(res);
    } catch (e) {
      if (id !== reqDetalle.current) return;
      setErrorDetalle(e?.message || 'No se pudo cargar el detalle de la corrida.');
    } finally {
      if (id === reqDetalle.current) setCargandoDetalle(false);
    }
  };

  const eliminar = async (rid) => {
    setEliminandoId(rid);
    setError(null);
    try {
      await api.eliminarResultado(rid);
      setLista((prev) => prev.filter((r) => r.id !== rid));
      if (rid === seleccionId) {
        setSeleccionId(null);
        setDetalle(null);
      }
      setConfirmarId(null);
      onEliminado?.(rid);
    } catch (e) {
      setError(e?.message || 'No se pudo eliminar la corrida.');
    } finally {
      setEliminandoId(null);
    }
  };

  if (!escenarioId) {
    return (
      <section className="sysb resp">
        <h3 className="sysb-title">// RESULTADOS // HISTORIAL</h3>
        <p className="sysb-muted">Selecciona un escenario para ver sus corridas anteriores.</p>
      </section>
    );
  }

  return (
    <section className="sysb resp" aria-label="Historial de resultados">
      <header className="resp-head">
        <h3 className="sysb-title">// RESULTADOS // HISTORIAL</h3>
        <button type="button" className="sysb-btn" onClick={cargarLista} disabled={cargando}>
          {cargando ? 'Cargando…' : 'Actualizar'}
        </button>
      </header>

      {error && (
        <p role="alert" className="sysb-error">
          {error}
        </p>
      )}

      {!cargando && !error && lista.length === 0 && (
        <p className="sysb-muted">
          Este escenario todavía no tiene corridas. Ejecuta una simulación para generar la primera.
        </p>
      )}

      <ul className="resp-list">
        {lista.map((r, idx) => {
          const abierto = r.id === seleccionId;
          return (
            <li key={r.id} className={`resp-item${abierto ? ' resp-item--open' : ''}`}>
              <div className="resp-row">
                <button
                  type="button"
                  className="resp-main"
                  onClick={() => verDetalle(r)}
                  aria-expanded={abierto}
                >
                  <span className="resp-date">{formatFecha(fechaDe(r))}</span>
                  <span className="sysb-muted">
                    {idx === 0 ? 'Última corrida' : `Corrida #${lista.length - idx}`}
                    {r.estado ? ` · ${r.estado}` : ''}
                  </span>
                </button>

                {confirmarId === r.id ? (
                  <span className="resp-confirm">
                    <button
                      type="button"
                      className="sysb-btn sysb-btn--danger"
                      onClick={() => eliminar(r.id)}
                      disabled={eliminandoId === r.id}
                    >
                      {eliminandoId === r.id ? 'Eliminando…' : 'Eliminar corrida'}
                    </button>
                    <button
                      type="button"
                      className="sysb-btn"
                      onClick={() => setConfirmarId(null)}
                      disabled={eliminandoId === r.id}
                    >
                      Cancelar
                    </button>
                  </span>
                ) : (
                  <button
                    type="button"
                    className="sysb-btn sysb-btn--danger"
                    onClick={() => setConfirmarId(r.id)}
                    aria-label={`Eliminar corrida del ${formatFecha(fechaDe(r))}`}
                  >
                    Eliminar
                  </button>
                )}
              </div>

              {abierto && (
                <div className="resp-detail">
                  {cargandoDetalle && <p className="sysb-muted">Cargando detalle…</p>}
                  {errorDetalle && (
                    <p role="alert" className="sysb-error">
                      {errorDetalle}
                    </p>
                  )}
                  {detalle && (
                    <div className="sysb-scroll">
                      <table className="sysb-table">
                        <tbody>
                          {aplana(detalle).map(([k, v]) => (
                            <tr key={k}>
                              <th scope="row">{k}</th>
                              <td>{v}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}