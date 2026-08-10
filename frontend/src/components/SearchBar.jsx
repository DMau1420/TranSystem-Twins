import React, { useState, useEffect, useRef } from 'react';
import { useMapData } from '../context/MapDataContext';
import { searchAddress } from '../utils/geocoding';
import { tokens } from '../styles/tokens';

const wrapperStyle = {
  position: 'absolute',
  top: 16,
  left: '50%',
  transform: 'translateX(-50%)',
  zIndex: 1000,
  width: 'min(480px, calc(100vw - 220px))',
  fontFamily: tokens.font.ui,
};

const pillStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  background: tokens.color.surface,
  borderRadius: tokens.radius.pill,
  boxShadow: tokens.shadow.card,
  padding: '6px 8px 6px 16px',
};

const inputStyle = {
  flex: 1,
  border: 'none',
  outline: 'none',
  fontFamily: tokens.font.ui,
  fontSize: 14,
  color: tokens.color.ink,
  background: 'transparent',
};

const dividerStyle = {
  width: 1,
  height: 22,
  background: tokens.color.border,
};

const iconButtonStyle = (active) => ({
  width: 36,
  height: 36,
  minWidth: 36,
  borderRadius: '50%',
  border: 'none',
  background: active ? tokens.color.accentSoft : 'transparent',
  color: tokens.color.accent,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  cursor: 'pointer',
});

const listStyle = {
  listStyle: 'none',
  margin: 0,
  marginTop: 8,
  padding: 0,
  background: tokens.color.surface,
  borderRadius: tokens.radius.lg,
  boxShadow: tokens.shadow.card,
  overflow: 'hidden',
};

const itemStyle = {
  padding: '10px 16px',
  fontSize: 13,
  color: tokens.color.ink,
  cursor: 'pointer',
  borderBottom: `1px solid ${tokens.color.border}`,
};

const statusTextStyle = {
  fontSize: 12,
  color: tokens.color.inkMuted,
  marginTop: 6,
  paddingLeft: 16,
};

const errorTextStyle = {
  fontSize: 12,
  color: tokens.color.danger,
  background: tokens.color.dangerSoft,
  borderRadius: tokens.radius.sm,
  padding: '6px 10px',
  marginTop: 6,
};

const SearchIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={tokens.color.inkMuted} strokeWidth="2">
    <circle cx="11" cy="11" r="7" />
    <line x1="21" y1="21" x2="16.65" y2="16.65" />
  </svg>
);

const LocateIcon = ({ spinning }) => (
  <svg
    width="18"
    height="18"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    style={spinning ? { animation: 'ts-spin 0.9s linear infinite' } : undefined}
  >
    <circle cx="12" cy="12" r="3" />
    <line x1="12" y1="2" x2="12" y2="5" />
    <line x1="12" y1="19" x2="12" y2="22" />
    <line x1="2" y1="12" x2="5" y2="12" />
    <line x1="19" y1="12" x2="22" y2="12" />
  </svg>
);

export const SearchBar = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [locating, setLocating] = useState(false);
  const [locateError, setLocateError] = useState(null);
  const { setSearchTarget } = useMapData();
  const debounceRef = useRef(null);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (query.trim().length < 3) {
      setResults([]);
      return;
    }

    setLoading(true);
    debounceRef.current = setTimeout(async () => {
      try {
        const found = await searchAddress(query);
        setResults(found);
      } catch (err) {
        console.error('Error buscando dirección:', err);
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 500);

    return () => clearTimeout(debounceRef.current);
  }, [query]);

  const handleSelect = (result) => {
    setSearchTarget({ lat: result.lat, lng: result.lng, displayName: result.displayName });
    setQuery(result.displayName);
    setResults([]);
  };

  const handleLocate = () => {
    if (!navigator.geolocation) {
      setLocateError('Tu navegador no soporta geolocalización.');
      return;
    }

    setLocating(true);
    setLocateError(null);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        setSearchTarget({ lat: latitude, lng: longitude, displayName: 'Mi ubicación' });
        setLocating(false);
      },
      (err) => {
        setLocating(false);
        setLocateError(
          err.code === err.PERMISSION_DENIED
            ? 'Permiso de ubicación denegado. Habilitalo en la configuración del navegador.'
            : 'No se pudo obtener tu ubicación.'
        );
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  return (
    <div style={wrapperStyle}>
      <style>{`@keyframes ts-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>

      <div style={pillStyle}>
        <SearchIcon />
        <input
          style={inputStyle}
          type="text"
          placeholder="Buscar calle o dirección en..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div style={dividerStyle} />
        <button
          style={iconButtonStyle(locating)}
          onClick={handleLocate}
          disabled={locating}
          title="Ir a mi ubicación actual"
        >
          <LocateIcon spinning={locating} />
        </button>
      </div>

      {loading && <div style={statusTextStyle}>Buscando…</div>}
      {locateError && <div style={errorTextStyle}>{locateError}</div>}

      {results.length > 0 && (
        <ul style={listStyle}>
          {results.map((r, idx) => (
            <li
              key={idx}
              style={{ ...itemStyle, borderBottom: idx === results.length - 1 ? 'none' : itemStyle.borderBottom }}
              onClick={() => handleSelect(r)}
            >
              {r.displayName}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default SearchBar;