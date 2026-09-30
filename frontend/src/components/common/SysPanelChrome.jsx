import React from 'react';

let injected = false;

function injectKeyframesOnce() {
  if (injected || typeof document === 'undefined') return;
  injected = true;
  const style = document.createElement('style');
  style.textContent = `
    @keyframes sys-scanline {
      0% { transform: translateY(-120%); }
      100% { transform: translateY(220%); }
    }
    @keyframes sys-pulse {
      0%, 100% { opacity: 0.3; transform: scale(0.85); }
      50% { opacity: 1; transform: scale(1); }
    }
  `;
  document.head.appendChild(style);
}

const cornerBase = {
  position: 'absolute',
  width: 10,
  height: 10,
  borderColor: 'var(--sys-cyan, #2de3ff)',
  opacity: 0.6,
  pointerEvents: 'none',
};

const corners = {
  topLeft: { ...cornerBase, top: 0, left: 0, borderTop: '1px solid', borderLeft: '1px solid' },
  bottomLeft: { ...cornerBase, bottom: 0, left: 0, borderBottom: '1px solid', borderLeft: '1px solid' },
};

const scanlineStyle = {
  position: 'absolute',
  top: 0,
  left: 0,
  right: 0,
  height: '35%',
  background: 'linear-gradient(180deg, transparent, rgba(45,227,255,0.05), transparent)',
  animation: 'sys-scanline 7s linear infinite',
  pointerEvents: 'none',
};

/**
 * Decoración HUD reutilizable: esquinas reticulares + scanline sutil.
 * Se coloca como primer hijo dentro de un contenedor con position: relative.
 */
export default function SysPanelChrome() {
  injectKeyframesOnce();
  return (
    <>
      <span style={corners.topLeft} />
      <span style={corners.bottomLeft} />
      <div style={scanlineStyle} />
    </>
  );
}