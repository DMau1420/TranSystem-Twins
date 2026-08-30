import React, { useState } from 'react';
import { useMapData } from '../context/MapDataContext';
import { tokens } from '../styles/tokens';
import { createPoints } from '../api/mapApi';
import { StepperInput } from './common/StepperInput';

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

const itemRow = () => ({
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

const saveBarStyle = {
  padding: 12,
  borderBottom: `1px solid ${tokens.color.border}`,
};

const saveButtonStyle = (disabled) => ({
  width: '100%',
  padding: '10px 0',
  background: disabled ? tokens.color.border : tokens.color.accent,
  color: tokens.color.surface,
  border: 'none',
  borderRadius: tokens.radius.sm,
  cursor: disabled ? 'default' : 'pointer',
  fontFamily: tokens.font.ui,
  fontSize: 13,
  fontWeight: 600,
});

const saveStatusStyle = (kind) => ({
  marginTop: 8,
  fontSize: 11.5,
  color: kind === 'error' ? tokens.color.danger : tokens.color.accentDark,
  background: kind === 'error' ? tokens.color.dangerSoft : tokens.color.accentSoft,
  borderRadius: tokens.radius.sm,
  padding: '6px 10px',
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
        {copied ? '✓ Copiado' : 'Copiar JSON'}
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
      <button style={toggleButtonStyle} onClick={() => setOpen((prev) => !prev)}>
        {open ? 'Ocultar panel' : `Ver puntos (${total})`}
      </button>

      {open && (
        <div style={panelStyle}>
          <div style={saveBarStyle}>
            <button
              style={saveButtonStyle(points.length === 0 || saveState === 'saving')}
              onClick={handleSave}
              disabled={points.length === 0 || saveState === 'saving'}
            >
              {saveState === 'saving' ? 'Guardando…' : `Guardar ${points.length} punto(s) en backend`}
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