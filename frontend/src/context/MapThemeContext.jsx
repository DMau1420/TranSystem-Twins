import { createContext, useContext, useState } from 'react';

const MapThemeContext = createContext(null);

/**
 * Contexto compartido para el estilo visual del mapa (claro/oscuro).
 * Envuelve el AppLayout para que Sidebar y MapContainer —que son
 * hermanos, no padre-hijo— puedan leer y cambiar el mismo estado.
 */
export function MapThemeProvider({ children, defaultTheme = 'dark' }) {
  const [mapStyle, setMapStyle] = useState(defaultTheme); // 'light' | 'dark'

  const toggleMapStyle = () => {
    setMapStyle((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  return (
    <MapThemeContext.Provider value={{ mapStyle, setMapStyle, toggleMapStyle }}>
      {children}
    </MapThemeContext.Provider>
  );
}

export function useMapTheme() {
  const ctx = useContext(MapThemeContext);
  if (!ctx) {
    throw new Error('useMapTheme debe usarse dentro de un MapThemeProvider');
  }
  return ctx;
}