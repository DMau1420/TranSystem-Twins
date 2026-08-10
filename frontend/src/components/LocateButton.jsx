import React, { useState } from 'react';
import { useMapData } from '../context/MapDataContext';

const buttonStyle = (loading) => ({
  position: 'absolute',
  top: 12,
  left: 390,
  zIndex: 1000,
  background: '#fff',
  border: '1px solid #ccc',
  borderRadius: 4,
  width: 40,
  height: 40,
  cursor: loading ? 'default' : 'pointer',
  fontSize: 18,
  boxShadow: '0 1px 4px rgba(0,0,0,0.15)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  opacity: loading ? 0.6 : 1,
});

export const LocateButton = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const { setSearchTarget } = useMapData();

  const handleClick = () => {
    if (!navigator.geolocation) {
      setError('Tu navegador no soporta geolocalización.');
      return;
    }

    setLoading(true);
    setError(null);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        setSearchTarget({ lat: latitude, lng: longitude, displayName: 'Mi ubicación' });
        setLoading(false);
      },
      (err) => {
        setLoading(false);
        if (err.code === err.PERMISSION_DENIED) {
          setError('Permiso de ubicación denegado. Habilitalo en la configuración del navegador.');
        } else {
          setError('No se pudo obtener tu ubicación.');
        }
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  return (
    <>
      <button
        style={buttonStyle(loading)}
        onClick={handleClick}
        disabled={loading}
        title="Ir a mi ubicación actual"
      >
        {loading ? '…' : '📍'}
      </button>
      {error && (
        <div
          style={{
            position: 'absolute',
            top: 56,
            left: 390,
            zIndex: 1000,
            background: '#fff5f5',
            color: '#c0392b',
            fontSize: 11,
            padding: '6px 10px',
            borderRadius: 4,
            maxWidth: 200,
            boxShadow: '0 1px 4px rgba(0,0,0,0.15)',
          }}
        >
          {error}
        </div>
      )}
    </>
  );
};

export default LocateButton;