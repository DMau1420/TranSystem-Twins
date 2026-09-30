// Tokens SYS_CORE compartidos: mismo lenguaje visual que Auth.css (login).
// Expuestos como CSS custom properties con fallback, para poder
// sobreescribirlos centralmente después si hace falta.
export const sysCore = {
  color: {
    bg: 'var(--sys-bg, #0a0c10)',
    panel: 'var(--sys-panel, rgba(10, 12, 16, 0.97))',
    border: 'var(--sys-border, rgba(45, 227, 255, 0.22))',
    borderStrong: 'var(--sys-border-strong, rgba(45, 227, 255, 0.6))',
    cyan: 'var(--sys-cyan, #2de3ff)',
    magenta: 'var(--sys-magenta, #ff2d6f)',
    amber: 'var(--sys-amber, #ffb020)',
    ink: 'var(--sys-ink, #e8fbff)',
    inkMuted: 'var(--sys-ink-muted, rgba(232, 251, 255, 0.55))',
  },
  font: {
    mono: "'JetBrains Mono', 'Courier New', monospace",
  },
};

export default sysCore;
