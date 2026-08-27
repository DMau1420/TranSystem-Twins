import React, { useState, useEffect, useRef } from 'react';
import { useMapData } from '../context/MapDataContext';
import { searchAddress } from '../utils/geocoding';
import './SearchBar.css';

const SearchIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
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
    className={spinning ? 'tst-search__locate-icon is-spinning' : 'tst-search__locate-icon'}
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
    <div className="tst-search">
      <div className="tst-search__pill">
        <span className="tst-search__icon">
          <SearchIcon />
        </span>
        <input
          className="tst-search__input"
          type="text"
          placeholder="Buscar calle o dirección en..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="tst-search__divider" />
        <button
          type="button"
          className={`tst-search__locate-btn ${locating ? 'is-active' : ''}`}
          onClick={handleLocate}
          disabled={locating}
          title="Ir a mi ubicación actual"
        >
          <LocateIcon spinning={locating} />
        </button>
      </div>

      {loading && <div className="tst-search__status">Buscando…</div>}
      {locateError && <div className="tst-search__error">{locateError}</div>}

      {results.length > 0 && (
        <ul className="tst-search__results">
          {results.map((r, idx) => (
            <li key={idx} className="tst-search__result-item" onClick={() => handleSelect(r)}>
              {r.displayName}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default SearchBar;