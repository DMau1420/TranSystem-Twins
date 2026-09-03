import React, { useState, useEffect } from 'react';
import { sysCore } from '../../styles/sysCore';
import SysPanelChrome from '../common/SysPanelChrome';

const toggleButtonStyle = {
  position: 'absolute',
  top: 138,
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

const panelStyle = (open) => ({
  position: 'absolute',
  top: 0,
  right: 0,
  height: '100vh',
  width: 280,
  background: sysCore.color.panel,
  backdropFilter: 'blur(6px)',
  borderLeft: `1px solid ${sysCore.color.borderStrong}`,
  boxShadow: open ? '-8px 0 30px rgba(45, 227, 255, 0.08)' : 'none',
  zIndex: 1002,
  display: 'flex',
  flexDirection: 'column',
  fontFamily: sysCore.font.mono,
  fontSize: 12.5,
  color: sysCore.color.ink,
  transform: open ? 'translateX(0)' : 'translateX(100%)',
  transition: 'transform 0.25s ease',
  pointerEvents: open ? 'auto' : 'none',
  overflow: 'hidden',
});

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

const layerRowStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '14px 18px',
  borderBottom: `1px solid ${sysCore.color.border}`,
};

const layerLabelWrapStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  fontSize: 12,
  letterSpacing: '0.02em',
};

const loadingDotStyle = {
  width: 6,
  height: 6,
  borderRadius: '50%',
  background: sysCore.color.cyan,
  boxShadow: `0 0 6px ${sysCore.color.cyan}`,
  animation: 'sys-pulse 1s ease-in-out infinite',
};

const switchStyle = (active) => ({
  width: 38,
  height: 20,
  borderRadius: 10,
  background: active ? 'rgba(45, 227, 255, 0.15)' : 'rgba(255, 255, 255, 0.06)',
  border: `1px solid ${active ? sysCore.color.cyan : sysCore.color.border}`,
  position: 'relative',
  cursor: 'pointer',
  transition: 'background 0.15s ease, border-color 0.15s ease',
  padding: 0,
});

const switchKnobStyle = (active) => ({
  position: 'absolute',
  top: 1,
  left: active ? 19 : 1,
  width: 16,
  height: 16,
  borderRadius: '50%',
  background: active ? sysCore.color.cyan : sysCore.color.inkMuted,
  boxShadow: active ? `0 0 6px ${sysCore.color.cyan}` : 'none',
  transition: 'left 0.15s ease, background 0.15s ease',
});

// --- Selector de estilo de mapa (segmented control Claro/Oscuro) ---

const segmentedWrapStyle = {
  display: 'flex',
  border: `1px solid ${sysCore.color.border}`,
  borderRadius: 4,
  overflow: 'hidden',
};

const segmentButtonStyle = (active) => ({
  padding: '5px 12px',
  border: 'none',
  background: active ? 'rgba(45, 227, 255, 0.15)' : 'transparent',
  color: active ? sysCore.color.cyan : sysCore.color.inkMuted,
  fontFamily: sysCore.font.mono,
  fontSize: 10.5,
  letterSpacing: '0.04em',
  textTransform: 'uppercase',
  cursor: 'pointer',
  transition: 'background 0.15s ease, color 0.15s ease',
});

const KEY_SHORTCUT = 'l';

/**
 * Panel deslizable de capas del mapa: Red vial OSM y estilo de tiles
 * (Claro/Oscuro). Estilo SYS_CORE, consistente con Auth.css.
 */
export const LayersPanel = ({
  showRoadNetwork,
  onToggleRoadNetwork,
  roadNetworkLoading,
  mapStyle,
  onChangeMapStyle,
}) => {
  const [open, setOpen] = useState(false);

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

  return (
    <>
      {!open && (
        <button style={toggleButtonStyle} onClick={() => setOpen(true)}>
          // CAPAS <span style={kbdHintStyle}>L</span>
        </button>
      )}

      <div style={panelStyle(open)}>
        <SysPanelChrome />
        <div style={headerStyle}>
          // CAPAS_DEL_MAPA //
          <button style={closeButtonStyle} onClick={() => setOpen(false)} title="Cerrar (Esc)">
            ✕
          </button>
        </div>

        <div style={layerRowStyle}>
          <div style={layerLabelWrapStyle}>
            <span>RED_VIAL // OSM</span>
            {roadNetworkLoading && <span style={loadingDotStyle} title="Cargando…" />}
          </div>
          <button
            style={switchStyle(showRoadNetwork)}
            onClick={onToggleRoadNetwork}
            aria-pressed={showRoadNetwork}
          >
            <span style={switchKnobStyle(showRoadNetwork)} />
          </button>
        </div>
      </div>
    </>
  );
};

export default LayersPanel;