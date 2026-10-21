import { useState } from 'react';
import { useProyecto } from '../../context/ProyectoContext';
import { modificarEdge, modificarSemaforo } from '../../api/proyectosApi';
import { sysCore } from '../../styles/sysCore';

const S = {
  box: {
    position: 'absolute', left: 16, bottom: 16, width: 300, maxHeight: '70vh', overflowY: 'auto',
    zIndex: 1001, background: sysCore.color.panel, backdropFilter: 'blur(6px)',
    border: `1px solid ${sysCore.color.borderStrong}`, borderRadius: 4, padding: 16,
    fontFamily: sysCore.font.mono, fontSize: 12, color: sysCore.color.ink,
  },
  head: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 },
  nombre: { fontSize: 14, fontWeight: 600, color: sysCore.color.cyan },
  id: { fontSize: 11, color: sysCore.color.inkMuted, wordBreak: 'break-all', marginTop: 2 },
  x: { background: 'none', border: 'none', color: sysCore.color.inkMuted, cursor: 'pointer', fontSize: 15 },
  label: { display: 'block', fontSize: 10.5, color: sysCore.color.inkMuted, margin: '10px 0 4px', textTransform: 'uppercase' },
  input: {
    width: '100%', boxSizing: 'border-box', padding: '6px 8px', background: 'rgba(255,255,255,0.05)',
    border: `1px solid ${sysCore.color.border}`, borderRadius: 3, color: sysCore.color.ink,
    fontFamily: sysCore.font.mono, fontSize: 12,
  },
  info: { fontSize: 10.5, color: sysCore.color.inkMuted, marginTop: 3 },
  fase: { border: `1px solid ${sysCore.color.border}`, borderRadius: 3, padding: 8, marginTop: 8 },
  fila: { display: 'flex', gap: 8, marginTop: 14 },
  btn: (primario, off) => ({
    flex: 1, padding: '8px 10px', cursor: off ? 'not-allowed' : 'pointer', opacity: off ? 0.5 : 1,
    fontFamily: sysCore.font.mono, fontSize: 11, textTransform: 'uppercase', borderRadius: 3,
    background: primario ? 'rgba(45, 227, 255, 0.15)' : 'transparent',
    color: primario ? sysCore.color.cyan : sysCore.color.inkMuted,
    border: `1px solid ${primario ? sysCore.color.cyan : sysCore.color.border}`,
  }),
  msg: (ok) => ({ marginTop: 10, fontSize: 11, color: ok ? sysCore.color.cyan : '#ff6b6b' }),
  aviso: { marginTop: 10, fontSize: 10.5, lineHeight: 1.4, color: '#e0c060' },
};

function PanelCalle({ p, escenario, guardado, onGuardado }) {
  const [carriles, setCarriles] = useState(guardado?.carriles ?? p.carriles);
  const [velocidad, setVelocidad] = useState(guardado?.velocidad_max ?? p.velocidad_max);
  const [msg, setMsg] = useState(null);
  const [guardando, setGuardando] = useState(false);

  async function guardar() {
    const c = parseInt(carriles, 10);
    const v = parseFloat(velocidad);
    if (!(c >= 1 && c <= 10)) return setMsg({ ok: false, t: 'Los carriles deben ser entre 1 y 10' });
    if (!(v >= 5 && v <= 120)) return setMsg({ ok: false, t: 'La velocidad debe ser entre 5 y 120 km/h' });

    setGuardando(true);
    try {
      await modificarEdge(escenario.id, p.edge_id, { carriles: c, velocidad_max: v });
      await onGuardado();
      setMsg({ ok: true, t: 'Guardado en el escenario' });
    } catch (err) {
      setMsg({ ok: false, t: `No se pudo guardar: ${err.message}` });
    } finally {
      setGuardando(false);
    }
  }

  function restaurar() {
    setCarriles(p.carriles);
    setVelocidad(p.velocidad_max);
    setMsg({ ok: true, t: 'Valores originales (sin guardar todavía)' });
  }

  return (
    <>
      <label style={S.label}>Carriles</label>
      <input style={S.input} type="number" min="1" max="10" value={carriles}
             onChange={(e) => setCarriles(e.target.value)} />
      <div style={S.info}>Original: {p.carriles}</div>

      <label style={S.label}>Velocidad máxima (km/h)</label>
      <input style={S.input} type="number" min="5" max="120" step="5" value={velocidad}
             onChange={(e) => setVelocidad(e.target.value)} />
      <div style={S.info}>Original: {p.velocidad_max} km/h</div>

      <label style={S.label}>Tipo · Longitud</label>
      <div style={S.info}>{p.tipo || 'desconocido'} · {p.longitud} m</div>

      <div style={S.fila}>
        <button style={S.btn(true, guardando)} disabled={guardando} onClick={guardar}>
          {guardando ? 'Guardando...' : 'Guardar'}
        </button>
        <button style={S.btn(false)} onClick={restaurar}>Restaurar</button>
      </div>
      {msg && <div style={S.msg(msg.ok)}>{msg.t}</div>}
    </>
  );
}

function PanelSemaforo({ p, escenario, guardado, onGuardado }) {
  const idPrograma = Object.keys(p.programas || {})[0];
  const originales = idPrograma ? p.programas[idPrograma] : [];
  const fasesGuardadas = Array.isArray(guardado) ? guardado : guardado?.fases;

  const [duraciones, setDuraciones] = useState(
    originales.map((f, i) => fasesGuardadas?.find((g) => g.indice === i)?.duracion ?? f.duracion)
  );
  const [msg, setMsg] = useState(null);
  const [guardando, setGuardando] = useState(false);

  if (!idPrograma) {
    return <div style={S.info}>Este semáforo no tiene programa de fases; no hay nada que editar.</div>;
  }

  async function guardar() {
    const fases = originales.map((f, i) => ({
      indice: i,
      duracion: parseInt(duraciones[i], 10),
      estado: f.estado,
    }));
    if (fases.some((f) => !(f.duracion >= 1 && f.duracion <= 300))) {
      return setMsg({ ok: false, t: 'Cada duración debe ser entre 1 y 300 segundos' });
    }

    setGuardando(true);
    try {
      await modificarSemaforo(escenario.id, p.tls_id, fases);
      await onGuardado();
      setMsg({ ok: true, t: 'Guardado. Este semáforo correrá a tiempo fijo en la próxima simulación.' });
    } catch (err) {
      setMsg({ ok: false, t: `No se pudo guardar: ${err.message}` });
    } finally {
      setGuardando(false);
    }
  }

  function restaurar() {
    setDuraciones(originales.map((f) => f.duracion));
    setMsg({ ok: true, t: 'Valores originales (sin guardar todavía)' });
  }

  return (
    <>
      <div style={S.info}>
        Tipo: {p.tipo_control} · Programa: {idPrograma}<br />
        Entrantes: {p.calles_entrantes?.length ?? 0} · Salientes: {p.calles_salientes?.length ?? 0}
      </div>

      {originales.map((f, i) => (
        <div key={i} style={S.fase}>
          <label style={{ ...S.label, marginTop: 0 }}>Fase {i} · duración (s)</label>
          <input style={S.input} type="number" min="1" max="300" value={duraciones[i]}
                 onChange={(e) => setDuraciones((prev) => prev.map((d, j) => (j === i ? e.target.value : d)))} />
          <div style={S.info}>Original: {f.duracion} s · estado: {f.estado}</div>
        </div>
      ))}

      <div style={S.aviso}>
        Al guardar, este semáforo pasa a tiempo fijo con estas duraciones. Los que no edites siguen automáticos.
      </div>

      <div style={S.fila}>
        <button style={S.btn(true, guardando)} disabled={guardando} onClick={guardar}>
          {guardando ? 'Guardando...' : 'Guardar'}
        </button>
        <button style={S.btn(false)} onClick={restaurar}>Restaurar</button>
      </div>
      {msg && <div style={S.msg(msg.ok)}>{msg.t}</div>}
    </>
  );
}

export default function EdicionPanel({ seleccion, onClose }) {
  const { escenarioActivo, modsEdges, modsSemaforos, recargarEscenarios } = useProyecto();
  const { tipo, id, props: p } = seleccion;
  const esCalle = tipo === 'calle';

  return (
    <div style={S.box}>
      <div style={S.head}>
        <div>
          <div style={S.nombre}>{esCalle ? p.nombre_calle || 'Sin nombre' : 'Semáforo'}</div>
          <div style={S.id}>
            ID: {id}{' '}
            <button style={{ ...S.x, fontSize: 11 }} title="Copiar ID"
                    onClick={() => navigator.clipboard?.writeText(String(id))}>
              copiar
            </button>
          </div>
          <div style={S.id}>
            Escenario: {escenarioActivo ? escenarioActivo.nombre : '— ninguno —'}
          </div>
        </div>
        <button style={S.x} onClick={onClose} aria-label="Cerrar">✕</button>
      </div>

      {!escenarioActivo ? (
        <div style={S.msg(false)}>
          Este proyecto no tiene escenarios. Crea uno para poder guardar cambios.
        </div>
      ) : esCalle ? (
        <PanelCalle
          key={`${id}-${escenarioActivo.id}`}
          p={p}
          escenario={escenarioActivo}
          guardado={modsEdges[id]}
          onGuardado={recargarEscenarios}
        />
      ) : (
        <PanelSemaforo
          key={`${id}-${escenarioActivo.id}`}
          p={p}
          escenario={escenarioActivo}
          guardado={modsSemaforos[id]}
          onGuardado={recargarEscenarios}
        />
      )}
    </div>
  );
}