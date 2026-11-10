import { useEffect, useState } from 'react';
import { useSimulacionContext } from '../../context/SimulacionContext';
import { sysCore } from '../../styles/sysCore';

const S = {
  wrap: {
    position: 'absolute',
    bottom: 24,
    left: '50%',
    transform: 'translateX(-50%)',
    zIndex: 1002,
    width: '90%',
    maxWidth: 620,
    background: 'rgba(10, 12, 16, 0.94)',
    backdropFilter: 'blur(8px)',
    border: `1px solid ${sysCore.color.cyan}`,
    borderRadius: 6,
    padding: '12px 18px',
    boxShadow: '0 0 24px rgba(45, 227, 255, 0.25), inset 0 0 12px rgba(45, 227, 255, 0.08)',
    fontFamily: sysCore.font.mono,
    color: sysCore.color.ink,
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
    animation: 'tstFadeIn 0.2s ease-out',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    fontSize: 11,
    letterSpacing: '0.06em',
    textTransform: 'uppercase',
  },
  title: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    color: sysCore.color.cyan,
    fontWeight: 600,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: '50%',
    background: sysCore.color.cyan,
    boxShadow: `0 0 8px ${sysCore.color.cyan}`,
    display: 'inline-block',
  },
  pct: {
    color: sysCore.color.cyan,
    fontWeight: 700,
    fontSize: 12,
  },
  track: {
    width: '100%',
    height: 6,
    background: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 3,
    overflow: 'hidden',
    position: 'relative',
  },
  fill: (pct) => ({
    height: '100%',
    width: `${pct}%`,
    background: `linear-gradient(90deg, ${sysCore.color.cyan}, #5bf5ff)`,
    boxShadow: `0 0 10px ${sysCore.color.cyan}`,
    transition: 'width 0.35s ease',
  }),
  bottomRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
    marginTop: 2,
  },
  msg: {
    fontSize: 11,
    color: '#d4f4ff',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    flex: 1,
  },
  cancelBtn: {
    background: 'rgba(255, 45, 111, 0.12)',
    border: `1px solid ${sysCore.color.magenta}`,
    color: sysCore.color.magenta,
    borderRadius: 3,
    padding: '3px 10px',
    cursor: 'pointer',
    fontSize: 10,
    fontWeight: 600,
    letterSpacing: '0.06em',
    fontFamily: sysCore.font.mono,
    textTransform: 'uppercase',
    flexShrink: 0,
  },
};

export default function BottomProgressBar() {
  const { running, progreso, mensaje, estado, error, cancelar } = useSimulacionContext();
  const [showDone, setShowDone] = useState(false);

  useEffect(() => {
    if (estado === 'completado') {
      setShowDone(true);
      const timer = setTimeout(() => setShowDone(false), 3500);
      return () => clearTimeout(timer);
    } else {
      setShowDone(false);
    }
  }, [estado]);

  if (!running && !showDone && estado !== 'error') return null;

  const isError = estado === 'error';
  const displayMsg = isError
    ? error || 'Error en la simulación.'
    : showDone
    ? 'Simulación completada con éxito (100%)'
    : mensaje || 'Ejecutando simulación de tráfico SUMO...';

  return (
    <div style={{ ...S.wrap, borderColor: isError ? sysCore.color.magenta : sysCore.color.cyan }}>
      <div style={S.header}>
        <div style={{ ...S.title, color: isError ? sysCore.color.magenta : sysCore.color.cyan }}>
          <span
            style={{
              ...S.dot,
              background: isError ? sysCore.color.magenta : sysCore.color.cyan,
              boxShadow: `0 0 8px ${isError ? sysCore.color.magenta : sysCore.color.cyan}`,
            }}
          />
          {isError ? '// ERROR EN SIMULACIÓN' : '// SUMO SIMULATOR // COMUNICACIÓN EN VIVO'}
        </div>
        <div style={{ ...S.pct, color: isError ? sysCore.color.magenta : sysCore.color.cyan }}>
          {isError ? 'FALLO' : `${progreso}%`}
        </div>
      </div>

      <div style={S.track}>
        <div
          style={{
            ...S.fill(isError ? 100 : progreso),
            background: isError ? sysCore.color.magenta : undefined,
            boxShadow: isError ? `0 0 10px ${sysCore.color.magenta}` : undefined,
          }}
        />
      </div>

      <div style={S.bottomRow}>
        <div
          style={{
            ...S.msg,
            color: isError ? sysCore.color.magenta : '#d4f4ff',
          }}
          title={displayMsg}
        >
          {'> '} {displayMsg}
        </div>
        {running && (
          <button style={S.cancelBtn} onClick={cancelar} title="Detener simulación">
            Cancelar
          </button>
        )}
        {isError && (
          <button style={S.cancelBtn} onClick={cancelar} title="Cerrar aviso">
            Cerrar
          </button>
        )}
      </div>
    </div>
  );
}
