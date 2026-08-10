import React, { useState } from 'react';
import { useMapData } from '../context/MapDataContext';
import { tokens } from '../styles/tokens';

const panelStyle = {
  position: 'absolute',
  top: 0,
  right: 0,
  height: '100vh',
  width: 340,
  background: tokens.color.surface,
  boxShadow: tokens.shadow.card,
  zIndex: 1000,
  display: 'flex',
  flexDirection: 'column',
  fontFamily: tokens.font.ui,
  fontSize: 13,
  color: tokens.color.ink,
};

const toggleButtonStyle = {
  position: 'absolute',
  top: 16,
  right: 16,
  zIndex: 1001,
  background: tokens.color.ink,
  color: tokens.color.surface,
  border: 'none',
  borderRadius: tokens.radius.pill,
  padding: '9px 16px',
  cursor: 'pointer',
  fontFamily: tokens.font.ui,
  fontSize: 13,
  fontWeight: 500,
  boxShadow: tokens.shadow.floating,
};

const tabsBarStyle = {
  display: 'flex',
  borderBottom: `1px solid ${tokens.color.border}`,
  position: 'sticky',
  top: 0,
  background: tokens.color.surface,
};

const tabButtonStyle = (active) => ({
  flex: 1,
  padding: '12px 0',
  border: 'none',
  background: 'transparent',
  color: active ? tokens.color.accent : tokens.color.inkMuted,
  fontWeight: active ? 600 : 500,
  borderBottom: active ? `2px solid ${tokens.color.accent}` : '2px solid transparent',
  cursor: 'pointer',
  fontFamily: tokens.font.ui,
  fontSize: 13,
});

const scrollAreaStyle = { overflowY: 'auto', flex: 1 };

const sectionTitleStyle = {
  padding: '10px 16px',
  background: tokens.color.surfaceMuted,
  fontWeight: 600,
  fontSize: 11,
  letterSpacing: '0.04em',
  textTransform: 'uppercase',
  color: tokens.color.inkMuted,
};

const itemRow = (accentColor) => ({
  display: 'flex',
  borderBottom: `1px solid ${tokens.color.border}`,
});

const itemAccentBar = (color) => ({
  width: 4,
  background: color,
  flexShrink: 0,
});

const itemBodyStyle = { padding: '10px 14px', flex: 1 };

const removeButtonStyle = {
  float: 'right',
  background: 'none',
  border: 'none',
  color: tokens.color.danger,
  cursor: 'pointer',
  fontSize: 14,
  lineHeight: 1,
};

const coordTextStyle = {
  color: tokens.color.inkMuted,
  fontFamily: tokens.font.mono,
  fontSize: 11,
};

const emptyStateStyle = {
  padding: '18px 16px',
  color: tokens.color.inkMuted,
  fontSize: 12.5,
};

const copyButtonStyle = {
  margin: 12,
  padding: '8px 14px',
  background: tokens.color.accent,
  color: tokens.color.surface,
  border: 'none',
  borderRadius: tokens.radius.pill,
  cursor: 'pointer',
  fontFamily: tokens.font.ui,
  fontSize: 12,
  fontWeight: 500,
};

const jsonBoxStyle = {
  margin: 0,
  padding: '0 16px 16px',
  fontFamily: tokens.font.mono,
  fontSize: 11,
  color: tokens.color.ink,
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
};

const ListView = ({ points, routes, zones, removeFeature }) => (
  <>
    <div style={sectionTitleStyle}>Puntos · {points.length}</div>
    {points.length === 0 && <div style={emptyStateStyle}>Ningún punto marcado todavía.</div>}
    {points.map((p) => (
      <div key={p.id} style={itemRow()}>
        <div style={itemAccentBar(tokens.color.amber)} />
        <div style={itemBodyStyle}>
          <button style={removeButtonStyle} onClick={() => removeFeature(p.id)}>✕</button>
          <strong>{p.street ?? 'Calle desconocida'}</strong>
          <br />
          <span style={coordTextStyle}>{p.lat.toFixed(5)}, {p.lng.toFixed(5)}</span>
        </div>
      </div>
    ))}

    <div style={sectionTitleStyle}>Rutas · {routes.length}</div>
    {routes.length === 0 && <div style={emptyStateStyle}>Ninguna ruta trazada todavía.</div>}
    {routes.map((r) => (
      <div key={r.id} style={itemRow()}>
        <div style={itemAccentBar(tokens.color.accent)} />
        <div style={itemBodyStyle}>
          <button style={removeButtonStyle} onClick={() => removeFeature(r.id)}>✕</button>
          <strong>{(r.distanceMeters / 1000).toFixed(2)} km</strong>
          <br />
          <span style={coordTextStyle}>{r.coordinates.length} puntos en el trazo</span>
        </div>
      </div>
    ))}

    <div style={sectionTitleStyle}>Zonas · {zones.length}</div>
    {zones.length === 0 && <div style={emptyStateStyle}>Ninguna zona marcada todavía.</div>}
    {zones.map((z) => (
      <div key={z.id} style={itemRow()}>
        <div style={itemAccentBar(tokens.color.slate)} />
        <div style={itemBodyStyle}>
          <button style={removeButtonStyle} onClick={() => removeFeature(z.id)}>✕</button>
          <span style={coordTextStyle}>Zona #{z.id.slice(0, 8)}</span>
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
        {copied ? '✓ Copiado' : 'Copiar JSON'}
      </button>
      <pre style={jsonBoxStyle}>{json}</pre>
    </>
  );
};

export const MapDataPanel = () => {
  const [open, setOpen] = useState(true);
  const [tab, setTab] = useState('list');
  const { points, routes, zones, removeFeature } = useMapData();
  const total = points.length + routes.length + zones.length;

  return (
    <>
      <button style={toggleButtonStyle} onClick={() => setOpen((prev) => !prev)}>
        {open ? 'Ocultar panel' : `Ver puntos (${total})`}
      </button>

      {open && (
        <div style={panelStyle}>
          <div style={tabsBarStyle}>
            <button style={tabButtonStyle(tab === 'list')} onClick={() => setTab('list')}>Lista</button>
            <button style={tabButtonStyle(tab === 'json')} onClick={() => setTab('json')}>JSON</button>
          </div>
          <div style={scrollAreaStyle}>
            {tab === 'list' ? (
              <ListView points={points} routes={routes} zones={zones} removeFeature={removeFeature} />
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