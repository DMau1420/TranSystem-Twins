import React, { useState, useEffect } from 'react';
import { useMapData } from '../context/MapDataContext';
import { sysCore } from '../styles/sysCore';
import SysPanelChrome from './common/SysPanelChrome';
import { createPoints } from '../api/mapApi';
import { StepperInput } from './common/StepperInput';

const panelStyle = {
  position: 'absolute',
  top: 0,
  right: 0,
  height: '100vh',
  width: 360,
  background: sysCore.color.panel,
  backdropFilter: 'blur(6px)',
  borderLeft: `1px solid ${sysCore.color.borderStrong}`,
  boxShadow: '-8px 0 30px rgba(45, 227, 255, 0.08)',
  zIndex: 1002,
  display: 'flex',
  flexDirection: 'column',
  fontFamily: sysCore.font.mono,
  fontSize: 12.5,
  color: sysCore.color.ink,
  overflow: 'hidden',
};

const toggleButtonStyle = {
  position: 'absolute',
  top: 90,
  right: 16,
  zIndex: 1001,
  background: 'rgba(10, 12, 16, 0.9)',
  color: sysCore.color.cyan,
  border: `1px solid ${sysCore.color.borderStrong}`,
  borderRadius: 4,
  padding: '8px 14px',
  cursor: 'pointer',
  fontFamily: sysCore.font.mono,
  fontSize: 11,
  fontWeight: 500,
  letterSpacing: '0.05em',
  textTransform: 'uppercase',
  boxShadow: '0 0 12px rgba(45, 227, 255, 0.15)',
  display: 'flex',
  alignItems: 'center',
  gap: 8,
};

const kbdHintStyle = {
  fontFamily: sysCore.font.mono,
  fontSize: 10,
  color: sysCore.color.cyan,
  border: `1px solid ${sysCore.color.border}`,
  borderRadius: 3,
  padding: '1px 5px',
  lineHeight: 1.4,
  opacity: 0.8,
};

const KEY_SHORTCUT = 'p';

const headerStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '16px 18px',
  borderBottom: `1px solid ${sysCore.color.border}`,
  fontWeight: 600,
  fontSize: 11,
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  color: sysCore.color.cyan,
};

const closeButtonStyle = {
  background: 'none',
  border: 'none',
  color: sysCore.color.inkMuted,
  cursor: 'pointer',
  fontSize: 15,
  lineHeight: 1,
  padding: 4,
  fontFamily: sysCore.font.mono,
};

const tabsBarStyle = {
  display: 'flex',
  borderBottom: `1px solid ${sysCore.color.border}`,
  position: 'sticky',
  top: 0,
  background: sysCore.color.panel,
};

const tabButtonStyle = (active) => ({
  flex: 1,
  padding: '12px 0',
  border: 'none',
  background: 'transparent',
  color: active ? sysCore.color.cyan : sysCore.color.inkMuted,
  fontWeight: active ? 600 : 500,
  borderBottom: active ? `2px solid ${sysCore.color.cyan}` : '2px solid transparent',
  cursor: 'pointer',
  fontFamily: sysCore.font.mono,
  fontSize: 11,
  letterSpacing: '0.05em',
  textTransform: 'uppercase',
});

const scrollAreaStyle = { overflowY: 'auto', flex: 1 };

const sectionTitleStyle = {
  padding: '10px 18px',
  background: 'rgba(45, 227, 255, 0.04)',
  fontWeight: 600,
  fontSize: 10.5,
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  color: sysCore.color.inkMuted,
};

const itemRow = () => ({
  display: 'flex',
  borderBottom: `1px solid ${sysCore.color.border}`,
});

const itemAccentBar = (color) => ({
  width: 3,
  background: color,
  boxShadow: `0 0 6px ${color}`,
  flexShrink: 0,
});

const itemBodyStyle = { padding: '10px 16px', flex: 1 };

const removeButtonStyle = {
  float: 'right',
  background: 'none',
  border: 'none',
  color: sysCore.color.magenta,
  cursor: 'pointer',
  fontSize: 13,
  lineHeight: 1,
  fontFamily: sysCore.font.mono,
};

const coordTextStyle = {
  color: sysCore.color.inkMuted,
  fontFamily: sysCore.font.mono,
  fontSize: 10.5,
};

const emptyStateStyle = {
  padding: '18px 16px',
  color: sysCore.color.inkMuted,
  fontSize: 11.5,
  fontStyle: 'italic',
};

const copyButtonStyle = {
  margin: 14,
  padding: '8px 14px',
  background: 'rgba(45, 227, 255, 0.1)',
  color: sysCore.color.cyan,
  border: `1px solid ${sysCore.color.borderStrong}`,
  borderRadius: 4,
  cursor: 'pointer',
  fontFamily: sysCore.font.mono,
  fontSize: 11,
  fontWeight: 500,
  letterSpacing: '0.05em',
  textTransform: 'uppercase',
};

const jsonBoxStyle = {
  margin: 0,
  padding: '0 16px 16px',
  fontFamily: sysCore.font.mono,
  fontSize: 10.5,
  color: sysCore.color.ink,
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
};

const saveBarStyle = {
  padding: 14,
  borderBottom: `1px solid ${sysCore.color.border}`,
};

const saveButtonStyle = (disabled) => ({
  width: '100%',
  padding: '10px 0',
  background: disabled ? 'rgba(255,255,255,0.05)' : 'rgba(45, 227, 255, 0.12)',
  color: disabled ? sysCore.color.inkMuted : sysCore.color.cyan,
  border: `1px solid ${disabled ? sysCore.color.border : sysCore.color.borderStrong}`,
  borderRadius: 4,
  cursor: disabled ? 'default' : 'pointer',
  fontFamily: sysCore.font.mono,
  fontSize: 11.5,
  fontWeight: 600,
  letterSpacing: '0.05em',
  textTransform: 'uppercase',
});

const saveStatusStyle = (kind) => ({
  marginTop: 8,
  fontSize: 11,
  color: kind === 'error' ? sysCore.color.magenta : sysCore.color.cyan,
  background: kind === 'error' ? 'rgba(255, 45, 111, 0.08)' : 'rgba(45, 227, 255, 0.08)',
  border: `1px solid ${kind === 'error' ? 'rgba(255, 45, 111, 0.3)' : 'rgba(45, 227, 255, 0.3)'}`,
  borderRadius: 4,
  padding: '6px 10px',
  fontFamily: sysCore.font.mono,
});

// Convierte los puntos del contexto a la forma que espera PointsPayload.
// ⚠️ Ajustar campos cuando se confirme el schema real del backend.
function buildPointsPayload(points) {
  return {
    points: points.map((p) => ({
      id: p.id,
      lat: p.lat,
      lng: p.lng,
      geoJson: p.geoJson,
      street: p.street ?? null,
      displayName: p.displayName ?? null,
    })),
  };
}

const ListView = ({ points, routes, zones, removeFeature, updateZone }) => (
  <>
    <div style={sectionTitleStyle}>// PUNTOS · {points.length}</div>
    {points.length === 0 && <div style={emptyStateStyle}>Ningún punto marcado todavía.</div>}
    {points.map((p) => (
      <div key={p.id} style={itemRow()}>
        <div style={itemAccentBar(sysCore.color.magenta)} />
        <div style={itemBodyStyle}>
          <button style={removeButtonStyle} onClick={() => removeFeature(p.id)}>✕</button>
          <strong>{p.street ?? 'Calle desconocida'}</strong>
          <br />
          <span style={coordTextStyle}>{p.lat.toFixed(5)}, {p.lng.toFixed(5)}</span>
        </div>
      </div>
    ))}

    <div style={sectionTitleStyle}>// RUTAS · {routes.length}</div>
    {routes.length === 0 && <div style={emptyStateStyle}>Ninguna ruta trazada todavía.</div>}
    {routes.map((r) => (
      <div key={r.id} style={itemRow()}>
        <div style={itemAccentBar(sysCore.color.cyan)} />
        <div style={itemBodyStyle}>
          <button style={removeButtonStyle} onClick={() => removeFeature(r.id)}>✕</button>
          <strong>{(r.distanceMeters / 1000).toFixed(2)} km</strong>
          <br />
          <span style={coordTextStyle}>{r.coordinates.length} puntos en el trazo</span>
        </div>
      </div>
    ))}

    <div style={sectionTitleStyle}>// ZONAS · {zones.length}</div>
    {zones.length === 0 && <div style={emptyStateStyle}>Ninguna zona marcada todavía.</div>}
    {zones.map((z) => (
      <div key={z.id} style={itemRow()}>
        <div style={itemAccentBar(sysCore.color.amber)} />
        <div style={itemBodyStyle}>
          <button style={removeButtonStyle} onClick={() => removeFeature(z.id)}>✕</button>
          <span style={coordTextStyle}>Zona #{z.id.slice(0, 8)}</span>
          <div style={{ marginTop: 8 }}>
            <StepperInput
              label="Vehículos por hora"
              value={z.vehiculos_por_hora ?? 0}
              onChange={(valOrFn) => {
                const newVal = typeof valOrFn === 'function'
                  ? valOrFn(z.vehiculos_por_hora ?? 0)
                  : valOrFn;
                updateZone(z.id, 'vehiculos_por_hora', newVal);
              }}
              min={0}
              max={99999}
            />
          </div>
        </div>
      </div>
    ))}
  </>
);

const JsonView = ({ points, routes, zones }) => {
  const [copied, setCopied] = useState(false);
  const json = JSON.stringify({ points, routes, zones }, null, 2);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(json);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (err) {
      console.error('No se pudo copiar:', err);
    }
  };

  return (
    <>
      <button style={copyButtonStyle} onClick={handleCopy}>
        {copied ? '✓ COPIADO' : 'COPIAR_JSON'}
      </button>
      <pre style={jsonBoxStyle}>{json}</pre>
    </>
  );
};

export const MapDataPanel = () => {
  const [open, setOpen] = useState(true);
  const [tab, setTab] = useState('list');
  const [saveState, setSaveState] = useState('idle'); // idle | saving | success | error
  const [saveMessage, setSaveMessage] = useState('');
  const { points, routes, zones, removeFeature, updateZone } = useMapData();
  const total = points.length + routes.length + zones.length;

  useEffect(() => {
    const handleKeyDown = (e) => {
      const tag = document.activeElement?.tagName?.toLowerCase();
      if (tag === 'input' || tag === 'textarea') return;

      if (e.key.toLowerCase() === KEY_SHORTCUT) {
        setOpen((prev) => !prev);
      }
      if (e.key === 'Escape') {
        setOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleSave = async () => {
    if (points.length === 0) return;

    setSaveState('saving');
    setSaveMessage('');

    try {
      const payload = buildPointsPayload(points);
      await createPoints(payload);
      setSaveState('success');
      setSaveMessage(`Se guardaron ${points.length} punto(s) en el backend.`);
    } catch (err) {
      console.error('Error guardando puntos:', err);
      setSaveState('error');
      setSaveMessage(
        `No se pudo guardar: ${err.message}. Revisá que el backend esté corriendo y que el formato coincida.`
      );
    }
  };

  return (
    <>
      {!open && (
        <button style={toggleButtonStyle} onClick={() => setOpen(true)}>
          {`// PUNTOS (${total})`} <span style={kbdHintStyle}>P</span>
        </button>
      )}

      {open && (
        <div style={panelStyle}>
          <SysPanelChrome />
          <div style={headerStyle}>
            // PUNTOS_DEL_MAPA //
            <button style={closeButtonStyle} onClick={() => setOpen(false)} title="Cerrar (P)">
              ✕
            </button>
          </div>

          <div style={saveBarStyle}>
            <button
              style={saveButtonStyle(points.length === 0 || saveState === 'saving')}
              onClick={handleSave}
              disabled={points.length === 0 || saveState === 'saving'}
            >
              {saveState === 'saving' ? 'GUARDANDO…' : `GUARDAR ${points.length} PUNTO(S)`}
            </button>
            {saveMessage && (
              <div style={saveStatusStyle(saveState === 'error' ? 'error' : 'ok')}>{saveMessage}</div>
            )}
          </div>

          <div style={tabsBarStyle}>
            <button style={tabButtonStyle(tab === 'list')} onClick={() => setTab('list')}>Lista</button>
            <button style={tabButtonStyle(tab === 'json')} onClick={() => setTab('json')}>JSON</button>
          </div>
          <div style={scrollAreaStyle}>
            {tab === 'list' ? (
              <ListView points={points} routes={routes} zones={zones} removeFeature={removeFeature} updateZone={updateZone} />
            ) : (
              <JsonView points={points} routes={routes} zones={zones} />
            )}
          </div>
        </div>
      )}
    </>
  );
};

export default MapDataPanel;