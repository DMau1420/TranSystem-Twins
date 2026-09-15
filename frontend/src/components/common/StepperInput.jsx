import React, { useState, useRef, useCallback, useEffect } from 'react';
import { tokens } from '../../styles/tokens';

/**
 * StepperInput — numeric input with −/+ buttons.
 *
 * Features:
 *  • Click         → increment / decrement by current step
 *  • Press & hold  → auto-repeat that accelerates over time
 *  • Step toggle   → switch between ×1 and ×5
 *
 * Props:
 *  - value       : number
 *  - onChange     : (newValue: number) => void
 *  - min         : number  (default 0)
 *  - max         : number  (default 99999)
 *  - label       : string  (optional, rendered above the input)
 */

// ── Hold-to-repeat config ────────────────────────
const INITIAL_DELAY = 400; // ms before repeat starts
const MIN_INTERVAL = 50;   // fastest repeat speed
const ACCEL_FACTOR = 0.82; // multiplier each tick (smaller = faster accel)

const STEPS = [1, 2, 3, 5, 10, 25, 50, 100];

export const StepperInput = ({ value, onChange, min = 0, max = 99999, label }) => {
  const [stepIdx, setStepIdx] = useState(0);
  const step = STEPS[stepIdx];
  const intervalRef = useRef(null);
  const timeoutRef = useRef(null);
  const currentInterval = useRef(INITIAL_DELAY);

  // ── Clamp helper ──────────────────────────────
  const clamp = useCallback((v) => Math.max(min, Math.min(max, v)), [min, max]);

  // ── Core change ───────────────────────────────
  const applyDelta = useCallback(
    (delta) => {
      onChange((prev) => {
        const numeric = typeof prev === 'number' ? prev : 0;
        return clamp(numeric + delta);
      });
    },
    [onChange, clamp],
  );

  // ── Repeat logic ──────────────────────────────
  const stopRepeat = useCallback(() => {
    clearTimeout(timeoutRef.current);
    clearInterval(intervalRef.current);
    timeoutRef.current = null;
    intervalRef.current = null;
    currentInterval.current = INITIAL_DELAY;
  }, []);

  const startRepeat = useCallback(
    (delta) => {
      // First immediate tick already happened via onMouseDown
      currentInterval.current = INITIAL_DELAY;

      const tick = () => {
        applyDelta(delta);
        currentInterval.current = Math.max(MIN_INTERVAL, currentInterval.current * ACCEL_FACTOR);
        timeoutRef.current = setTimeout(tick, currentInterval.current);
      };

      // Wait INITIAL_DELAY before the first repeat
      timeoutRef.current = setTimeout(tick, INITIAL_DELAY);
    },
    [applyDelta],
  );

  // Clean up on unmount
  useEffect(() => stopRepeat, [stopRepeat]);

  // ── Event handlers ────────────────────────────
  const handlePointerDown = (delta) => (e) => {
    e.preventDefault();
    applyDelta(delta); // immediate first tick
    startRepeat(delta);
  };

  const handlePointerUpOrLeave = () => {
    stopRepeat();
  };

  const handleDirectInput = (e) => {
    const raw = e.target.value.replace(/[^0-9]/g, '');
    if (raw === '') {
      onChange(min);
      return;
    }
    onChange(clamp(parseInt(raw, 10)));
  };

  const toggleStep = () => setStepIdx((i) => (i + 1) % STEPS.length);

  // ── Styles ────────────────────────────────────
  const wrapperStyle = {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  };

  const labelStyle = {
    fontSize: 10.5,
    fontWeight: 600,
    letterSpacing: '0.03em',
    textTransform: 'uppercase',
    color: tokens.color.inkMuted,
    fontFamily: tokens.font.ui,
  };

  const rowStyle = {
    display: 'flex',
    alignItems: 'center',
    gap: 0,
    borderRadius: tokens.radius.sm,
    border: `1px solid ${tokens.color.border}`,
    overflow: 'hidden',
    background: tokens.color.surface,
    height: 34,
  };

  const btnBase = {
    width: 34,
    height: '100%',
    border: 'none',
    cursor: 'pointer',
    fontFamily: tokens.font.ui,
    fontSize: 16,
    fontWeight: 600,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: tokens.color.surface,
    transition: 'background 0.15s',
    userSelect: 'none',
    WebkitUserSelect: 'none',
    flexShrink: 0,
  };

  const minusBtnStyle = {
    ...btnBase,
    background: tokens.color.accentDark,
    borderRight: `1px solid ${tokens.color.border}`,
  };

  const plusBtnStyle = {
    ...btnBase,
    background: tokens.color.accent,
    borderLeft: `1px solid ${tokens.color.border}`,
  };

  const inputStyle = {
    flex: 1,
    minWidth: 0,
    textAlign: 'center',
    border: 'none',
    outline: 'none',
    fontFamily: tokens.font.mono,
    fontSize: 13,
    fontWeight: 600,
    color: tokens.color.ink,
    background: 'transparent',
    padding: '0 4px',
  };

  // ── Gradient: light blue (×1) → futuristic purple (×100) ──
  const t = stepIdx / (STEPS.length - 1); // 0 → 1
  const hue = Math.round(200 + t * 70);          // 200 (sky) → 270 (purple)
  const sat = Math.round(60 + t * 30);           // 60% → 90%
  const bgLight = Math.round(92 - t * 55);       // 92% → 37%  (background)
  const fgLight = Math.round(48 - t * 18);       // 48% → 30%  (text, always readable)

  const stepBg = `hsl(${hue}, ${sat}%, ${bgLight}%)`;
  const stepFg = bgLight < 55 ? '#fff' : `hsl(${hue}, ${sat}%, ${fgLight}%)`;

  const stepToggleStyle = {
    height: '100%',
    border: 'none',
    borderLeft: `1px solid ${tokens.color.border}`,
    background: stepBg,
    color: stepFg,
    cursor: 'pointer',
    fontFamily: tokens.font.mono,
    fontSize: 10.5,
    fontWeight: 700,
    padding: '0 8px',
    transition: 'all 0.25s ease',
    userSelect: 'none',
    WebkitUserSelect: 'none',
    flexShrink: 0,
  };

  return (
    <div style={wrapperStyle}>
      {label && <span style={labelStyle}>{label}</span>}

      <div style={rowStyle}>
        {/* ── Minus button ── */}
        <button
          style={minusBtnStyle}
          onPointerDown={handlePointerDown(-step)}
          onPointerUp={handlePointerUpOrLeave}
          onPointerLeave={handlePointerUpOrLeave}
          tabIndex={-1}
          aria-label={`Disminuir ${step}`}
        >
          −
        </button>

        {/* ── Numeric display / input ── */}
        <input
          type="text"
          inputMode="numeric"
          style={inputStyle}
          value={value}
          onChange={handleDirectInput}
          aria-label={label ?? 'Cantidad'}
        />

        {/* ── Plus button ── */}
        <button
          style={plusBtnStyle}
          onPointerDown={handlePointerDown(step)}
          onPointerUp={handlePointerUpOrLeave}
          onPointerLeave={handlePointerUpOrLeave}
          tabIndex={-1}
          aria-label={`Aumentar ${step}`}
        >
          +
        </button>

        {/* ── Step toggle ×1 / ×5 ── */}
        <button style={stepToggleStyle} onClick={toggleStep} tabIndex={-1} aria-label="Cambiar paso">
          ×{step}
        </button>
      </div>
    </div>
  );
};

export default StepperInput;
