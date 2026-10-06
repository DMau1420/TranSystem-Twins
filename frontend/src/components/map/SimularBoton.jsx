import { useEffect, useState } from 'react';
import { useProyecto } from '../../context/ProyectoContext';
import { simularEscenario } from '../../api/proyectosApi';
import { sysCore } from '../../styles/sysCore';

// [clave en el resultado, etiqueta, unidad]
const INDICADORES = [
  ['vehiculos_atendidos', 'Vehículos atendidos', ''],
  ['tiempo_promedio_recorrido', 'Tiempo prom. de recorrido', 's'],
  ['tiempo_promedio_espera', 'Espera promedio', 's'],
  ['velocidad_promedio', 'Velocidad promedio', 'km/h'],
  ['longitud_max_fila', 'Fila máxima', ''],
];

const S = {
  wrap: {
    position: 'absolute', right: 16, bottom: 40, zIndex: 1001,
    display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6,
    fontFamily: sysCore.font.mono, fontSize: 12,
  },
  btn: (off) => ({
    padding: '10px 16px', cursor: off ? 'not-allowed' : 'pointer', opacity: off ? 0.6 : 1,
    fontFamily: sysCore.font.mono, fontSize: 12, textTransform: 'uppercase', borderRadius: 3,
    background: 'rgba(45, 227, 255, 0.15)', color: sysCore.color.cyan,
    border: `1px solid ${sysCore.color.cyan}`, backdropFilter: 'blur(6px)',
  }),
  link: {
    background: 'none', border: 'none', cursor: 'pointer', padding: 0,
    fontFamily: sysCore.font.mono, fontSize: 11, color: sysCore.color.inkMuted,
    textDecoration: 'underline',
  },
  err: {
    maxWidth: 280, fontSize: 11, color: '#ff6b6b', textAlign: 'right',
    background: sysCore.color.panel, border: '1px solid #ff6b6b', borderRadius: 3, padding: '6px 8px',
  },
  overlay: {
    position: 'absolute', inset: 0, zIndex: 2000, display: 'flex',
    alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.55)',
  },
  modal: {
    width: 360, maxWidth: '90%', background: sysCore.color.panel, backdropFilter: 'blur(6px)',
    border: `1px solid ${sysCore.color.borderStrong}`, borderRadius: 4, padding: 20,
    fontFamily: sysCore.font.mono, fontSize: 12, color: sysCore.color.ink,
  },
  titulo: { fontSize: 14, fontWeight: 600, color: sysCore.color.cyan },
  sub: { fontSize: 11, color: sysCore.color.inkMuted, marginTop: 2, marginBottom: 14 },
  fila: {
    display: 'flex', justifyContent: 'space-between', padding: '8px 0',
    borderTop: `1px solid ${sysCore.color.border}`,
  },
  valor: { color: sysCore.color.cyan, fontWeight: 600 },
  nota: { fontSize: 10.5, lineHeight: 1.4, color: '#e0c060', marginTop: 12 },
  cerrar: (primario) => ({
    marginTop: 14, width: '100%', padding: '8px 10px', cursor: 'pointer', borderRadius: 3,
    fontFamily: sysCore.font.mono, fontSize: 11, textTransform: 'uppercase',
    background: 'rgba(45, 227, 255, 0.15)', color: sysCore.color.cyan,
    border: `1px solid ${sysCore.color.cyan}`,
  }),
};

export default function SimularBoton() {
  const { escenarioActivo, recargarEscenarios } = useProyecto();
  const [simulando, setSimulando] = useState(false);
  const [segundos, setSegundos] = useState(0);
  const [error, setError] = useState(null);
  const [modal, setModal] = useState(false);
  const [local, setLocal] = useState(null); // { id, data } del último resultado recibido

  // Cronómetro mientras corre la simulación (puede tardar minutos)
  useEffect(() => {
    if (!simulando) return undefined;
    setSegundos(0);
    const t = setInterval(() => setSegundos((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [simulando]);

  if (!escenarioActivo) return null;

  const resultado =
    local?.id === escenarioActivo.id ? local.data : escenarioActivo.resultado ?? null;

  async function simular() {
    setSimulando(true);
    setError(null);
    try {
      const data = await simularEscenario(escenarioActivo.id);
      setLocal({ id: escenarioActivo.id, data: data?.resultado ?? data });
      setModal(true);
      await recargarEscenarios();
    } catch (err) {
      setError(err.message || 'No se pudo simular');
    } finally {
      setSimulando(false);
    }
  }

  return (
    <>
      <div style={S.wrap}>
        {error && <div style={S.err}>{error}</div>}
        <button style={S.btn(simulando)} disabled={simulando} onClick={simular}>
          {simulando ? `Simulando... ${segundos}s` : '▶ Simular escenario'}
        </button>
        {resultado && !simulando && (
          <button style={S.link} onClick={() => setModal(true)}>ver último resultado</button>
        )}
      </div>

      {modal && resultado && (
        <div style={S.overlay} onClick={() => setModal(false)}>
          <div style={S.modal} onClick={(e) => e.stopPropagation()}>
            <div style={S.titulo}>Resultados de la simulación</div>
            <div style={S.sub}>Escenario: {escenarioActivo.nombre}</div>

            {INDICADORES.map(([clave, etiqueta, unidad]) => (
              <div key={clave} style={S.fila}>
                <span>{etiqueta}</span>
                <span style={S.valor}>
                  {resultado[clave] ?? '—'}{unidad && resultado[clave] != null ? ` ${unidad}` : ''}
                </span>
              </div>
            ))}

            <div style={S.nota}>
              Los números pueden variar un poco entre corridas del mismo escenario
              (la demanda aún no usa semilla fija).
            </div>

            <button style={S.cerrar(true)} onClick={() => setModal(false)}>Cerrar</button>
          </div>
        </div>
      )}
    </>
  );
}